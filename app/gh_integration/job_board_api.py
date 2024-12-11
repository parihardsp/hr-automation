"""
Module for simulating job content retrieval from Greenhouse API.

This module provides a SimulateJobUrl class that loads mock job content
from a JSON file, simulating API interactions for testing purposes.
"""
# pylint: disable=C0301

import json
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class SimulateJobUrl:
    """
    A class to simulate job content retrieval from a mock JSON file.

    This class provides methods to load and return mock job content,
    primarily used for testing and development purposes.
    """

    def __init__(self, board_token: str):
        """
        Initialize the SimulateJobUrl with a board token and mock data path.

        Args:
            board_token (str): Token for the job board.
        """
        self.board_token = board_token
        self.mock_data_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'Samples',
            'gh_job_content.json'
        )

    def _load_mock_data(self) -> Dict[str, Any]:
        """
        Load mock data from JSON file.

        Returns:
            Dict[str, Any]: Parsed JSON data from the mock file.

        Raises:
            FileNotFoundError: If the mock data file is not found.
            json.JSONDecodeError: If the JSON is invalid.
        """
        try:
            with open(self.mock_data_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            logger.error('Mock data file not found at: %s', self.mock_data_path)
            raise
        except json.JSONDecodeError as e:
            logger.error('Invalid JSON in mock data file: %s', str(e))
            raise
        except Exception as e:
            logger.error('Error loading mock data: %s', str(e))
            raise

    async def fetch_job_content(self, job_id: int) -> Dict[str, Any]:
        """
        Return mock job content from JSON file.

        Args:
            job_id (int): The ID of the job to retrieve.

        Returns:
            Dict[str, Any]: Mock job content with modified job ID.

        Raises:
            Exception: If there's an error retrieving mock job content.
        """
        try:
            logger.info('Fetching mock job content for job_id: %s', job_id)

            # Load mock data from JSON file
            mock_data = self._load_mock_data()

            # Modify the mock data to use the provided job_id
            mock_data["id"] = job_id
            mock_data["absolute_url"] = f"http://your.co/careers?gh_jid={job_id}"

            logger.info('Successfully returned mock job content for job_id: %s', job_id)
            return mock_data

        except Exception as e:
            logger.error('Error returning mock job content: %s', str(e))
            raise RuntimeError(f'Error with mock job content: {str(e)}') from e