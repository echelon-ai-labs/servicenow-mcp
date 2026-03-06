
import unittest
from unittest.mock import MagicMock, patch, call
import requests
from servicenow_mcp.tools.csm_tools import (
    list_accounts,
    list_locations,
    list_products,
    get_cases_by_account,
    get_cases_by_location,
    get_cases_by_product,
    get_cases_by_integration,
    get_case_history,
    ListAccountsParams,
    ListLocationsParams,
    ListProductsParams,
    GetCasesByAccountParams,
    GetCasesByLocationParams,
    GetCasesByProductParams,
    GetCasesByIntegrationParams,
    GetCaseHistoryParams,
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


SAMPLE_ACCOUNT = {
    "sys_id": "acct001",
    "name": "Aramark Inc.",
    "account_code": "ARAM",
    "city": "Philadelphia",
    "state": "PA",
    "country": "US",
}

SAMPLE_LOCATION = {
    "sys_id": "loc001",
    "name": "Wrigley Field - Section 200",
    "company": "Levy Restaurants",
    "city": "Chicago",
    "state": "IL",
    "country": "US",
}

SAMPLE_PRODUCT = {
    "sys_id": "prod001",
    "name": "Mashgin Kiosk - Aramark HQ",
    "account": "Aramark Inc.",
    "product_model": "Kiosk",
}

SAMPLE_CASE = {
    "sys_id": "case001",
    "number": "CS0017600",
    "short_description": "Aramark | Wrigley Field | Shift4 Inquiry",
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

SAMPLE_CASE_HISTORY = {
    "sys_id": "case001",
    "number": "CS0008423",
    "short_description": "Aramark | Origin issue",
    "description": "Details here",
    "state": "Closed",
    "priority": "2 - High",
    "assigned_to": "John Doe",
    "company": "Aramark Inc.",
    "assignment_group": "CSM Team",
    "comments": "2025-01-15 - Customer called in\n2025-01-16 - Escalated",
    "work_notes": "2025-01-15 - Investigated root cause",
    "close_notes": "Resolved by firmware update",
    "opened_at": "2025-01-14 09:00:00",
    "closed_at": "2025-01-20 17:00:00",
    "resolved_at": "2025-01-19 15:00:00",
}


class TestListAccounts(unittest.TestCase):

    @patch('servicenow_mcp.tools.csm_tools.requests.get')
    def test_list_accounts_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": [SAMPLE_ACCOUNT]}
        mock_get.return_value = mock_response

        result = list_accounts(_make_config(), _make_auth(), ListAccountsParams())

        self.assertTrue(result["success"])
        self.assertEqual(len(result["accounts"]), 1)
        self.assertEqual(result["accounts"][0]["name"], "Aramark Inc.")
        call_args = mock_get.call_args
        self.assertIn("/table/customer_account", call_args[0][0])

    @patch('servicenow_mcp.tools.csm_tools.requests.get')
    def test_list_accounts_with_name_filter(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": [SAMPLE_ACCOUNT]}
        mock_get.return_value = mock_response

        result = list_accounts(_make_config(), _make_auth(), ListAccountsParams(name_filter="Aramark"))

        self.assertTrue(result["success"])
        query = mock_get.call_args[1]["params"]["sysparm_query"]
        self.assertIn("nameLIKEAramark", query)

    @patch('servicenow_mcp.tools.csm_tools.requests.get')
    def test_list_accounts_empty(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": []}
        mock_get.return_value = mock_response

        result = list_accounts(_make_config(), _make_auth(), ListAccountsParams())

        self.assertTrue(result["success"])
        self.assertEqual(result["accounts"], [])
        self.assertEqual(result["message"], "Found 0 accounts")

    @patch('servicenow_mcp.tools.csm_tools.requests.get')
    def test_list_accounts_request_error(self, mock_get):
        mock_get.side_effect = requests.RequestException("Connection timeout")

        result = list_accounts(_make_config(), _make_auth(), ListAccountsParams())

        self.assertFalse(result["success"])
        self.assertIn("Failed to list accounts", result["message"])


class TestListLocations(unittest.TestCase):

    @patch('servicenow_mcp.tools.csm_tools.requests.get')
    def test_list_locations_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": [SAMPLE_LOCATION]}
        mock_get.return_value = mock_response

        result = list_locations(_make_config(), _make_auth(), ListLocationsParams())

        self.assertTrue(result["success"])
        self.assertEqual(len(result["locations"]), 1)
        self.assertEqual(result["locations"][0]["name"], "Wrigley Field - Section 200")
        call_args = mock_get.call_args
        self.assertIn("/table/cmn_location", call_args[0][0])

    @patch('servicenow_mcp.tools.csm_tools.requests.get')
    def test_list_locations_with_account_filter(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": [SAMPLE_LOCATION]}
        mock_get.return_value = mock_response

        result = list_locations(_make_config(), _make_auth(), ListLocationsParams(account="Levy"))

        self.assertTrue(result["success"])
        query = mock_get.call_args[1]["params"]["sysparm_query"]
        self.assertIn("companyLIKELevy", query)

    @patch('servicenow_mcp.tools.csm_tools.requests.get')
    def test_list_locations_with_name_filter(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": [SAMPLE_LOCATION]}
        mock_get.return_value = mock_response

        result = list_locations(_make_config(), _make_auth(), ListLocationsParams(name_filter="Wrigley"))

        self.assertTrue(result["success"])
        query = mock_get.call_args[1]["params"]["sysparm_query"]
        self.assertIn("nameLIKEWrigley", query)


class TestListProducts(unittest.TestCase):

    @patch('servicenow_mcp.tools.csm_tools.requests.get')
    def test_list_products_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": [SAMPLE_PRODUCT]}
        mock_get.return_value = mock_response

        result = list_products(_make_config(), _make_auth(), ListProductsParams())

        self.assertTrue(result["success"])
        self.assertEqual(len(result["products"]), 1)
        self.assertEqual(result["products"][0]["name"], "Mashgin Kiosk - Aramark HQ")
        call_args = mock_get.call_args
        self.assertIn("/table/sn_install_base_sold_product", call_args[0][0])

    @patch('servicenow_mcp.tools.csm_tools.requests.get')
    def test_list_products_with_account_filter(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": [SAMPLE_PRODUCT]}
        mock_get.return_value = mock_response

        result = list_products(_make_config(), _make_auth(), ListProductsParams(account="Aramark"))

        self.assertTrue(result["success"])
        query = mock_get.call_args[1]["params"]["sysparm_query"]
        self.assertIn("accountLIKEAramark", query)

    @patch('servicenow_mcp.tools.csm_tools.requests.get')
    def test_list_products_with_product_name_filter(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": [SAMPLE_PRODUCT]}
        mock_get.return_value = mock_response

        result = list_products(_make_config(), _make_auth(), ListProductsParams(product_name="Kiosk"))

        self.assertTrue(result["success"])
        query = mock_get.call_args[1]["params"]["sysparm_query"]
        self.assertIn("nameLIKEKiosk", query)


class TestGetCasesByAccount(unittest.TestCase):

    @patch('servicenow_mcp.tools.csm_tools.requests.get')
    def test_get_cases_by_account_success(self, mock_get):
        # First call: account lookup; second call: case search
        mock_acct_response = MagicMock()
        mock_acct_response.status_code = 200
        mock_acct_response.json.return_value = {"result": [{"sys_id": "acct001", "name": "Aramark Inc."}]}

        mock_case_response = MagicMock()
        mock_case_response.status_code = 200
        mock_case_response.json.return_value = {"result": [SAMPLE_CASE]}

        mock_get.side_effect = [mock_acct_response, mock_case_response]

        params = GetCasesByAccountParams(account_name="Aramark")
        result = get_cases_by_account(_make_config(), _make_auth(), params)

        self.assertTrue(result["success"])
        self.assertEqual(len(result["cases"]), 1)
        self.assertIn("Aramark", result["message"])
        # Verify two API calls were made
        self.assertEqual(mock_get.call_count, 2)
        # First call to customer_account
        self.assertIn("/table/customer_account", mock_get.call_args_list[0][0][0])
        # Second call to task table
        self.assertIn("/table/task", mock_get.call_args_list[1][0][0])

    @patch('servicenow_mcp.tools.csm_tools.requests.get')
    def test_get_cases_by_account_not_found(self, mock_get):
        mock_acct_response = MagicMock()
        mock_acct_response.status_code = 200
        mock_acct_response.json.return_value = {"result": []}
        mock_get.return_value = mock_acct_response

        params = GetCasesByAccountParams(account_name="NonExistentCorp")
        result = get_cases_by_account(_make_config(), _make_auth(), params)

        self.assertFalse(result["success"])
        self.assertIn("Account not found", result["message"])
        self.assertEqual(result["cases"], [])
        # Only one API call made (account lookup, no case search)
        self.assertEqual(mock_get.call_count, 1)

    @patch('servicenow_mcp.tools.csm_tools.requests.get')
    def test_get_cases_by_account_with_filters(self, mock_get):
        mock_acct_response = MagicMock()
        mock_acct_response.status_code = 200
        mock_acct_response.json.return_value = {"result": [{"sys_id": "acct001", "name": "Aramark Inc."}]}

        mock_case_response = MagicMock()
        mock_case_response.status_code = 200
        mock_case_response.json.return_value = {"result": []}

        mock_get.side_effect = [mock_acct_response, mock_case_response]

        params = GetCasesByAccountParams(
            account_name="Aramark",
            state="New",
            priority="3 - Moderate",
            created_after="2025-01-01",
        )
        result = get_cases_by_account(_make_config(), _make_auth(), params)

        self.assertTrue(result["success"])
        case_query = mock_get.call_args_list[1][1]["params"]["sysparm_query"]
        self.assertIn("state=New", case_query)
        self.assertIn("priority=3 - Moderate", case_query)
        self.assertIn("sys_created_on>=2025-01-01", case_query)


class TestGetCasesByLocation(unittest.TestCase):

    @patch('servicenow_mcp.tools.csm_tools.requests.get')
    def test_get_cases_by_location_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": [SAMPLE_CASE]}
        mock_get.return_value = mock_response

        params = GetCasesByLocationParams(location_name="Wrigley Field")
        result = get_cases_by_location(_make_config(), _make_auth(), params)

        self.assertTrue(result["success"])
        self.assertEqual(len(result["cases"]), 1)
        self.assertIn("Wrigley Field", result["message"])
        query = mock_get.call_args[1]["params"]["sysparm_query"]
        self.assertIn("short_descriptionLIKEWrigley Field", query)
        self.assertIn("sys_class_name=sn_customerservice_case", query)


class TestGetCasesByProduct(unittest.TestCase):

    @patch('servicenow_mcp.tools.csm_tools.requests.get')
    def test_get_cases_by_product_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": [SAMPLE_CASE]}
        mock_get.return_value = mock_response

        params = GetCasesByProductParams(product_name="Origin")
        result = get_cases_by_product(_make_config(), _make_auth(), params)

        self.assertTrue(result["success"])
        self.assertEqual(len(result["cases"]), 1)
        self.assertIn("Origin", result["message"])
        query = mock_get.call_args[1]["params"]["sysparm_query"]
        self.assertIn("short_descriptionLIKEOrigin", query)
        self.assertIn("descriptionLIKEOrigin", query)


class TestGetCasesByIntegration(unittest.TestCase):

    @patch('servicenow_mcp.tools.csm_tools.requests.get')
    def test_get_cases_by_integration_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": [SAMPLE_CASE]}
        mock_get.return_value = mock_response

        params = GetCasesByIntegrationParams(integration_name="Shift4")
        result = get_cases_by_integration(_make_config(), _make_auth(), params)

        self.assertTrue(result["success"])
        self.assertEqual(len(result["cases"]), 1)
        self.assertIn("Shift4", result["message"])
        query = mock_get.call_args[1]["params"]["sysparm_query"]
        self.assertIn("short_descriptionLIKEShift4", query)
        self.assertIn("descriptionLIKEShift4", query)


class TestGetCaseHistory(unittest.TestCase):

    @patch('servicenow_mcp.tools.csm_tools.requests.get')
    def test_get_case_history_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": [SAMPLE_CASE_HISTORY]}
        mock_get.return_value = mock_response

        params = GetCaseHistoryParams(case_number="CS0008423")
        result = get_case_history(_make_config(), _make_auth(), params)

        self.assertTrue(result["success"])
        self.assertEqual(result["case"]["number"], "CS0008423")
        self.assertIn("comments", result["case"])
        self.assertIn("Customer called in", result["case"]["comments"])
        self.assertIn("work_notes", result["case"])
        self.assertIn("close_notes", result["case"])
        self.assertIn("opened_at", result["case"])
        self.assertIn("closed_at", result["case"])
        query = mock_get.call_args[1]["params"]["sysparm_query"]
        self.assertIn("number=CS0008423", query)
        self.assertIn("sys_class_name=sn_customerservice_case", query)

    @patch('servicenow_mcp.tools.csm_tools.requests.get')
    def test_get_case_history_not_found(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": []}
        mock_get.return_value = mock_response

        params = GetCaseHistoryParams(case_number="CS9999999")
        result = get_case_history(_make_config(), _make_auth(), params)

        self.assertFalse(result["success"])
        self.assertIn("Case not found", result["message"])

    @patch('servicenow_mcp.tools.csm_tools.requests.get')
    def test_get_case_history_request_error(self, mock_get):
        mock_get.side_effect = requests.RequestException("Server error")

        params = GetCaseHistoryParams(case_number="CS0008423")
        result = get_case_history(_make_config(), _make_auth(), params)

        self.assertFalse(result["success"])
        self.assertIn("Failed to get case history", result["message"])

    @patch('servicenow_mcp.tools.csm_tools.requests.get')
    def test_get_case_history_assigned_to_dict(self, mock_get):
        case_with_dict_assigned = {
            **SAMPLE_CASE_HISTORY,
            "assigned_to": {"display_value": "John Doe", "value": "user123"},
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": [case_with_dict_assigned]}
        mock_get.return_value = mock_response

        params = GetCaseHistoryParams(case_number="CS0008423")
        result = get_case_history(_make_config(), _make_auth(), params)

        self.assertTrue(result["success"])
        self.assertEqual(result["case"]["assigned_to"], "John Doe")


if __name__ == '__main__':
    unittest.main()
