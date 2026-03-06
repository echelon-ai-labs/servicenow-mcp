
import unittest
from unittest.mock import MagicMock, patch
import requests
from servicenow_mcp.tools.case_tools import (
    list_cases,
    get_case_by_number,
    search_cases,
    ListCasesParams,
    GetCaseByNumberParams,
    SearchCasesParams,
)
from servicenow_mcp.utils.config import ServerConfig, AuthConfig, AuthType, BasicAuthConfig
from servicenow_mcp.auth.auth_manager import AuthManager


def _make_config():
    auth_config = AuthConfig(type=AuthType.BASIC, basic=BasicAuthConfig(username='test', password='test'))
    return ServerConfig(instance_url="https://dev12345.service-now.com", auth=auth_config)


def _make_auth():
    auth_manager = MagicMock(spec=AuthManager)
    auth_manager.get_headers.return_value = {"Authorization": "Bearer FAKE_TOKEN"}
    return auth_manager


SAMPLE_CASE = {
    "sys_id": "abc123",
    "number": "CS0017600",
    "short_description": "Levy | Wrigley Field | Shift4 Inquiry",
    "description": "Customer needs help with Shift4 integration",
    "state": "New",
    "priority": "3 - Moderate",
    "category": "Inquiry",
    "subcategory": "General",
    "assigned_to": "Jane Smith",
    "contact_type": "email",
    "sys_created_on": "2025-01-15 10:00:00",
    "sys_updated_on": "2025-01-16 08:30:00",
}

SAMPLE_CASE_DICT_ASSIGNED = {
    **SAMPLE_CASE,
    "assigned_to": {"display_value": "Jane Smith", "value": "user_sys_id_123"},
}


