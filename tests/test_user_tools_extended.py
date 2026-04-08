"""Extended tests for user management tools — covers uncovered paths."""

import unittest
from unittest.mock import MagicMock, patch

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.tools.user_tools import (
    CreateUserParams,
    UpdateUserParams,
    GetUserParams,
    ListUsersParams,
    CreateGroupParams,
    UpdateGroupParams,
    AddGroupMembersParams,
    RemoveGroupMembersParams,
    ListGroupsParams,
    create_user,
    update_user,
    get_user,
    list_users,
    create_group,
    update_group,
    add_group_members,
    remove_group_members,
    list_groups,
)
from servicenow_mcp.utils.config import AuthConfig, AuthType, BasicAuthConfig, ServerConfig


class TestUserToolsExtended(unittest.TestCase):

    def setUp(self):
        self.config = ServerConfig(
            instance_url="https://dev12345.service-now.com",
            auth=AuthConfig(type=AuthType.BASIC, basic=BasicAuthConfig(username="test", password="test")),
        )
        self.auth = MagicMock(spec=AuthManager)
        self.auth.get_headers.return_value = {"Authorization": "Bearer FAKE"}

    # --- error paths ---

    @patch("servicenow_mcp.tools.user_tools.requests.post")
    def test_create_user_error(self, mock_post):
        from requests.exceptions import RequestException
        mock_post.side_effect = RequestException("fail")
        params = CreateUserParams(user_name="test.user", first_name="Test", last_name="User", email="t@t.com")
        result = create_user(self.config, self.auth, params)
        self.assertFalse(result.success)

    @patch("servicenow_mcp.tools.user_tools.requests.patch")
    def test_update_user_error(self, mock_patch):
        from requests.exceptions import RequestException
        mock_patch.side_effect = RequestException("fail")
        params = UpdateUserParams(user_id="u1", first_name="Updated")
        result = update_user(self.config, self.auth, params)
        self.assertFalse(result.success)

    @patch("servicenow_mcp.tools.user_tools.requests.get")
    def test_get_user_error(self, mock_get):
        from requests.exceptions import RequestException
        mock_get.side_effect = RequestException("fail")
        params = GetUserParams(user_name="admin")
        result = get_user(self.config, self.auth, params)
        self.assertFalse(result["success"])

    @patch("servicenow_mcp.tools.user_tools.requests.get")
    def test_list_users_error(self, mock_get):
        from requests.exceptions import RequestException
        mock_get.side_effect = RequestException("fail")
        params = ListUsersParams()
        result = list_users(self.config, self.auth, params)
        self.assertFalse(result["success"])

    @patch("servicenow_mcp.tools.user_tools.requests.post")
    def test_create_group_error(self, mock_post):
        from requests.exceptions import RequestException
        mock_post.side_effect = RequestException("fail")
        params = CreateGroupParams(name="TestGroup")
        result = create_group(self.config, self.auth, params)
        self.assertFalse(result.success)

    @patch("servicenow_mcp.tools.user_tools.requests.put")
    def test_update_group_error(self, mock_put):
        from requests.exceptions import RequestException
        mock_put.side_effect = RequestException("fail")
        params = UpdateGroupParams(group_id="g1", name="Updated")
        result = update_group(self.config, self.auth, params)
        self.assertFalse(result.success)

    @patch("servicenow_mcp.tools.user_tools.requests.post")
    @patch("servicenow_mcp.tools.user_tools.requests.get")
    def test_add_group_members_error(self, mock_get, mock_post):
        from requests.exceptions import RequestException
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": []}),
        )
        mock_post.side_effect = RequestException("fail")
        params = AddGroupMembersParams(group_id="g1", members=["u1"])
        result = add_group_members(self.config, self.auth, params)
        self.assertFalse(result.success)

    @patch("servicenow_mcp.tools.user_tools.requests.get")
    def test_remove_group_members_error(self, mock_get):
        from requests.exceptions import RequestException
        mock_get.side_effect = RequestException("fail")
        params = RemoveGroupMembersParams(group_id="g1", members=["u1"])
        result = remove_group_members(self.config, self.auth, params)
        self.assertFalse(result.success)

    @patch("servicenow_mcp.tools.user_tools.requests.get")
    def test_list_groups_error(self, mock_get):
        from requests.exceptions import RequestException
        mock_get.side_effect = RequestException("fail")
        params = ListGroupsParams()
        result = list_groups(self.config, self.auth, params)
        self.assertFalse(result["success"])

    # --- additional coverage paths ---

    @patch("servicenow_mcp.tools.user_tools.requests.post")
    def test_create_user_with_all_fields(self, mock_post):
        mock_post.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "u1", "user_name": "alice"}}),
        )
        params = CreateUserParams(
            user_name="alice", first_name="Alice", last_name="Smith",
            email="alice@test.com", department="IT", title="Engineer",
            manager="admin", location="NYC", phone="555-0100",
        )
        result = create_user(self.config, self.auth, params)
        self.assertTrue(result.success)

    @patch("servicenow_mcp.tools.user_tools.requests.patch")
    def test_update_user_with_all_fields(self, mock_patch):
        mock_patch.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "u1", "user_name": "alice"}}),
        )
        params = UpdateUserParams(
            user_id="u1", first_name="Alice", last_name="Jones",
            email="alice@new.com", department="Eng", title="Sr Eng",
            manager="boss", active=True,
        )
        result = update_user(self.config, self.auth, params)
        self.assertTrue(result.success)

    @patch("servicenow_mcp.tools.user_tools.requests.get")
    def test_get_user_not_found(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": []}),
        )
        params = GetUserParams(user_name="nonexistent")
        result = get_user(self.config, self.auth, params)
        self.assertFalse(result["success"])

    @patch("servicenow_mcp.tools.user_tools.requests.get")
    def test_get_user_by_email(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": [{"sys_id": "u1", "user_name": "alice", "email": "alice@t.com"}]}),
        )
        params = GetUserParams(email="alice@t.com")
        result = get_user(self.config, self.auth, params)
        self.assertTrue(result["success"])

    @patch("servicenow_mcp.tools.user_tools.requests.get")
    def test_get_user_by_id(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": [{"sys_id": "u1", "user_name": "alice"}]}),
        )
        params = GetUserParams(user_id="u1")
        result = get_user(self.config, self.auth, params)
        self.assertTrue(result["success"])

    @patch("servicenow_mcp.tools.user_tools.requests.get")
    def test_list_users_with_filters(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": [{"sys_id": "u1", "user_name": "alice"}]}),
        )
        params = ListUsersParams(department="IT", active=True, query="title=Engineer")
        result = list_users(self.config, self.auth, params)
        self.assertTrue(result["success"])

    @patch("servicenow_mcp.tools.user_tools.requests.get")
    def test_list_groups_with_filters(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": [{"sys_id": "g1", "name": "IT Support"}]}),
        )
        params = ListGroupsParams(active=True, query="type=team")
        result = list_groups(self.config, self.auth, params)
        self.assertTrue(result["success"])

    @patch("servicenow_mcp.tools.user_tools.requests.delete")
    @patch("servicenow_mcp.tools.user_tools.requests.get")
    def test_remove_group_members_success(self, mock_get, mock_delete):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": [{"sys_id": "m1", "user": {"value": "u1"}}]}),
        )
        mock_delete.return_value = MagicMock(raise_for_status=MagicMock())
        params = RemoveGroupMembersParams(group_id="g1", members=["u1"])
        result = remove_group_members(self.config, self.auth, params)
        self.assertTrue(result.success)


if __name__ == "__main__":
    unittest.main()
