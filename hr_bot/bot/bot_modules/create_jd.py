# bot/bot_modules/create_jd.py

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

print(DefaultConfig.BC_OPENAI_API_KEY)

file_path = r'bot/bot_modules/ques_modified.json'

# Initialize OpenAI
CONFIG = DefaultConfig()

openai.log = False
openai.api_type = "azure"
openai.api_key = CONFIG.BC_OPENAI_API_KEY
openai.api_base = "https://bc-api-management-uksouth.azure-api.net"
openai.api_version = "2023-03-15-preview"
chat_models = ["gpt-4-32k", "gpt-4", "gpt-35-turbo"]

try:
    print(f"OpenAI API Key configured: {'Yes' if openai.api_key else 'No'}")  # Debug print
except Exception as e:
    print(f"Error initializing OpenAI: {str(e)}")


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
        self.section_header_shown = False  # New flag to track if section header has been shown

    def load_template(self):
        with open(file_path, 'r') as file:
            return json.load(file)

    def is_active(self):
        return self.current_section is not None

    async def handle_message(self, turn_context: TurnContext):
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
        self.current_section = self.sections[self.section_index]
        self.section_header_shown = False  # Reset section header flag
        await self.ask_next_question(turn_context)

    async def ask_next_question(self, turn_context: TurnContext):
        # Show section header if not already shown for current section
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
                self.section_header_shown = False  # Reset section header flag for new section
                await self.ask_next_question(turn_context)
            else:
                await self.generate_job_description(turn_context)

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
                self.section_header_shown = False  # Reset section header flag for new section
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
                engine=chat_models[0],
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

    # Records the user's answer to a question and moves on to the next question or section.
    # async def generate_job_description(self, turn_context: TurnContext):
    #     prompt = f"Generate a professional job description based on the following information:\n\n"
    #     for section, questions in self.job_description.items():
    #         prompt += f"{section}:\n"
    #         for question, answer in questions.items():
    #             if answer is not None:  # Only include non-skipped questions
    #                 prompt += f"- {question} {answer}\n"
    #         prompt += "\n"
    #
    #     try:
    #         response = openai.ChatCompletion.create(
    #             engine=chat_models[0],
    #             messages=[
    #                 {"role": "system",
    #                  "content": "You are a professional HR assistant tasked with creating job descriptions. Only include information that was explicitly provided."},
    #                 {"role": "user", "content": prompt}
    #             ],
    #             max_tokens=1000,
    #             n=1,
    #             stop=None,
    #             temperature=0.7,
    #         )
    #         self.generated_jd = response.choices[0].message['content'].strip()
    #         await turn_context.send_activity(MessageFactory.text(f"Generated Job Description:\n\n{self.generated_jd}"))
    #         await self.show_accept_refine_buttons(turn_context)
    #     except Exception as e:
    #         await turn_context.send_activity(
    #             MessageFactory.text(f"An error occurred while generating the job description: {str(e)}"))

    async def generate_job_description(self, turn_context: TurnContext):
        # Extract all answers from the job_description dictionary
        answers = {}
        for section, questions in self.job_description.items():
            for question, answer in questions.items():
                if answer is not None and answer.strip() != "":
                    answers[question] = answer.strip()

        # Helper function to check if a section should be included
        def should_include_section(content):
            if not content:
                return False
            return not any(marker in content for marker in ["[", "]"])  # Check for placeholder text

        # Create dynamic sections based on available content
        growth_opportunities = answers.get(
            "What opportunities for learning and growth does this role offer? Are there any skills you expect them to develop?",
            "")
        opportunities_section = f"""
    Opportunity
    {growth_opportunities}

    """ if should_include_section(growth_opportunities) else ""

        additional_responsibilities = []

        cross_functional = answers.get(
            "How often will this person need to work with teams outside of engineering, like marketing, sales, or customer success?",
            "")
        if should_include_section(cross_functional):
            additional_responsibilities.append(f"• Working with: {cross_functional}")

        technologies = answers.get("Great! Any specific technologies or platforms they'll need to work with?", "")
        if should_include_section(technologies):
            additional_responsibilities.append(f"• Technologies: {technologies}")

        long_term_goals = answers.get("Great! Are there any long term goals for this position?", "")
        if should_include_section(long_term_goals):
            additional_responsibilities.append(f"• Long-term goals: {long_term_goals}")

        success_metrics = answers.get("Great! What is that defining success in this role?", "")
        if should_include_section(success_metrics):
            additional_responsibilities.append(f"• Success metrics: {success_metrics}")

        strategic_alignment = answers.get(
            "How does this role contribute to the company's larger strategic goals or vision?", "")
        if should_include_section(strategic_alignment):
            additional_responsibilities.append(f"• Strategic alignment: {strategic_alignment}")

        additional_responsibilities_section = f"""
    Additional responsibilities include:
    {chr(10).join(additional_responsibilities)}

    """ if additional_responsibilities else ""

        # Create the template prompt with proper spacing and conditional sections
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

    {additional_responsibilities_section}{opportunities_section}ABOUT YOU
    The ideal candidate will have:

    Required Qualifications:"""

        # Add required qualifications only if they exist
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

        working_style = answers.get(
            "What type of working style thrives in this role—do you prefer people who are more independent or team-oriented?",
            "")
        if should_include_section(working_style):
            required_quals.append(f"• Working Style: {working_style}")

        template += f"""
    {chr(10).join(required_quals)}

    """

        # Add preferred qualifications only if they exist
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

        # Add work environment section only if relevant fields exist
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

        # Add compensation section only if it exists
        compensation = answers.get("Would you like to include salary details or any benefits for this role?", "")
        if should_include_section(compensation):
            template += f"""
    Compensation and Benefits:
    {compensation}

    """

        template += """
    PROCESS
    Simply submit your CV.

    We have a rigorous recruitment process to ensure we attract the very best talent.

    Diversity Statement:
    We see diversity as something that creates a better workplace and delivers better outcomes. We actively encourage applications from all backgrounds and foster an inclusive environment where everyone can express themselves regardless of race, religion, sex, gender, color, national origin, disability, or any other applicable legally protected characteristic.
    """

        try:
            # Generate company overview section
            company_overview_prompt = f"""Based on this company information, create a professional 2-paragraph company overview:
            {answers.get("To help candidates understand more about your company, could you provide a brief overview of your organization?", "[Company Overview]")}
            Culture: {answers.get("And what's the work culture like on the team?", "[Company Culture]")}
            """

            company_overview_response = openai.ChatCompletion.create(
                engine=chat_models[0],
                messages=[
                    {"role": "system",
                     "content": "You are a professional HR writer creating company overviews for job descriptions. Ensure proper spacing between paragraphs using double line breaks."},
                    {"role": "user", "content": company_overview_prompt}
                ],
                max_tokens=200,
                temperature=0.7,
            )

            company_overview = company_overview_response.choices[0].message['content'].strip()

            # Replace the placeholder in the template
            final_template = template.replace("{company_overview}", company_overview)

            # Generate the final job description
            response = openai.ChatCompletion.create(
                engine=chat_models[0],
                messages=[
                    {"role": "system", "content": """You are a professional HR assistant tasked with creating job descriptions. 
                    Follow these formatting rules strictly:
                    1. Maintain double line breaks between sections
                    2. Keep one line break between items within sections
                    3. Ensure consistent bullet point formatting using •
                    4. Preserve all whitespace and newlines from the template
                    5. Format the title block with each field on its own line with proper spacing
                    6. Remove any sections that contain placeholder text in square brackets"""},
                    {"role": "user", "content": final_template}
                ],
                max_tokens=1000,
                temperature=0.7,
            )

            self.generated_jd = response.choices[0].message['content'].strip()

            # Post-process to ensure proper spacing in the title block
            title_block_lines = self.generated_jd.split('\n')[:4]
            rest_of_jd = self.generated_jd.split('\n')[4:]

            formatted_title_block = '\n'.join(line + '\n' for line in title_block_lines if line.strip())

            self.generated_jd = formatted_title_block + '\n' + '\n'.join(rest_of_jd)

            await turn_context.send_activity(MessageFactory.text(f"Generated Job Description:\n\n{self.generated_jd}"))
            await self.show_accept_refine_buttons(turn_context)

        except Exception as e:
            await turn_context.send_activity(
                MessageFactory.text(f"An error occurred while generating the job description: {str(e)}"))

    async def show_accept_refine_buttons(self, turn_context: TurnContext):
        reply = MessageFactory.text("How would you like to proceed?")
        reply.suggested_actions = SuggestedActions(
            actions=[
                {
                    "type": ActionTypes.im_back,
                    "title": "Accept",
                    "value": "Accept"
                },
                {
                    "type": ActionTypes.im_back,
                    "title": "Refine",
                    "value": "Refine"
                }
            ]
        )
        await turn_context.send_activity(reply)

    # Processes the user's response (either accept or request a refinement)
    async def handle_accept_refine(self, turn_context: TurnContext):
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
        refinement = turn_context.activity.text
        prompt = f"Refine the following job description based on this feedback: '{refinement}'\n\nOriginal Job Description:\n{self.generated_jd}"

        try:
            response = openai.ChatCompletion.create(
                engine=chat_models[0],
                messages=[
                    {"role": "system",
                     "content": "You are a professional HR assistant tasked with refining job descriptions. Apply the requested changes accurately."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                n=1,
                stop=None,
                temperature=0.7,
            )
            self.generated_jd = response.choices[0].message['content'].strip()
            await turn_context.send_activity(MessageFactory.text(f"Refined Job Description:\n\n{self.generated_jd}"))
            await self.show_accept_refine_buttons(turn_context)
        except Exception as e:
            await turn_context.send_activity(
                MessageFactory.text(f"An error occurred while refining the job description: {str(e)}"))

    async def finalize_job_description(self, turn_context: TurnContext):
        await turn_context.send_activity(
            MessageFactory.text("Great! Your job description has been finalized. What would you like to do next?"))

        card = HeroCard(
            title="Job Description Options",
            buttons=[
                CardAction(
                    type=ActionTypes.im_back,
                    title="Download as PDF",
                    value="download_pdf"
                ),
                CardAction(
                    type=ActionTypes.im_back,
                    title="Send it over email",
                    value="send_email"
                )
            ]
        )

        await turn_context.send_activity(MessageFactory.attachment(CardFactory.hero_card(card)))

    async def download_as_pdf(self, turn_context: TurnContext):
        pdf_bytes = self.generate_pdf()

        # Create a directory to store PDFs if it doesn't exist
        os.makedirs('generated_pdfs', exist_ok=True)

        # Generate a unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"job_description_{timestamp}.pdf"
        filepath = os.path.join('generated_pdfs', filename)

        # Save the PDF locally
        with open(filepath, 'wb') as f:
            f.write(pdf_bytes)

        # Create an attachment
        content_type = "application/pdf"
        attachment = Attachment(
            name=filename,
            content_type=content_type,
            content_url=f"data:{content_type};base64,{base64.b64encode(pdf_bytes).decode()}"
        )

        # Send the PDF as an attachment
        await turn_context.send_activity(
            MessageFactory.attachment(attachment,
                                      "Here's your Job Description PDF. You can download it by clicking on the attachment.")
        )

    async def handle_final_option(self, turn_context: TurnContext):
        option = turn_context.activity.text.lower()

        if option == "download_pdf":
            await self.download_as_pdf(turn_context)
        elif option == "send_email":
            await self.send_over_email(turn_context)

    async def send_over_email(self, turn_context: TurnContext):
        if not self.user_email:
            await turn_context.send_activity(
                MessageFactory.text("Sorry, we couldn't find your email address. Please try logging in again."))
            return

        try:
            msg = MIMEMultipart()
            msg['From'] = "your_bot@example.com"
            msg['To'] = self.user_email
            msg['Subject'] = "Your Finalized Job Description"

            body = f"Here's your finalized job description:\n\n{self.generated_jd}"
            msg.attach(MIMEText(body, 'plain'))

            # Attach PDF
            pdf_bytes = self.generate_pdf()
            pdf_attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
            pdf_attachment.add_header('content-disposition', 'attachment', filename="job_description.pdf")
            msg.attach(pdf_attachment)

            # Placeholder for sending email
            # server = smtplib.SMTP('smtp.gmail.com', 587)
            # server.starttls()
            # server.login("your_email@gmail.com", "your_password")
            # server.send_message(msg)
            # server.quit()

            await turn_context.send_activity(
                MessageFactory.text(f"An email with the job description has been sent to {self.user_email}."))
        except Exception as e:
            await turn_context.send_activity(
                MessageFactory.text(f"An error occurred while sending the email: {str(e)}"))

