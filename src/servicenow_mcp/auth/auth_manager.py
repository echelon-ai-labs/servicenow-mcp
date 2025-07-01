"""
Authentication manager for the ServiceNow MCP server.
"""

import base64
import logging
import os
from typing import Dict, Optional

import requests
from requests.auth import HTTPBasicAuth

from servicenow_mcp.utils.config import AuthConfig, AuthType


logger = logging.getLogger(__name__)


class AuthManager:
    """
    Authentication manager for ServiceNow API.
    
    This class handles authentication with the ServiceNow API using
    different authentication methods.
    """
    
    def __init__(self, config: AuthConfig, instance_url: str = None):
        """
        Initialize the authentication manager.
        
        Args:
            config: Authentication configuration.
            instance_url: ServiceNow instance URL.
        """
        self.config = config
        self.instance_url = instance_url
        self.token: Optional[str] = None
        self.token_type: Optional[str] = None
    
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
            if not self.token:
                self._get_oauth_token()
            
            headers["Authorization"] = f"{self.token_type} {self.token}"
        
        elif self.config.type == AuthType.API_KEY:
            if not self.config.api_key:
                raise ValueError("API key configuration is required")
            
            headers[self.config.api_key.header_name] = self.config.api_key.api_key
        
        return headers
    
    def _get_oauth_token(self):
        """
        Get an OAuth token from ServiceNow.
        
        Raises:
            ValueError: If OAuth configuration is missing or token request fails.
        """
        if not self.config.oauth:
            raise ValueError("OAuth configuration is required")
        oauth_config = self.config.oauth

        # Determine token URL
        token_url = oauth_config.token_url
        if not token_url:
            if not self.instance_url:
                raise ValueError("Instance URL is required for OAuth authentication")
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

        # Try client_credentials grant first
        data_client_credentials = {
            "grant_type": "client_credentials"
        }
        
        logger.info("Attempting client_credentials grant...")
        response = requests.post(token_url, headers=headers, data=data_client_credentials)
        
        logger.info(f"client_credentials response status: {response.status_code}")
        logger.info(f"client_credentials response body: {response.text}")
        
        if response.status_code == 200:
            token_data = response.json()
            self.token = token_data.get("access_token")
            self.token_type = token_data.get("token_type", "Bearer")
            return

        # Try password grant if client_credentials failed
        if oauth_config.username and oauth_config.password:
            data_password = {
                "grant_type": "password",
                "username": oauth_config.username,
                "password": oauth_config.password
            }
            
            logger.info("Attempting password grant...")
            response = requests.post(token_url, headers=headers, data=data_password)
            
            logger.info(f"password grant response status: {response.status_code}")
            logger.info(f"password grant response body: {response.text}")
            
            if response.status_code == 200:
                token_data = response.json()
                self.token = token_data.get("access_token")
                self.token_type = token_data.get("token_type", "Bearer")
                return

        raise ValueError("Failed to get OAuth token using both client_credentials and password grants.")
    
    def refresh_token(self):
        """Refresh the OAuth token if using OAuth authentication."""
        if self.config.type == AuthType.OAUTH:
            self._get_oauth_token() 