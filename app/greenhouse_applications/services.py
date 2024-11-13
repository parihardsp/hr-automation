import json
import openai
import asyncio
from sqlalchemy.testing.plugin.plugin_base import logging


from app.core.config import Settings
from typing import Dict, Any

from app.core.logger_setup import setup_logger
# Set up the logger
logger = setup_logger()

# Initialize configuration
CONFIG = Settings()

# Configure OpenAI with error handling
try:
    openai.api_type = "azure"
    openai.api_key = CONFIG.BC_OPENAI_API_KEY
    openai.api_base = "https://bc-api-management-uksouth.azure-api.net"
    openai.api_version = "2023-03-15-preview"
    deployment_name = "gpt-4-32k"
except Exception as e:
    logging.error(f"Error configuring OpenAI: {str(e)}")
    raise


# variable which will have job_content
job_content = """job_content = "Job Title: Software Engineer Department: Technology &amp; Development Location: Remote / [Your Location] Employment Type: Full-Time Job Summary: We are seeking a highly motivated and skilled Software Engineer to join our dynamic development team. The successful candidate will be responsible for designing, developing, and implementing software solutions to address complex business challenges. This role involves working with cross-functional teams to define system requirements, troubleshoot issues, and deploy high-quality software. Responsibilities: Design, develop, test, and deploy high-quality software applications. Collaborate with product management, design, and other teams to understand requirements and deliver solutions. Perform code reviews and provide constructive feedback to peers. Write and maintain documentation for all software solutions. Troubleshoot and debug applications to optimize performance and functionality. Stay up-to-date with industry trends and technologies to improve skills and enhance software capabilities. Ensure application security, maintainability, and scalability are addressed in the design. Required Skills &amp; Qualifications: Bachelor&#39;s degree in Computer Science, Software Engineering, or related field. 3+ years of experience in software development. Proficiency in Python, JavaScript, and related frameworks (e.g., React, Django). Experience with RESTful API design and development. Knowledge of database systems like PostgreSQL, MySQL, or MongoDB. Familiarity with version control systems, especially Git. Strong analytical and problem-solving skills. Excellent communication and collaboration abilities. Preferred Qualifications: Experience with cloud platforms like AWS, Azure, or Google Cloud. Knowledge of containerization tools (e.g., Docker) and CI/CD pipelines. Familiarity with Agile and Scrum development methodologies. Benefits: Competitive salary and performance-based incentives. Flexible working hours and remote work options. Comprehensive health, dental, and vision insurance. Opportunities for professional growth and development. A collaborative and innovative work environment. We are committed to creating a diverse and inclusive workplace and encourage applications from candidates of all backgrounds. Any HTML included through the hosted job application editor will be automatically converted into corresponding HTML entities.&amp;lt;/p&amp;gt;"
"""

resume_content_sample = """Name: John Doe Contact Information: john.doe@example.com | (123) 456-7890 | LinkedIn: linkedin.com/in/johndoe | Location: Remote / City, State Professional Summary: Experienced software engineer with over 5 years of expertise in web and software development. Skilled in designing, developing, and deploying complex applications, with a strong focus on performance optimization, security, and maintainability. Committed to continuous learning and staying updated with industry trends. Experience: Software Engineer Company: ABC Tech Solutions Location: Remote Duration: January 2020 - Present - Led the development of a high-traffic web application, which improved user engagement by 30%. - Collaborated with cross-functional teams to define system requirements and deliver scalable solutions. - Implemented security best practices and optimized application performance, reducing response time by 20%. - Tech Stack: Python, Django, React, PostgreSQL, AWS. Junior Developer Company: XYZ Innovations Location: City, State Duration: June 2018 - December 2019 - Supported senior developers in building and maintaining a SaaS platform. - Assisted in creating RESTful APIs and integrating third-party services. - Conducted code reviews and contributed to improving code quality across the team. - Tech Stack: JavaScript, Node.js, MySQL. Education: Bachelor's Degree in Computer Science University of Technology City, State Graduated: May 2018 Skills: Programming Languages: Python, JavaScript, SQL Web Technologies: React, Django, Node.js Database Management: PostgreSQL, MySQL Version Control: Git, GitHub Cloud Platforms: AWS, Azure Certifications: AWS Certified Solutions Architect – Associate, Amazon Web Services (AWS), Issued: 2022 Certified ScrumMaster (CSM), Scrum Alliance, Issued: 2021 Projects: Project Management Tool: Developed an internal project management tool to track and optimize workflow across departments, reducing project completion time by 25%. E-commerce Platform: Created a scalable e-commerce platform with custom APIs for product management and payment processing. Additional Information: Volunteer Web Developer for a non-profit organization, designing and maintaining its website to improve user accessibility and engagement."""


