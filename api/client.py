import requests
import json
from typing import Dict, Any, Optional

from config.config import BASE_URL
from utils.logger import get_logger

logger = get_logger(__name__)

class ApiClient:
    """
    Reusable HTTP Client for interacting with the API.
    Handles automatic header injection, authentication, and logging.
    """

    def __init__(self, token: Optional[str] = None):
        """
        Initialize the ApiClient with an optional bearer token.
        
        Args:
            token (str, optional): Bearer token for authorization.
        """
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json"
        })
        if token:
            self.session.headers.update({
                "Authorization": f"Bearer {token}"
            })

    @staticmethod
    def generate_token(client_id: str, client_secret: str, payload_template: dict) -> str:
        """
        Fetches a new JWT token using the provided credentials.
        """
        payload = payload_template.copy()
        payload["clientId"] = client_id
        payload["clientSecret"] = client_secret
        
        url = f"{BASE_URL}/api/v1/auth"
        logger.info(f"Executing POST {url} to get token")
        
        temp_session = requests.Session()
        temp_session.headers.update({"Content-Type": "application/json"})
        response = temp_session.post(url, json=payload)
        
        logger.info(f"Auth Status Code: {response.status_code}")
        try:
            logger.debug(f"Auth Response: {json.dumps(response.json(), indent=2)}")
        except ValueError:
            logger.debug(f"Auth Response: {response.text}")
            
        response.raise_for_status()
        
        data = response.json()
        token = data.get("access_token") or data.get("token") or data.get("data", {}).get("token") or data.get("data", {}).get("access_token")
        
        if not token:
            logger.error("Token not found in authentication response")
            raise ValueError("Token not found in authentication response")
            
        return token

    def _log_request_response(self, response: requests.Response, payload: Optional[Dict] = None):
        """
        Internal method to log the complete HTTP cycle.
        """
        req = response.request
        logger.info(f"--- HTTP REQUEST ---")
        logger.info(f"Method: {req.method}")
        logger.info(f"URL: {req.url}")
        if payload:
            logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
        
        logger.info(f"--- HTTP RESPONSE ---")
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Elapsed Time: {response.elapsed.total_seconds()}s")
        try:
            logger.debug(f"Response Body: {json.dumps(response.json(), indent=2)}")
        except ValueError:
            logger.debug(f"Response Body: {response.text}")

    def get(self, endpoint: str, params: Optional[Dict] = None) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        logger.info(f"Executing GET {url}")
        response = self.session.get(url, params=params)
        self._log_request_response(response)
        return response

    def post(self, endpoint: str, payload: Dict[str, Any]) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        logger.info(f"Executing POST {url}")
        response = self.session.post(url, json=payload)
        self._log_request_response(response, payload)
        return response

    def put(self, endpoint: str, payload: Dict[str, Any]) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        logger.info(f"Executing PUT {url}")
        response = self.session.put(url, json=payload)
        self._log_request_response(response, payload)
        return response

    def delete(self, endpoint: str) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        logger.info(f"Executing DELETE {url}")
        response = self.session.delete(url)
        self._log_request_response(response)
        return response