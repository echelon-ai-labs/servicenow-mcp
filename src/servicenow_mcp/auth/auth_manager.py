"""
Authentication manager for the ServiceNow MCP server.
"""

import base64
import logging
import time
from typing import Dict, Optional

import requests

from servicenow_mcp.utils.config import AuthConfig, AuthType

logger = logging.getLogger(__name__)


class AuthManager:
    """
    Authentication manager for ServiceNow API.

    This class handles authentication with the ServiceNow API using
    Basic, API key, or OAuth authentication.
    """

    def __init__(self, config: AuthConfig, instance_url: Optional[str] = None):
        """
        Initialize the authentication manager.

        Args:
            config: Authentication configuration.
            instance_url: ServiceNow instance URL.
        """
        self.config = config
        self.instance_url = instance_url
        self.token: Optional[str] = None
        self.token_type: Optional[str] = None  # Fixed: Should be Optional[str]
        self.refresh_token: Optional[str] = None
        self.expires_at: float = 0  # epoch timestamp
        self.refresh_token_expires_at: float = 0  # refresh token expiry

    def get_headers(self) -> Dict[str, str]:
        """
        Get the authentication headers for API requests.

        Returns:
            Dict[str, str]: Headers to include in API requests.
        """
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        if self.config.type == AuthType.BASIC:
            if not self.config.basic:
                raise ValueError("Basic auth configuration is required")

            auth_str = f"{self.config.basic.username}:{self.config.basic.password}"
            encoded = base64.b64encode(auth_str.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"

        elif self.config.type == AuthType.OAUTH:
            if not self.token or time.time() >= self.expires_at:
                self._get_oauth_token()
            headers["Authorization"] = f"{self.token_type} {self.token}"

        elif self.config.type == AuthType.API_KEY:
            if not self.config.api_key:
                raise ValueError("API key configuration is required")
            headers[self.config.api_key.header_name] = self.config.api_key.api_key

        return headers

    def _get_oauth_token(self):
        """
        Get or refresh an OAuth token from ServiceNow.

        Raises:
            ValueError: If OAuth configuration is missing or token request fails.
        """
        if not self.config.oauth:
            raise ValueError("OAuth configuration is required")

        oauth_config = self.config.oauth
        token_url = oauth_config.token_url
        if not token_url:
            # Build default token URL from instance_url
            if not self.instance_url:
                raise ValueError("Instance URL is required to build token URL")
            instance_parts = self.instance_url.split(".")
            if len(instance_parts) < 2:
                raise ValueError(f"Invalid instance URL: {self.instance_url}")
            instance_name = instance_parts[0].split("//")[-1]
            token_url = f"https://{instance_name}.service-now.com/oauth_token.do"

        # Prepare Authorization header
        auth_str = f"{oauth_config.client_id}:{oauth_config.client_secret}"
        auth_header = base64.b64encode(auth_str.encode()).decode()
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # Check if refresh token is valid and available
        if (self.refresh_token and
            time.time() < self.refresh_token_expires_at):
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            }
            logger.info("Using refresh token for OAuth")
        else:
            # Use password grant if no valid refresh token
            if not oauth_config.username or not oauth_config.password:
                raise ValueError("Username and password are required for OAuth authentication")
            data = {
                "grant_type": "password",
                "username": oauth_config.username,
                "password": oauth_config.password,
            }
            # Clear expired refresh token
            self.refresh_token = None
            self.refresh_token_expires_at = 0
            logger.info("Using password grant for OAuth")

        try:
            response = requests.post(token_url, headers=headers, data=data, timeout=30)
            response.raise_for_status()
            token_data = response.json()

            self.token = token_data.get("access_token")
            self.token_type = token_data.get("token_type", "Bearer")

            expires_in = token_data.get("expires_in", 1799)  # default 30 min
            self.expires_at = time.time() + expires_in - 30  # refresh early

            # Handle refresh token and its expiry
            new_refresh_token = token_data.get("refresh_token")
            if new_refresh_token:
                self.refresh_token = new_refresh_token
                # ServiceNow refresh tokens typically expire in 24 hours
                refresh_expires_in = token_data.get("refresh_expires_in", 86400)  # 24 hours default
                self.refresh_token_expires_at = time.time() + refresh_expires_in - 300  # refresh 5 min early

            if not self.token:
                raise ValueError("No access token in response")

            logger.info("Successfully obtained OAuth token")

        except requests.RequestException as e:
            logger.error(f"Failed to get OAuth token: {e}")
            raise ValueError(f"Failed to get OAuth token: {e}")

    def refresh_token_method(self):  # Fixed: Renamed to avoid conflict
        """Force refresh if using OAuth authentication."""
        if self.config.type == AuthType.OAUTH:
            if not self.token or time.time() >= self.expires_at:
                self._get_oauth_token()