#Function which takes the raw Jd can converts it into reformatted JD (o/p: Json)
def format_jd_with_gpt(jd_text):
    prompt = f"""
    You are a powerful AI that helps reformat job descriptions (JDs) into a structured JSON format. Below is the template you need to follow:

    **Template (in JSON format):**

    ```json
    {{
        "companyInfo": {{
            "companyName": "",
            "location": "",
            "industry": ""
        }},
        "requiredQualifications": [
            {{
                "degree": "",
                "field": "",
                "additionalRequirements": ""
            }}
        ],
        "requiredWorkExperience": {{
            "yearsRequired": "",
            "description": ""
        }},
        "rolesAndResponsibilities": [
            ""
        ],
        "requiredSkills": [
            ""
        ],
        "requiredCertifications": [
            {{
                "certificationName": "",
                "issuingOrganization": ""
            }}
        ]
    }}
    ```

    **Job Description Text:**
    {jd_text}

    **Reformatted Job Description:**
    Please extract and reformat the information from the provided job description text according to the template above. Ensure that each section is clearly labeled and formatted appropriately. If any section is missing, leave it blank but indicate its presence in the template.
    """

    response = openai.ChatCompletion.create(
        engine=deployment_name,
        messages=[
            {"role": "system",
             "content": prompt},
        ],
        max_tokens=1500,
        temperature=0.7
    )

    analysis = response.choices[0].message.content

    return analysis



def format_resume_with_gpt(resume_text):
    prompt = f"""
    You are a powerful AI that helps reformat resumes into a structured JSON format. Below is the template you need to follow:

    **Template (in JSON format):**

    ```json
    {{
        "personalInfo": {{
            "name": "",
            "location": "",
            "email": "",
            "phone": "",
            "linkedIn": ""
        }},
        "education": [
            {{
                "degree": "",
                "field": "",
                "institution": "",
                "graduationYear": "",
                "gpa": ""
            }}
        ],
        "workExperience": [
            {{
                "company": "",
                "position": "",
                "duration": "",
                "responsibilities": [""],
                "achievements": [""]
            }}
        ],
        "skills": {{
            "technical": [""],
            "soft": [""],
            "languages": [""]
        }},
        "certifications": [
            {{
                "name": "",
                "issuingOrganization": "",
                "issueDate": "",
                "expiryDate": ""
            }}
        ],
        "projects": [
            {{
                "name": "",
                "description": "",
                "technologies": [""],
                "link": ""
            }}
        ]
    }}
    ```

    **Resume Text:**
    {resume_text}

    **Reformatted Resume:**
    Please extract and reformat the information from the provided resume text according to the template above.
    """

    response = openai.ChatCompletion.create(
        engine=deployment_name,
        messages=[
            {"role": "system", "content": prompt},
        ],
        max_tokens=1500,
        temperature=0.7
    )

    analysis = response.choices[0].message.content

    return analysis


# Dummy data for resume_data
resume_data = {
    "experience": [
        {
            "company": "ABC Tech Solutions",
            "position": "Software Engineer",
            "duration": "January 2020 - Present",
            "responsibilities": [
                "Led the development of a high-traffic web application",
                "Collaborated with cross-functional teams to define system requirements and deliver scalable solutions"
            ],
            "achievements": [
                "Improved user engagement by 30%",
                "Optimized application performance, reducing response time by 20%"
            ]
        },
        {
            "company": "XYZ Innovations",
            "position": "Junior Developer",
            "duration": "June 2018 - December 2019",
            "responsibilities": [
                "Supported senior developers in building and maintaining a SaaS platform",
                "Assisted in creating RESTful APIs and integrating third-party services"
            ],
            "achievements": [
                "Contributed to improving code quality across the team"
            ]
        }
    ],
    "skills": {
        "technical": ["Python", "JavaScript", "SQL"],
        "soft": ["Analytical", "Problem-solving"],
        "languages": ["English"]
    },
    "qualifications": {
        "degree": "Bachelor's Degree",
        "field": "Computer Science",
        "institution": "University of Technology",
        "graduationYear": 2018,
        "gpa": None
    },
    "projects": [
        {
            "name": "Project Management Tool",
            "description": "Developed an internal project management tool to track and optimize workflow",
            "technologies": ["Python", "Django"],
            "link": None
        },
        {
            "name": "E-commerce Platform",
            "description": "Created a scalable e-commerce platform with custom APIs for product management and payment processing",
            "technologies": ["JavaScript", "Node.js"],
            "link": None
        }
    ],
    "certifications": [
        {
            "name": "AWS Certified Solutions Architect – Associate",
            "issuingOrganization": "Amazon Web Services (AWS)",
            "issueDate": "2022",
            "expiryDate": None
        },
        {
            "name": "Certified ScrumMaster (CSM)",
            "issuingOrganization": "Scrum Alliance",
            "issueDate": "2021",
            "expiryDate": None
        }
    ]
}

