"""Importing all the necessary libraries"""
import os
import hmac
import hashlib
import logging
import json
import requests

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def generate_signature(secret_key: str, message_body: bytes) -> str:
    """Generate HMAC SHA256 signature."""
    return hmac.new(secret_key.encode(), message_body, hashlib.sha256).hexdigest()


def send_webhook_request():
    """Send a webhook request with a generated signature."""
    webhook_url = os.getenv('WEBHOOK_URL', 'http://127.0.0.1:8000/api/simulate_webhook')
    secret_key = os.getenv('SECRET_KEY', 'your_secret_key_here')

    # Get the current directory of the script
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Build the path to the 'dummy_data_3.json' inside 'Dummy Data' folder
    dummy_data_path = os.path.join(current_dir, 'Dummy Data', 'dummy_data_3.json')

    try:
        with open(dummy_data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info("Dummy data loaded successfully.")
    except FileNotFoundError:
        logger.error("Dummy data file not found.")
        return
    except json.JSONDecodeError:
        logger.error("Error decoding JSON from dummy data file.")
        return
    except Exception as e:
        logger.error("Unexpected error reading dummy data: %s", str(e))
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
        response = requests.post(webhook_url, data=json_data, headers=headers,timeout=120)
        logger.info("Response Status Code: %d", response.status_code)

        try:
            logger.info("Response Body: %s", response.json())
        except ValueError:
            logger.warning("Response Body is not valid JSON: %s", response.text)
    except requests.RequestException as e:
        logger.error("Error sending request: %s", str(e))

if __name__ == "__main__":
    send_webhook_request()
    