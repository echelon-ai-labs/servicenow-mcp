"""
Extended tests for auth_manager.py targeting uncovered lines.
Missing lines: 52, 58-68, 79-81, 91, 97-103, 154-160, 164-165
"""

import unittest
from unittest.mock import MagicMock, patch

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import (
    ApiKeyConfig,
    AuthConfig,
    AuthType,
    BasicAuthConfig,
    OAuthConfig,
)


class TestAuthManagerGetHeaders(unittest.TestCase):
    """Tests for AuthManager.get_headers covering uncovered branches."""

    def test_basic_auth_missing_config_raises(self):
        """Line 52: basic auth with no BasicAuthConfig raises ValueError."""
        config = AuthConfig(type=AuthType.BASIC, basic=None)
        manager = AuthManager(config)
        with self.assertRaises(ValueError, msg="Basic auth configuration is required"):
            manager.get_headers()

    def test_api_key_auth_returns_headers(self):
        """Lines 58-68: API key auth type adds header_name to headers."""
        api_key_config = ApiKeyConfig(header_name="X-API-Key", api_key="my-secret-key")
        config = AuthConfig(type=AuthType.API_KEY, api_key=api_key_config)
        manager = AuthManager(config)
        headers = manager.get_headers()
        self.assertIn("X-API-Key", headers)
        self.assertEqual(headers["X-API-Key"], "my-secret-key")
        self.assertIn("Accept", headers)
        self.assertIn("Content-Type", headers)

    def test_api_key_missing_config_raises(self):
        """Line 65-66: API key auth with no ApiKeyConfig raises ValueError."""
        config = AuthConfig(type=AuthType.API_KEY, api_key=None)
        manager = AuthManager(config)
        with self.assertRaises(ValueError, msg="API key configuration is required"):
            manager.get_headers()

    @patch("requests.post")
    def test_oauth_get_headers_calls_get_oauth_token(self, mock_post):
        """Lines 58-62: OAuth auth calls _get_oauth_token when no token cached."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "tok", "token_type": "Bearer"}
        mock_post.return_value = mock_response

        config = AuthConfig(
            type=AuthType.OAUTH,
            oauth=OAuthConfig(
                client_id="cid",
                client_secret="csec",
                username="user",
                password="pass",
                token_url="https://example.service-now.com/oauth_token.do",
            ),
        )
        manager = AuthManager(config, "https://example.service-now.com")
        headers = manager.get_headers()
        self.assertIn("Authorization", headers)
        self.assertIn("Bearer tok", headers["Authorization"])


class TestExtractOAuthErrorCode(unittest.TestCase):
    """Tests for AuthManager._extract_oauth_error_code."""

    def _make_oauth_manager(self):
        config = AuthConfig(
            type=AuthType.OAUTH,
            oauth=OAuthConfig(
                client_id="cid",
                client_secret="csec",
                username="user",
                password="pass",
            ),
        )
        return AuthManager(config)

    def test_non_json_response_returns_non_json_response(self):
        """Lines 79-81: response.json() raises ValueError → return 'non_json_response'."""
        manager = self._make_oauth_manager()
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("No JSON")
        result = manager._extract_oauth_error_code(mock_response)
        self.assertEqual(result, "non_json_response")

    def test_json_response_with_error_key(self):
        """Non-exception path: JSON response with 'error' key."""
        manager = self._make_oauth_manager()
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "invalid_client"}
        result = manager._extract_oauth_error_code(mock_response)
        self.assertEqual(result, "invalid_client")

    def test_json_response_without_error_key(self):
        """JSON response with no 'error' key returns 'unknown_error'."""
        manager = self._make_oauth_manager()
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        result = manager._extract_oauth_error_code(mock_response)
        self.assertEqual(result, "unknown_error")


class TestGetOAuthToken(unittest.TestCase):
    """Tests for AuthManager._get_oauth_token covering uncovered branches."""

    def test_missing_oauth_config_raises(self):
        """Line 91: no oauth config raises ValueError."""
        config = AuthConfig(type=AuthType.OAUTH, oauth=None)
        manager = AuthManager(config, "https://example.service-now.com")
        with self.assertRaises(ValueError, msg="OAuth configuration is required"):
            manager._get_oauth_token()

    @patch("requests.post")
    def test_token_url_derived_from_instance_url(self, mock_post):
        """Lines 97-103: no explicit token_url, derive from instance_url."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "tok", "token_type": "Bearer"}
        mock_post.return_value = mock_response

        config = AuthConfig(
            type=AuthType.OAUTH,
            oauth=OAuthConfig(
                client_id="cid",
                client_secret="csec",
                username="user",
                password="pass",
                token_url=None,
            ),
        )
        manager = AuthManager(config, "https://myinstance.service-now.com")
        manager._get_oauth_token()

        called_url = mock_post.call_args[0][0]
        self.assertEqual(called_url, "https://myinstance.service-now.com/oauth_token.do")
        self.assertEqual(manager.token, "tok")

    def test_no_token_url_and_no_instance_url_raises(self):
        """Lines 97-98: no token_url and no instance_url raises ValueError."""
        config = AuthConfig(
            type=AuthType.OAUTH,
            oauth=OAuthConfig(
                client_id="cid",
                client_secret="csec",
                username="user",
                password="pass",
                token_url=None,
            ),
        )
        manager = AuthManager(config, instance_url=None)
        with self.assertRaises(ValueError, msg="Instance URL is required"):
            manager._get_oauth_token()

    def test_invalid_instance_url_raises(self):
        """Lines 100-101: instance_url with too few parts raises ValueError."""
        config = AuthConfig(
            type=AuthType.OAUTH,
            oauth=OAuthConfig(
                client_id="cid",
                client_secret="csec",
                username="user",
                password="pass",
                token_url=None,
            ),
        )
        manager = AuthManager(config, instance_url="https://localhost")
        with self.assertRaises(ValueError, msg="Invalid instance URL"):
            manager._get_oauth_token()

    @patch("requests.post")
    def test_both_grants_fail_raises_value_error(self, mock_post):
        """Lines 154-160: both client_credentials and password grants fail → ValueError."""
        fail_response = MagicMock()
        fail_response.status_code = 401
        fail_response.json.return_value = {"error": "invalid_client"}
        mock_post.return_value = fail_response

        config = AuthConfig(
            type=AuthType.OAUTH,
            oauth=OAuthConfig(
                client_id="cid",
                client_secret="csec",
                username="user",
                password="pass",
                token_url="https://example.service-now.com/oauth_token.do",
            ),
        )
        manager = AuthManager(config, "https://example.service-now.com")
        with self.assertRaises(ValueError, msg="Failed to get OAuth token"):
            manager._get_oauth_token()
        self.assertEqual(mock_post.call_count, 2)

    @patch("requests.post")
    def test_client_credentials_fails_no_username_raises(self, mock_post):
        """Lines 136-160: client_credentials fails; empty username → no password fallback → raises."""
        fail_response = MagicMock()
        fail_response.status_code = 400
        fail_response.json.return_value = {"error": "unsupported_grant_type"}
        mock_post.return_value = fail_response

        config = AuthConfig(
            type=AuthType.OAUTH,
            oauth=OAuthConfig(
                client_id="cid",
                client_secret="csec",
                username="",
                password="",
                token_url="https://example.service-now.com/oauth_token.do",
            ),
        )
        manager = AuthManager(config, "https://example.service-now.com")
        with self.assertRaises(ValueError):
            manager._get_oauth_token()
        self.assertEqual(mock_post.call_count, 1)


class TestRefreshToken(unittest.TestCase):
    """Tests for AuthManager.refresh_token."""

    @patch("requests.post")
    def test_refresh_token_oauth_calls_get_oauth_token(self, mock_post):
        """Lines 164-165: refresh_token with OAuth type calls _get_oauth_token."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "newtoken", "token_type": "Bearer"}
        mock_post.return_value = mock_response

        config = AuthConfig(
            type=AuthType.OAUTH,
            oauth=OAuthConfig(
                client_id="cid",
                client_secret="csec",
                username="user",
                password="pass",
                token_url="https://example.service-now.com/oauth_token.do",
            ),
        )
        manager = AuthManager(config, "https://example.service-now.com")
        manager.token = "oldtoken"
        manager.refresh_token()
        self.assertEqual(manager.token, "newtoken")

    def test_refresh_token_non_oauth_does_nothing(self):
        """refresh_token with non-OAuth type is a no-op."""
        config = AuthConfig(
            type=AuthType.BASIC,
            basic=BasicAuthConfig(username="u", password="p"),
        )
        manager = AuthManager(config)
        manager.refresh_token()
        self.assertIsNone(manager.token)


if __name__ == "__main__":
    unittest.main()