# Dummy data for jd_data
jd_data = {
    "required_experience": {
        "yearsRequired": "3+ years",
        "description": "Experience in software development"
    },
    "required_skills": [
        "Python",
        "JavaScript",
        "React",
        "Django"
    ],
    "roles_responsibilities": [
        "Design, develop, test, and deploy high-quality software applications",
        "Collaborate with product management, design, and other teams to understand requirements and deliver solutions",
        "Perform code reviews and provide constructive feedback"
    ],
    "required_qualifications": [
        {
            "degree": "Bachelor's degree",
            "field": "Computer Science, Software Engineering, or related field"
        }
    ],
    "required_certifications": [
        {
            "certificationName": "AWS Certified Solutions Architect - Associate",
            "issuingOrganization": "Amazon Web Services (AWS)"
        }
    ]
}

application_id = 12345

async def generate_similarity_scores(
        resume_data: Dict[str, Any],
        jd_data: Dict[str, Any],
        application_id: int
) -> Dict[str, Any]:
    """
    Generate similarity scores between processed resume and JD using GPT

    Args:
        resume_data: Dictionary containing resume fields (experience, skills, etc.)
        jd_data: Dictionary containing JD fields (required experience, skills, etc.)
        application_id: ID of the application for logging purposes

    Returns:
        Dict containing scores and detailed analysis
    """
    try:
        logger.info(f"Generating similarity scores for application ID: {application_id}")

        prompt_template = """
        You are a helpful assistant that scores resumes based on the provided job description (JD).
        Evaluate the resume based on the following criteria:
        1. Overall Relevance Score (0-100 points): Overall score based on entire evaluation done
        2. Skills Match (0-30 points): How well do the skills listed in the resume match the skills required in the JD?
        3. Experience Match (0-30 points): How well does the candidate's experience match the job requirements?
        4. Education Match (0-20 points): How well does the candidate's education align with the job requirements?
        5. Overall Relevance (0-20 points): Overall relevance of the candidate's profile to the job.

        Job Description: {processed_jd}
        Resume: {processed_resume}

        Please provide the output in the following format:

        {{
          "matching_score": 0,
          "sections": [
            {{
              "name": "Skills Match",
              "score": 0,
              "max_score": 30,
              "overview": ""
            }},
            {{
              "name": "Experience Match",
              "score": 0,
              "max_score": 30,
              "overview": ""
            }},
            {{
              "name": "Education Match",
              "score": 0,
              "max_score": 20,
              "overview": ""
            }},
            {{
              "name": "Overall Relevance",
              "score": 0,
              "max_score": 20,
              "overview": ""
            }}
          ]
        }}
        """

        # Make GPT API call
        response = await openai.ChatCompletion.acreate(
            engine=deployment_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt_template.format(
                    processed_jd=json.dumps(jd_data, indent=2),
                    processed_resume=json.dumps(resume_data, indent=2)
                )}
            ],
            max_tokens=1500,
            temperature=0.7
        )

        # Parse GPT response to extract scores and analysis
        analysis = response.choices[0].message.content

        # Convert the analysis to a Python dictionary
        output = json.loads(analysis)

        # Calculate the overall matching score
        overall_score = sum(section['score'] for section in output['sections'])
        output['matching_score'] = overall_score

        return output

    except Exception as e:
        logger.error(f"Error generating similarity scores: {str(e)}")
        raise



if __name__ == "__main__":
    analysis = asyncio.run(generate_similarity_scores(resume_data, jd_data, application_id))
    print(analysis)

    # analysis = asyncio.run(generate_similarity_scores(resume_data, jd_data, application_id))
    # print(f"Matching score: {analysis['matching_score']}")
    # for section in analysis['sections']:
    #     print(f"{section['name']}: {section['score']}/{section['max_score']}")
    #     print(f"Overview: {section['overview']}")
    # print()

# # Assuming formatted_jd is the output returned by format_jd_with_gpt
# formatted_jd = format_jd_with_gpt(job_content)
#
# # Remove ```json block formatting if present
# formatted_jd = formatted_jd.strip("```json").strip("```").strip()
#
# print("Formatted JD (Raw Output):")
# print(formatted_jd)
#
# # Parse JSON output into a dictionary
# try:
#     formatted_jd_dict = json.loads(formatted_jd)
#
#     # Fetching and printing sections:
#     required_experience = formatted_jd_dict["requiredWorkExperience"]
#     print("Required Experience:", required_experience)
#
#     required_skills = formatted_jd_dict["requiredSkills"]
#     print("Required Skills:", required_skills)
#
#     roles_responsibilities = formatted_jd_dict["rolesAndResponsibilities"]
#     print("Roles and Responsibilities:", roles_responsibilities)
#
#     requiredQualifications = formatted_jd_dict["requiredQualifications"]
#     print("Required Qualifications:", requiredQualifications)
#
#     requiredCertifications = formatted_jd_dict["requiredCertifications"]
#     print("Required Certifications:", requiredCertifications)
#
# except json.JSONDecodeError as e:
#     print("JSON decoding failed:", str(e))
# except KeyError as e:
#     print("Missing key in JSON:", str(e))
#





