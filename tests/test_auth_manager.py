import unittest
from unittest.mock import MagicMock, patch

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import AuthConfig, AuthType, OAuthConfig


class TestAuthManagerLogging(unittest.TestCase):
    def setUp(self):
        self.auth_config = AuthConfig(
            type=AuthType.OAUTH,
            oauth=OAuthConfig(
                client_id="client-id",
                client_secret="client-secret",
                username="user",
                password="pass",
                token_url="https://example.service-now.com/oauth_token.do",
            ),
        )
        self.auth_manager = AuthManager(self.auth_config, "https://example.service-now.com")

    @patch("requests.post")
    def test_oauth_success_does_not_log_token_values(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "SECRET_ACCESS_TOKEN",
            "refresh_token": "SECRET_REFRESH_TOKEN",
            "token_type": "Bearer",
        }
        mock_response.text = (
            '{"access_token":"SECRET_ACCESS_TOKEN","refresh_token":"SECRET_REFRESH_TOKEN"}'
        )
        mock_post.return_value = mock_response

        with self.assertLogs("servicenow_mcp.auth.auth_manager", level="INFO") as logs:
            self.auth_manager._get_oauth_token()

        log_text = "\n".join(logs.output)
        self.assertNotIn("SECRET_ACCESS_TOKEN", log_text)
        self.assertNotIn("SECRET_REFRESH_TOKEN", log_text)
        self.assertEqual(self.auth_manager.token, "SECRET_ACCESS_TOKEN")
        self.assertEqual(self.auth_manager.token_type, "Bearer")

    @patch("requests.post")
    def test_oauth_fallback_flow_does_not_log_token_values(self, mock_post):
        failed_response = MagicMock()
        failed_response.status_code = 401
        failed_response.json.return_value = {
            "error": "invalid_client",
            "error_description": "bad client SECRET_ACCESS_TOKEN",
        }
        failed_response.text = '{"error":"invalid_client","error_description":"bad client SECRET_ACCESS_TOKEN"}'

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "access_token": "SECRET_ACCESS_TOKEN",
            "token_type": "Bearer",
        }
        success_response.text = '{"access_token":"SECRET_ACCESS_TOKEN","token_type":"Bearer"}'

        mock_post.side_effect = [failed_response, success_response]

        with self.assertLogs("servicenow_mcp.auth.auth_manager", level="INFO") as logs:
            self.auth_manager._get_oauth_token()

        log_text = "\n".join(logs.output)
        self.assertNotIn("SECRET_ACCESS_TOKEN", log_text)
        self.assertIn("invalid_client", log_text)
        self.assertEqual(mock_post.call_count, 2)
        self.assertEqual(self.auth_manager.token, "SECRET_ACCESS_TOKEN")


if __name__ == "__main__":
    unittest.main()