class TestListCases(unittest.TestCase):

    @patch('servicenow_mcp.tools.case_tools.requests.get')
    def test_list_cases_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": [SAMPLE_CASE]}
        mock_get.return_value = mock_response

        result = list_cases(_make_config(), _make_auth(), ListCasesParams())

        self.assertTrue(result["success"])
        self.assertEqual(len(result["cases"]), 1)
        self.assertEqual(result["cases"][0]["number"], "CS0017600")
        # Verify query goes to task table with sys_class_name filter
        call_args = mock_get.call_args
        self.assertIn("/table/task", call_args[0][0])
        self.assertIn("sys_class_name=sn_customerservice_case", call_args[1]["params"]["sysparm_query"])

    @patch('servicenow_mcp.tools.case_tools.requests.get')
    def test_list_cases_with_filters(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": [SAMPLE_CASE]}
        mock_get.return_value = mock_response

        params = ListCasesParams(
            state="New",
            priority="3 - Moderate",
            category="Inquiry",
            contact_type="email",
            created_after="2025-01-01",
        )
        result = list_cases(_make_config(), _make_auth(), params)

        self.assertTrue(result["success"])
        query = mock_get.call_args[1]["params"]["sysparm_query"]
        self.assertIn("state=New", query)
        self.assertIn("priority=3 - Moderate", query)
        self.assertIn("category=Inquiry", query)
        self.assertIn("contact_type=email", query)
        self.assertIn("sys_created_on>=2025-01-01", query)

    @patch('servicenow_mcp.tools.case_tools.requests.get')
    def test_list_cases_empty_results(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": []}
        mock_get.return_value = mock_response

        result = list_cases(_make_config(), _make_auth(), ListCasesParams())

        self.assertTrue(result["success"])
        self.assertEqual(result["cases"], [])
        self.assertEqual(result["message"], "Found 0 cases")

    @patch('servicenow_mcp.tools.case_tools.requests.get')
    def test_list_cases_request_error(self, mock_get):
        mock_get.side_effect = requests.RequestException("Connection timeout")

        result = list_cases(_make_config(), _make_auth(), ListCasesParams())

        self.assertFalse(result["success"])
        self.assertIn("Failed to list cases", result["message"])
        self.assertEqual(result["cases"], [])

    @patch('servicenow_mcp.tools.case_tools.requests.get')
    def test_list_cases_limit_cap(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": []}
        mock_get.return_value = mock_response

        # Request 500 but should be capped at 200
        list_cases(_make_config(), _make_auth(), ListCasesParams(limit=500))

        call_params = mock_get.call_args[1]["params"]
        self.assertEqual(call_params["sysparm_limit"], 200)

    @patch('servicenow_mcp.tools.case_tools.requests.get')
    def test_list_cases_assigned_to_dict_handling(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": [SAMPLE_CASE_DICT_ASSIGNED]}
        mock_get.return_value = mock_response

        result = list_cases(_make_config(), _make_auth(), ListCasesParams())

        self.assertTrue(result["success"])
        self.assertEqual(result["cases"][0]["assigned_to"], "Jane Smith")


class TestGetCaseByNumber(unittest.TestCase):

    @patch('servicenow_mcp.tools.case_tools.requests.get')
    def test_get_case_by_number_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": [SAMPLE_CASE]}
        mock_get.return_value = mock_response

        params = GetCaseByNumberParams(case_number="CS0017600")
        result = get_case_by_number(_make_config(), _make_auth(), params)

        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "Case CS0017600 found")
        self.assertEqual(result["case"]["number"], "CS0017600")
        self.assertEqual(result["case"]["short_description"], "Levy | Wrigley Field | Shift4 Inquiry")
        # Verify query includes both sys_class_name and number
        query = mock_get.call_args[1]["params"]["sysparm_query"]
        self.assertIn("sys_class_name=sn_customerservice_case", query)
        self.assertIn("number=CS0017600", query)

    @patch('servicenow_mcp.tools.case_tools.requests.get')
    def test_get_case_by_number_not_found(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": []}
        mock_get.return_value = mock_response

        params = GetCaseByNumberParams(case_number="CS9999999")
        result = get_case_by_number(_make_config(), _make_auth(), params)

        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Case not found: CS9999999")

    @patch('servicenow_mcp.tools.case_tools.requests.get')
    def test_get_case_by_number_request_error(self, mock_get):
        mock_get.side_effect = requests.RequestException("Connection refused")

        params = GetCaseByNumberParams(case_number="CS0017600")
        result = get_case_by_number(_make_config(), _make_auth(), params)

        self.assertFalse(result["success"])
        self.assertIn("Failed to fetch case", result["message"])


class TestSearchCases(unittest.TestCase):

    @patch('servicenow_mcp.tools.case_tools.requests.get')
    def test_search_cases_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": [SAMPLE_CASE]}
        mock_get.return_value = mock_response

        params = SearchCasesParams(search_text="Shift4")
        result = search_cases(_make_config(), _make_auth(), params)

        self.assertTrue(result["success"])
        self.assertEqual(len(result["cases"]), 1)
        self.assertIn("Shift4", result["message"])
        # Verify LIKE search in query
        query = mock_get.call_args[1]["params"]["sysparm_query"]
        self.assertIn("short_descriptionLIKEShift4", query)
        self.assertIn("descriptionLIKEShift4", query)

    @patch('servicenow_mcp.tools.case_tools.requests.get')
    def test_search_cases_with_filters(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": []}
        mock_get.return_value = mock_response

        params = SearchCasesParams(
            search_text="Shift4",
            state="New",
            priority="3 - Moderate",
            created_after="2025-01-01",
        )
        result = search_cases(_make_config(), _make_auth(), params)

        self.assertTrue(result["success"])
        query = mock_get.call_args[1]["params"]["sysparm_query"]
        self.assertIn("state=New", query)
        self.assertIn("priority=3 - Moderate", query)
        self.assertIn("sys_created_on>=2025-01-01", query)

    @patch('servicenow_mcp.tools.case_tools.requests.get')
    def test_search_cases_limit_cap(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": []}
        mock_get.return_value = mock_response

        search_cases(_make_config(), _make_auth(), SearchCasesParams(search_text="test", limit=999))

        call_params = mock_get.call_args[1]["params"]
        self.assertEqual(call_params["sysparm_limit"], 200)

    @patch('servicenow_mcp.tools.case_tools.requests.get')
    def test_search_cases_request_error(self, mock_get):
        mock_get.side_effect = requests.RequestException("Server error")

        params = SearchCasesParams(search_text="test")
        result = search_cases(_make_config(), _make_auth(), params)

        self.assertFalse(result["success"])
        self.assertIn("Failed to search cases", result["message"])
        self.assertEqual(result["cases"], [])


if __name__ == '__main__':
    unittest.main()
