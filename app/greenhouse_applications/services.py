import os
import io
import json
import openai
import PyPDF2
import requests
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv
from datetime import datetime, timedelta
from app.core.logger_setup import setup_logger
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas

logger = setup_logger()
load_dotenv()

# Fetch environment variables
account_name = os.getenv('ACCOUNT_NAME')
container_name = os.getenv('CONTAINER_NAME')
account_key = os.getenv('account_key')
account_url = f"https://{account_name}.blob.core.windows.net"
openai.api_key = os.getenv('BC_OPENAI_API_KEY')
openai.api_base = os.getenv('BASE_URL')
openai.api_version = "2023-03-15-preview"
deployment_name = "gpt-4-32k"
openai.api_type = "azure"

class CandidateJobEvaluator:
    def __init__(self):
        self.blob_service_client = BlobServiceClient(account_url=account_url, credential=account_key)
        self.formatted_resume = None
        # Add default JD data as class attribute
        self.jd_data = {
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
        logger.info(f"BlobServiceClient initialized for account: {account_name}")

    def generate_sas_token(self, container_name: str, blob_name: str) -> str:
        """
        Generate a SAS (Shared Access Signature) token for a specific blob.
        """
        try:
            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=container_name,
                blob_name=blob_name,
                account_key=account_key,
                permission=BlobSasPermissions(read=True, write=True),
                expiry=datetime.utcnow() + timedelta(hours=0.166667)
            )
            logger.info(f"SAS token generated successfully: {sas_token}")
            return sas_token
        except Exception as e:
            logger.error(f"Error generating SAS token: {e}")
            raise

    def upload_pdf_to_blob(self, pdf_filename: str) -> bool:
        """
        Upload a PDF file to Azure Blob Storage.
        """
        try:
            pdf_path = Path('C:/Users/AnishaChoudhury/Documents/Code/hr-automation/Resumes').joinpath(pdf_filename)
            logger.info(f"Looking for file at path: {pdf_path}")

            if not os.path.exists(pdf_path):
                logger.error(f"File not found: {pdf_path}")
                return False

            sas_token = self.generate_sas_token(container_name, pdf_filename)
            blob_url = f"{account_url}/{container_name}/{pdf_filename}?{sas_token}"
            blob_pdf_path = f"{account_url}/{container_name}/{pdf_filename}"

            with open(pdf_path, "rb") as pdf_file:
                data = pdf_file.read()
                headers = {
                    "x-ms-blob-type": "BlockBlob",
                    "Content-Type": "application/pdf"
                }
                response = requests.put(blob_url, data=data, headers=headers)

                if response.status_code == 201:
                    logger.info(f"Successfully uploaded blob: {pdf_filename}")
                    return True, blob_pdf_path
                else:
                    logger.error(f"Failed to upload blob: {pdf_filename}. Status code: {response.status_code}")
                    return False

        except Exception as e:
            logger.error(f"Error uploading blob: {str(e)}")
            return False

    
    def extract_text_from_pdf(self, pdf_content):
      """Extract text from a PDF file content."""
      print('inside extract_text_from_pdf')
      text = ""
      try:
        # Create a PDF file object from bytes
        pdf_file = io.BytesIO(pdf_content)
        # Create PDF reader object
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        # Extract text from each page
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        # print(text)
        
              
      except Exception as e:
          raise Exception(f"Error extracting text from PDF: {str(e)}")
      
      return text
    
    def get_latest_blob_with_sas(self) -> tuple[str, str, str]:
        """
        Get the latest blob from the container with its SAS token.
        """
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            blobs = list(container_client.list_blobs())
            
            if not blobs:
                logger.error("No blobs found in container")
                raise Exception("No blobs found in container")

            latest_blob = max(blobs, key=lambda x: x.last_modified)
            latest_blob_name = latest_blob.name
            
            logger.info(f"Latest blob found: {latest_blob_name}, Last modified: {latest_blob.last_modified}")
            
            sas_token = self.generate_sas_token(container_name, latest_blob_name)
            blob_url = f"{account_url}/{container_name}/{latest_blob_name}?{sas_token}"

            response = requests.get(blob_url)
            if response.status_code != 200:
                raise Exception(f"Failed to download blob: {response.status_code}")
            
            # Extract text from PDF
            extracted_text = self.extract_text_from_pdf(response.content)
            # print(f'get_latest_blob_with_sas:{extracted_text}')
            
            return latest_blob_name, blob_url, extracted_text
                
        except Exception as e:
            logger.error(f"Error getting latest blob with SAS: {str(e)}")
            raise

    def format_jd_with_gpt(self, jd_text):
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

    def format_resume_with_gpt(self, resume_text: str) -> Dict[str, Any]:
      """
      Format resume text using GPT-4 into structured JSON
      """
      resume_text = resume_text.encode('utf-8', errors='ignore').decode('utf-8')

      system_message = """You are an AI that reformats resumes into structured JSON. 
      Extract all relevant information and return ONLY valid JSON without any additional text or explanation.
      Ensure the response can be parsed by json.loads(). Include all available skills, work experience, and education details."""

      prompt = f"""Please format the following resume into valid JSON using this exact structure:
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
                  "companyName": "",
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
      Resume text:
      {resume_text}
      """
      try:
          response = openai.ChatCompletion.create(
              engine=deployment_name,
              messages=[
                  {"role": "system", "content": system_message},
                  {"role": "user", "content": prompt}
              ],
              max_tokens=2000,
              temperature=0.7
          )

          response_text = response.choices[0].message.content.strip()          
          try:
              parsed_json = json.loads(response_text)
            #   parsed_json["processing_status"] = "COMPLETED"
            #   self.formatted_resume = parsed_json
              return parsed_json
          except json.JSONDecodeError as e:
              
              logger.error(f"Error parsing GPT response as JSON: {e}")
              logger.error(f"Raw response: {response_text}")
              return None

      except Exception as e:
          logger.error(f"Error in GPT API call: {e}")
          return None
      
    def get_company_info_with_llm(self, company_name: str) -> Dict[str, Any]:
        """
        Use GPT to identify and provide information about a company.
        
        Args:
            company_name (str): Name of the company to search for
            
        Returns:
            Dict[str, Any]: Company information and possible LinkedIn URL
        """
        try:
            system_message = """You are a knowledgeable assistant that helps identify companies and provide accurate information about them.
            For any company name provided:
            1. Identify the most likely matching real company
            2. Provide key information about the company
            3. Consider searching for the company website and LinkedIn/Google presence
            4. If multiple companies match, provide information about the most relevant one
            5. If you're not confident about the company match, indicate that in your response
            6. For Indian companies, specifically consider:
            - Professional body registrations (ICAI, etc.)
            - Local business directories
            - Company websites (usually ending in .co.in or .com)
            Return ONLY valid JSON without any additional text."""

            prompt = f"""Please provide information about this company: {company_name}
            
            Think about how you would search for this company online:
            1. Common website patterns (company.com, company.co.in)
            2. Professional directories and associations
            3. Business registries
            4. Location-specific listings
            
            Return the information in this exact JSON format:
            {{
                "company_info": {{
                    "Website": "Company website URL if available, or most likely URL pattern",
                    "description": "A brief description covering the key points about the company",
                    "industry": "Main industry",
                    "Company size": "Approximate number of employees",
                    "Headquarters": "Main headquarters location",
                    "type": "Type of company (e.g., Private, Public, etc.)",
                    "key_products_services": ["List of main products/services"],
                    "Founded": "Founding year if known, otherwise null",
                    "Specialties": ["Any notable facts about the company"]
                }}
            }}"""

            try:
                response = openai.ChatCompletion.create(
                    engine=deployment_name,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.7
                )

                response_text = response.choices[0].message.content.strip()
                
                try:
                    parsed_json = json.loads(response_text)
                    return parsed_json
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing GPT response as JSON: {e}")
                    logger.error(f"Raw response: {response_text}")
                    return None

            except Exception as e:
                logger.error(f"Error in GPT API call: {e}")
                return None

        except Exception as e:
            logger.error(f"Error getting company info with LLM: {str(e)}")
            return None
      
    def get_companies_info(self) -> Dict[str, Any]:
        """
        Get information about the two most recent companies using LLM.
        """
        try:
            if not self.formatted_resume:
                raise ValueError("No formatted resume data available. Please process the resume first.")
                
            work_experience = self.formatted_resume.get("workExperience", [])
            if not work_experience:
                raise ValueError("No work experience found in the formatted resume")

            companies = work_experience[:2]  # Get two most recent companies
            company_info = {}

            for company in companies:
                company_name = company.get("companyName")
                if not company_name:
                    continue

                # Get company information using LLM
                llm_info = self.get_company_info_with_llm(company_name)
                
                if llm_info:
                    company_info[company_name] = {
                        "llm_matched_info": llm_info
                    }
                else:
                    company_info[company_name] = {
                        "error": "Could not retrieve company information"
                    }

            # Save to JSON file
            output_filename = 'company_info_llm.json'
            with open(output_filename, 'w', encoding='utf-8') as output_file:
                json.dump(company_info, output_file, ensure_ascii=False, indent=4)
                
            logger.info(f"Company information saved to {output_filename}")
            return company_info

        except Exception as e:
            logger.error(f"Error in getting companies info: {str(e)}")
            return {"error": str(e)}
        

    def generate_similarity_scores(
        self,
        resume_text: Dict[str, Any],
        jd_data: Dict[str, Any],
        application_id: int
        ) -> Dict[str, Any]:
        """
        Generate similarity scores between processed resume and JD using GPT

        Args:
            resume_text: Dictionary containing resume fields (experience, skills, etc.)
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
            response = openai.ChatCompletion.create(
                engine=deployment_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt_template.format(
                        processed_jd=json.dumps(jd_data, indent=2),
                        processed_resume=json.dumps(resume_text, indent=2)
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
    

    def process_resume(self, pdf_filename: str) -> dict:
        """
        Main method to handle the complete resume processing workflow.
        """
        try:
            # Step 1: Upload PDF to blob storage
            upload_success, blob_pdf_url = self.upload_pdf_to_blob(pdf_filename)
            if not upload_success:
                raise Exception("Failed to upload PDF to blob storage")
            
            latest_blob_name, blob_url, extracted_text = self.get_latest_blob_with_sas()
            formatted_resume = self.format_resume_with_gpt(extracted_text)
            if formatted_resume is None:
              raise Exception("Failed to format resume with GPT")
            self.formatted_resume = formatted_resume
            company_info = self.get_companies_info()
            if company_info:
                formatted_resume['companyBackground'] = company_info

            return {
                "status": "success",
                "uploaded_file": pdf_filename,
                "latest_blob": latest_blob_name,
                "blob_pdf_url" : blob_pdf_url,
                "formatted_resume": formatted_resume

            }

        except Exception as e:
            logger.error(f"Error in resume processing workflow: {str(e)}")
            return {
                "status": "error",
                "error_message": str(e),
                "uploaded_file": pdf_filename
            }

# Testing functions for local development
def test_resume_processing():
    """
    Test function for local development and testing resume processing.
    """
    try:
        processor = CandidateJobEvaluator()
        
        # Test cases
        pdf_filename = 'AkshayRodi.pdf'
        result = processor.process_resume(pdf_filename)
        
        if result["status"] == "success":
            print("\nFormatted Resume (JSON):")
            print("-" * 50)
            print(json.dumps(result['formatted_resume'], indent=2))
            print(f"\nBlob Storage Path: {result['blob_pdf_url']}")
            print("Processing completed successfully!")
        else:
            print("\nProcessing Failed:")
            print(f"Error: {result['error_message']}")
        
        print("-" * 80)  # Separator between test cases
            
    except Exception as e:
        logger.error(f"Test execution error: {str(e)}")

if __name__ == "__main__":
    # Run tests when file is executed directly
    test_resume_processing()