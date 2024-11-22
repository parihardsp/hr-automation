import os
import json
import openai
import base64
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from botbuilder.core import TurnContext, MessageFactory, CardFactory
from botbuilder.schema import ActionTypes, CardAction, HeroCard, SuggestedActions, Attachment
from hr_bot.config import DefaultConfig


# File path for questions template
file_path = r'bot/bot_modules/ques_modified.json'

# Initialize configuration
CONFIG = DefaultConfig()

# Configure OpenAI
openai.api_type = "azure"
openai.api_key = CONFIG.BC_OPENAI_API_KEY
openai.api_base = "https://bc-api-management-uksouth.azure-api.net"
openai.api_version = "2023-03-15-preview"
deployment_name = "gpt-4-32k"  # or your specific deployment name


class JobDescriptionHandler:
    def __init__(self):
        self.job_description = self.load_template()
        self.current_section = None
        self.current_question = None
        self.sections = list(self.job_description.keys())
        self.section_index = 0
        self.question_index = 0
        self.generated_jd = None
        self.user_email = None
        self.section_header_shown = False

    def load_template(self):
        """Load the question template from JSON file"""
        try:
            with open(file_path, 'r') as file:
                return json.load(file)
        except Exception as e:
            print(f"Error loading template: {str(e)}")
            return {}

    def is_active(self):
        """Check if the job description creation process is active"""
        return self.current_section is not None

    async def handle_message(self, turn_context: TurnContext):
        """Handle incoming messages based on the current state"""
        if not self.is_active() and turn_context.activity.text.lower() == "create a jd":
            await self.start_job_description(turn_context)
        elif self.is_active():
            if self.generated_jd is not None:
                await self.handle_accept_refine(turn_context)
            elif self.current_question:
                await self.handle_answer(turn_context)
            else:
                await self.handle_refinement(turn_context)

    async def start_job_description(self, turn_context: TurnContext):
        """Start the job description creation process"""
        self.current_section = self.sections[self.section_index]
        self.section_header_shown = False
        await self.ask_next_question(turn_context)

    async def ask_next_question(self, turn_context: TurnContext):
        """Ask the next question in the current section"""
        if not self.section_header_shown:
            formatted_section = f"\n{'-' * 40}\n{self.current_section}\n{'-' * 40}"
            await turn_context.send_activity(MessageFactory.text(formatted_section))
            self.section_header_shown = True

        questions = list(self.job_description[self.current_section].keys())
        if self.question_index < len(questions):
            self.current_question = questions[self.question_index]
            await turn_context.send_activity(MessageFactory.text(self.current_question))
        else:
            self.section_index += 1
            self.question_index = 0
            if self.section_index < len(self.sections):
                self.current_section = self.sections[self.section_index]
                self.section_header_shown = False
                await self.ask_next_question(turn_context)
            else:
                await self.generate_job_description(turn_context)

    async def analyze_answer(self, question, answer):
        prompt = f"""
        Q: {question}
        A: {answer}

        Is this answer appropriate and relevant? (Yes/No)
        """

        try:
            response = openai.ChatCompletion.create(
                engine=deployment_name,
                messages=[
                    {"role": "system",
                     "content": "You're an HR assistant. Determine if answers are appropriate and relevant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=10,
                n=1,
                stop=None,
                temperature=0.3,
            )

            analysis = response.choices[0].message['content'].strip().lower()
            return analysis.startswith('yes')
        except Exception as e:
            return False

    async def handle_answer(self, turn_context: TurnContext):
        answer = turn_context.activity.text.strip().lower()

        if answer == "skip":
            self.job_description[self.current_section][self.current_question] = None
            await self.move_to_next_question(turn_context)
            return

        is_appropriate = await self.analyze_answer(self.current_question, answer)

        if is_appropriate:
            self.job_description[self.current_section][self.current_question] = answer
            await self.move_to_next_question(turn_context)
        else:
            await turn_context.send_activity(MessageFactory.text(
                "I didn't understand the answer. Please give me a relevant response or write 'skip' to move on."))

    async def move_to_next_question(self, turn_context: TurnContext):
        """Move to the next question or section"""
        self.question_index += 1
        questions = list(self.job_description[self.current_section].keys())
        if self.question_index < len(questions):
            self.current_question = questions[self.question_index]
            await turn_context.send_activity(MessageFactory.text(self.current_question))
        else:
            self.section_index += 1
            self.question_index = 0
            if self.section_index < len(self.sections):
                self.current_section = self.sections[self.section_index]
                self.section_header_shown = False
                await self.ask_next_question(turn_context)
            else:
                await self.generate_job_description(turn_context)

    async def generate_job_description(self, turn_context: TurnContext):
        """Generate the complete job description"""
        answers = {}
        for section, questions in self.job_description.items():
            for question, answer in questions.items():
                if answer is not None and answer.strip() != "":
                    answers[question] = answer.strip()

        def should_include_section(content):
            if not content:
                return False
            return not any(marker in content for marker in ["[", "]"])

        # Build the job description template
        template = self.build_job_description_template(answers, should_include_section)

        try:
            # Generate company overview
            company_overview = await self.generate_company_overview(answers)
            final_template = template.replace("{company_overview}", company_overview)

            # Generate final job description
            response = openai.ChatCompletion.create(
                engine=deployment_name,
                messages=[
                    {"role": "system", "content": """You are a professional HR assistant creating job descriptions.
                    Follow these formatting rules:
                    1. Use double line breaks between sections
                    2. Use single line breaks within sections
                    3. Use bullet points (•) consistently
                    4. Keep all whitespace and formatting
                    5. Remove sections with placeholder text"""},
                    {"role": "user", "content": final_template}
                ],
                max_tokens=1000,
                temperature=0.7,
            )

            self.generated_jd = response.choices[0].message['content'].strip()

            # Format the title block
            self.generated_jd = self.format_title_block(self.generated_jd)

            await turn_context.send_activity(MessageFactory.text(f"Generated Job Description:\n\n{self.generated_jd}"))
            await self.show_accept_refine_buttons(turn_context)

        except Exception as e:
            await turn_context.send_activity(
                MessageFactory.text(f"An error occurred while generating the job description: {str(e)}"))

    def build_job_description_template(self, answers, should_include_section):
        """Build the job description template with all sections"""
        template = f"""
    Title: {answers.get("Let's begin with the basics. What's the job title you're hiring for?", "[Job Title]")}
    Location: {answers.get("Well. Where is this position based at?", "[Location]")}
    Reports To: {answers.get("Got it. And who will this person report to?", "[Reports To]")}
    Job Type: {answers.get("Thanks! And is this position full-time, part-time, or contract?", "[Job Type]")}
    Division: {answers.get("Which department will this role be in?", "[Division]")}

    • Are you ready to drive excellence and innovation within a dynamic organization?
    • Do you want to have the opportunity to shape the future in your field?

    If so, we would love to hear from you!

    ABOUT US
    {{company_overview}}

    OUR VALUES
    [To be populated based on company culture information]

    THE ROLE
    Key responsibilities
    We are seeking an experienced {answers.get("Let's begin with the basics. What's the job title you're hiring for?", "[Job Title]")} to join our team. The ideal candidate will report to {answers.get("Got it. And who will this person report to?", "[Manager Role]")}.

    Specific duties
    {answers.get("Now, let's talk about the key responsibilities. Can you describe the main duties this person will handle?", "[Main Duties]")}
    """

        # Additional Responsibilities
        additional_responsibilities = []

        cross_functional = answers.get(
            "How often will this person need to work with teams outside of engineering, like marketing, sales, or customer success?",
            "")
        if should_include_section(cross_functional):
            additional_responsibilities.append(f"• Working with: {cross_functional}")

        technologies = answers.get("Great! Any specific technologies or platforms they'll need to work with?", "")
        if should_include_section(technologies):
            additional_responsibilities.append(f"• Technologies: {technologies}")

        if additional_responsibilities:
            template += f"""
    Additional responsibilities include:
    {chr(10).join(additional_responsibilities)}
    """

        # Growth Opportunities
        growth_opportunities = answers.get(
            "What opportunities for learning and growth does this role offer? Are there any skills you expect them to develop?",
            "")
        if should_include_section(growth_opportunities):
            template += f"""
    Opportunity
    {growth_opportunities}
    """

        # Required Qualifications
        template += "\n    Required Qualifications:\n"
        required_quals = []

        experience = answers.get(
            "Let's cover the skills and qualifications next. What's the minimum level of experience required for this role?",
            "")
        if should_include_section(experience):
            required_quals.append(f"• Experience: {experience}")

        education = answers.get("Great! Any specific educational background or certifications needed?", "")
        if should_include_section(education):
            required_quals.append(f"• Education: {education}")

        skills = answers.get("And are there any must-have technical skills or soft skills?", "")
        if should_include_section(skills):
            required_quals.append(f"• Technical Skills: {skills}")

        template += "    " + "\n    ".join(required_quals) + "\n"

        # Preferred Qualifications
        preferred_quals = []
        additional_quals = answers.get("Are there any additional qualifications or skills that would be a bonus?", "")
        if should_include_section(additional_quals):
            preferred_quals.append(f"• {additional_quals}")

        preferred_background = answers.get("Is there any preferred candidate background that would fit the role best?",
                                           "")
        if should_include_section(preferred_background):
            preferred_quals.append(f"• {preferred_background}")

        if preferred_quals:
            template += f"""
    Preferred Qualifications:
    {chr(10).join(preferred_quals)}
    """

        # Work Environment
        work_env = []
        work_mode = answers.get("Can you talk about the work mode?", "")
        if should_include_section(work_mode):
            work_env.append(f"• Mode: {work_mode}")

        management_style = answers.get(
            "How would you describe your management style? What kind of guidance or mentorship can the new hire expect?",
            "")
        if should_include_section(management_style):
            work_env.append(f"• Management Style: {management_style}")

        if work_env:
            template += f"""
    Work Environment:
    {chr(10).join(work_env)}
    """

        # Compensation
        compensation = answers.get("Would you like to include salary details or any benefits for this role?", "")
        if should_include_section(compensation):
            template += f"""
    Compensation and Benefits:
    {compensation}
    """

        # Add standard closing sections
        template += """
    PROCESS
    Simply submit your CV.

    We have a rigorous recruitment process to ensure we attract the very best talent.

    Diversity Statement:
    We see diversity as something that creates a better workplace and delivers better outcomes. We actively encourage applications from all backgrounds and foster an inclusive environment where everyone can express themselves regardless of race, religion, sex, gender, color, national origin, disability, or any other applicable legally protected characteristic.
    """

        return template

    async def generate_company_overview(self, answers):
        """Generate the company overview section"""
        company_overview_prompt = f"""Based on this company information, create a professional 2-paragraph company overview:
        {answers.get("To help candidates understand more about your company, could you provide a brief overview of your organization?", "[Company Overview]")}
        Culture: {answers.get("And what's the work culture like on the team?", "[Company Culture]")}
        """

        try:
            response = openai.ChatCompletion.create(
                engine=deployment_name,
                messages=[
                    {"role": "system",
                     "content": "You are a professional HR writer creating company overviews for job descriptions. Ensure proper spacing between paragraphs using double line breaks."},
                    {"role": "user", "content": company_overview_prompt}
                ],
                max_tokens=200,
                temperature=0.7,
            )
            return response.choices[0].message['content'].strip()
        except Exception as e:
            print(f"Error generating company overview: {str(e)}")
            return "[Company Overview]"

    def format_title_block(self, jd):
        """Format the title block with proper spacing"""
        title_block_lines = jd.split('\n')[:4]
        rest_of_jd = jd.split('\n')[4:]
        formatted_title_block = '\n'.join(line + '\n' for line in title_block_lines if line.strip())
        return formatted_title_block + '\n' + '\n'.join(rest_of_jd)

    async def show_accept_refine_buttons(self, turn_context: TurnContext):
        """Show buttons for accepting or refining the job description"""
        reply = MessageFactory.text("How would you like to proceed?")
        reply.suggested_actions = SuggestedActions(
            actions=[
                CardAction(type=ActionTypes.im_back, title="Accept", value="Accept"),
                CardAction(type=ActionTypes.im_back, title="Refine", value="Refine")
            ]
        )
        await turn_context.send_activity(reply)

    async def handle_accept_refine(self, turn_context: TurnContext):
        """Handle user's choice to accept or refine the job description"""
        user_choice = turn_context.activity.text.lower()
        if user_choice == "accept":
            await self.finalize_job_description(turn_context)
        elif user_choice == "refine":
            await turn_context.send_activity(
                MessageFactory.text("Please specify what you'd like to change or add to the job description."))
        elif user_choice in ["download_pdf", "send_email"]:
            await self.handle_final_option(turn_context)
        else:
            await self.handle_refinement(turn_context)

    async def handle_refinement(self, turn_context: TurnContext):
        """Handle refinement requests for the job description"""
        refinement = turn_context.activity.text
        prompt = f"Refine the following job description based on this feedback: '{refinement}'\n\nOriginal Job Description:\n{self.generated_jd}"

        try:
            response = openai.ChatCompletion.create(
                engine=deployment_name,
                messages=[
                    {"role": "system", "content": "You are a professional HR assistant refining job descriptions."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7,
            )
            self.generated_jd = response.choices[0].message['content'].strip()
            await turn_context.send_activity(MessageFactory.text(f"Refined Job Description:\n\n{self.generated_jd}"))
            await self.show_accept_refine_buttons(turn_context)
        except Exception as e:
            await turn_context.send_activity(
                MessageFactory.text(f"An error occurred while refining the job description: {str(e)}"))

    async def finalize_job_description(self, turn_context: TurnContext):
        """Show final options for the job description"""
        await turn_context.send_activity(
            MessageFactory.text("Great! Your job description has been finalized. What would you like to do next?"))

        card = HeroCard(
            title="Job Description Options",
            buttons=[
                CardAction(type=ActionTypes.im_back, title="Download as PDF", value="download_pdf"),
                CardAction(type=ActionTypes.im_back, title="Send it over email", value="send_email")
            ]
        )

        await turn_context.send_activity(MessageFactory.attachment(CardFactory.hero_card(card)))

    async def handle_final_option(self, turn_context: TurnContext):
        """Handle final options (PDF download or email)"""
        option = turn_context.activity.text.lower()

        if option == "download_pdf":
            await self.download_as_pdf(turn_context)
        elif option == "send_email":
            await self.send_over_email(turn_context)

    async def download_as_pdf(self, turn_context: TurnContext):
        """Generate and send PDF as attachment"""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from io import BytesIO

            # Create PDF buffer
            buffer = BytesIO()

            # Create the PDF document
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []

            # Create custom style for the content
            content_style = ParagraphStyle(
                'CustomStyle',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=11,
                spaceAfter=12,
                leading=14
            )

            # Add title with larger font
            title_style = ParagraphStyle(
                'TitleStyle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30
            )

            # Split the job description into sections and format them
            sections = self.generated_jd.split('\n\n')
            for section in sections:
                if section.strip():
                    story.append(Paragraph(section.replace('\n', '<br/>'), content_style))
                    story.append(Spacer(1, 12))

            # Build the PDF
            doc.build(story)

            # Get the PDF content
            pdf_content = buffer.getvalue()
            buffer.close()

            # Create directory for PDFs if it doesn't exist
            os.makedirs('generated_pdfs', exist_ok=True)

            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"job_description_{timestamp}.pdf"
            filepath = os.path.join('generated_pdfs', filename)

            # Save PDF locally
            with open(filepath, 'wb') as f:
                f.write(pdf_content)

            # Create attachment for Bot Framework
            attachment = Attachment(
                name=filename,
                content_type="application/pdf",
                content_url=f"data:application/pdf;base64,{base64.b64encode(pdf_content).decode()}"
            )

            # Send the PDF
            await turn_context.send_activity(
                MessageFactory.attachment(attachment,
                                          "Here's your Job Description PDF. You can download it by clicking on the attachment.")
            )

        except Exception as e:
            await turn_context.send_activity(
                MessageFactory.text(f"An error occurred while generating the PDF: {str(e)}"))

    async def send_over_email(self, turn_context: TurnContext):
        """Send job description via email"""
        if not self.user_email:
            await turn_context.send_activity(
                MessageFactory.text("Please provide your email address:"))
            return

        try:
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = CONFIG.SMTP_FROM_EMAIL
            msg['To'] = self.user_email
            msg['Subject'] = "Your Generated Job Description"

            # Email body
            body = f"""
            Dear User,

            Please find attached your generated job description.

            Best regards,
            HR Bot Team
            """
            msg.attach(MIMEText(body, 'plain'))

            # Generate PDF for attachment
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from io import BytesIO

                # Create PDF buffer
                buffer = BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=letter)
                styles = getSampleStyleSheet()
                story = []

                # Custom style for content
                content_style = ParagraphStyle(
                    'CustomStyle',
                    parent=styles['Normal'],
                    fontName='Helvetica',
                    fontSize=11,
                    spaceAfter=12,
                    leading=14
                )

                # Format and add content
                sections = self.generated_jd.split('\n\n')
                for section in sections:
                    if section.strip():
                        story.append(Paragraph(section.replace('\n', '<br/>'), content_style))
                        story.append(Spacer(1, 12))

                # Build PDF
                doc.build(story)
                pdf_content = buffer.getvalue()
                buffer.close()

                # Attach PDF to email
                pdf_attachment = MIMEApplication(pdf_content, _subtype="pdf")
                pdf_attachment.add_header('Content-Disposition', 'attachment',
                                          filename="job_description.pdf")
                msg.attach(pdf_attachment)

                # Here you would implement your email sending logic
                # Example using smtplib:
                """
                import smtplib

                with smtplib.SMTP(CONFIG.SMTP_SERVER, CONFIG.SMTP_PORT) as server:
                    server.starttls()
                    server.login(CONFIG.SMTP_USERNAME, CONFIG.SMTP_PASSWORD)
                    server.send_message(msg)
                """

                await turn_context.send_activity(
                    MessageFactory.text(f"An email with the job description has been sent to {self.user_email}"))

            except Exception as e:
                await turn_context.send_activity(
                    MessageFactory.text(f"An error occurred while generating the PDF: {str(e)}"))

        except Exception as e:
            await turn_context.send_activity(
                MessageFactory.text(f"An error occurred while sending the email: {str(e)}"))

    def generate_pdf(self):
        """Helper method to generate PDF content"""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from io import BytesIO

            # Create PDF buffer
            buffer = BytesIO()

            # Create the PDF document
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []

            # Create custom style
            content_style = ParagraphStyle(
                'CustomStyle',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=11,
                spaceAfter=12,
                leading=14
            )

            # Format the content
            sections = self.generated_jd.split('\n\n')
            for section in sections:
                if section.strip():
                    story.append(Paragraph(section.replace('\n', '<br/>'), content_style))
                    story.append(Spacer(1, 12))

            # Build the PDF
            doc.build(story)

            # Get the content
            pdf_content = buffer.getvalue()
            buffer.close()

            return pdf_content

        except Exception as e:
            print(f"Error generating PDF: {str(e)}")
            return None