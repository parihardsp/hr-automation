import json
import requests
import os
import hmac
import hashlib
from app.core.logger_setup import setup_logger

logger = setup_logger(__name__)

def generate_signature(secret_key: str, message_body: bytes) -> str:
    return hmac.new(secret_key.encode(), message_body, hashlib.sha256).hexdigest()


def send_webhook_request():
    webhook_url = "http://127.0.0.1:8000/api/simulate_webhook"

    # Get the current directory of the script
    current_dir = os.path.dirname(os.path.abspath(__file__))

<<<<<<< HEAD:app/greenhouse_applications/send_webhook_request.py
    # Build the path to the 'dummy_data_2.json' inside 'Dummy Data' folder
    dummy_data_path = os.path.join(current_dir, 'Dummy Data', 'dummy_data_2.json')
=======
    # Build the path to the 'gh_app_data_2.json' inside 'Dummy Data' folder
    dummy_data_path = os.path.join(current_dir, 'Samples', 'gh_app_data.json')
>>>>>>> 419e0c9ee2b9d157058b141adb33761e9163ff4a:app/gh_integration/send_webhook_request.py

    try:
        with open(dummy_data_path, 'r') as f:
            data = json.load(f)
            logger.info("Dummy data loaded successfully.")
    except Exception as e:
        logger.error(f"Error reading dummy data: {str(e)}")
        return

    json_data = json.dumps(data)
    message_body = json_data.encode()

    secret_key = 'your_secret_key_here'
    signature = generate_signature(secret_key, message_body)
    logger.info("Signature generated.")

    headers = {
        'Content-Type': 'application/json',
        'Signature': signature
    }

    try:
        response = requests.post(webhook_url, data=json_data, headers=headers)
        logger.info(f"Response Status Code: {response.status_code}")

        try:
            logger.info(f"Response Body: {response.json()}")
        except ValueError:
            logger.warning("Response Body is not valid JSON: %s", response.text)
    except Exception as e:
        logger.error(f"Error sending request: {str(e)}")


if __name__ == "__main__":
    send_webhook_request()
