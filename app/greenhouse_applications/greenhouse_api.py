# # greenhouse_api.py
#
# import httpx
# from fastapi import HTTPException
# import logging
# from typing import Dict, Any
#
# logger = logging.getLogger(__name__)
#
# class GreenhouseService:
#     def __init__(self, board_token: str):
#         self.board_token = board_token
#         self.base_url = "https://boards-api.greenhouse.io/v1/boards"
#
#     async def fetch_job_content(self, job_id: int) -> Dict[str, Any]:
#         """
#         Fetch job content details from Greenhouse API
#         """
#         try:
#             logger.info(f"Fetching job content for job_id: {job_id}")
#             async with httpx.AsyncClient() as client:
#                 url = f"{self.base_url}/{self.board_token}/jobs/{job_id}"
#                 logger.debug(f"Making request to: {url}")
#
#                 response = await client.get(url)
#
#                 if response.status_code == 404:
#                     logger.error(f"Job not found in Greenhouse for job_id: {job_id}")
#                     raise HTTPException(status_code=404, detail="Job not found in Greenhouse")
#
#                 response.raise_for_status()
#                 job_content = response.json()
#                 logger.info(f"Successfully fetched job content for job_id: {job_id}")
#                 return job_content
#
#         except httpx.HTTPError as e:
#             logger.error(f"HTTP error occurred while fetching job content: {str(e)}")
#             raise HTTPException(status_code=503, detail=f"Error fetching job content from Greenhouse: {str(e)}")
#
#         except Exception as e:
#             logger.error(f"Unexpected error fetching job content: {str(e)}")
#             raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# greenhouse_api.py

import json
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class GreenhouseService:
    def __init__(self, board_token: str):
        self.board_token = board_token
        self.mock_data_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'mock_data',
            'mock_job_content.json'
        )

    def _load_mock_data(self) -> Dict[str, Any]:
        """Load mock data from JSON file"""
        try:
            with open(self.mock_data_path, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            logger.error(f"Mock data file not found at: {self.mock_data_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in mock data file: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error loading mock data: {str(e)}")
            raise

    async def fetch_job_content(self, job_id: int) -> Dict[str, Any]:
        """
        Return mock job content from JSON file
        """
        try:
            logger.info(f"Fetching mock job content for job_id: {job_id}")

            # Load mock data from JSON file
            mock_data = self._load_mock_data()

            # Modify the mock data to use the provided job_id
            mock_data["id"] = job_id
            mock_data["absolute_url"] = f"http://your.co/careers?gh_jid={job_id}"

            logger.info(f"Successfully returned mock job content for job_id: {job_id}")
            return mock_data

        except Exception as e:
            logger.error(f"Error returning mock job content: {str(e)}")
            raise Exception(f"Error with mock job content: {str(e)}")