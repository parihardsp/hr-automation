
import requests
import json
from app.core.logger_setup import setup_logger

# Set up the logger
logger = setup_logger()

def test_single_jd():
    """Test creating a single JD"""

    try:
        # Test data
        test_data = {
            "content": """
                Job Title: Python Backend Developer
                Location: Remote (India)
                Department: Engineering
                
                About the Role:
                We are looking for a Python Backend Developer to join our engineering team. The ideal candidate will have strong experience in FastAPI and SQL databases.
                
                Key Responsibilities:
                - Develop and maintain backend services using Python/FastAPI
                - Design and implement database schemas
                - Write clean, maintainable, and efficient code
                - Collaborate with frontend developers and other team members
                
                Required Skills:
                - 3+ years of Python development experience
                - Strong knowledge of FastAPI and SQLAlchemy
                - Experience with PostgreSQL and database design
                - Familiarity with Git and CI/CD pipelines
                
                Nice to Have:
                - Experience with Docker and Kubernetes
                - Knowledge of Redis and message queues
                - AWS/Azure cloud experience
                
                Benefits:
                - Competitive salary
                - Health insurance
                - Flexible working hours
                - Learning and development budget
            """.strip(),
            "user_id": "test_recruiter_1"
        }

        url = "http://localhost:8000/api/generated-jd"

        logger.info("Starting JD creation test...")
        logger.debug(f"Test data: {json.dumps(test_data, indent=2)}")

        # Make the request
        logger.info("Sending POST request to create JD...")
        response = requests.post(
            url,
            json=test_data,
            headers={"Content-Type": "application/json"}
        )

        # Log response
        logger.info(f"Received response with status code: {response.status_code}")
        logger.debug(f"Full response: {response.text}")

        if response.status_code == 201:
            logger.info("JD created successfully!")
            response_data = response.json()
            logger.info(f"Created JD ID: {response_data.get('jd_id')}")
        else:
            logger.error(f"Failed to create JD. Status code: {response.status_code}")
            logger.error(f"Error response: {response.text}")

    except requests.RequestException as e:
        logger.error(f"Network error occurred: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
    finally:
        # Clean up handlers
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)


if __name__ == "__main__":
    test_single_jd()