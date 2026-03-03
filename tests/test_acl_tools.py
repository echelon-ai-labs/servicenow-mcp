"""
Tests for Access Control List (ACL) and Security tools.

This module contains unit tests for ACL, Role, and Security Attribute management.
"""

import requests
import pytest
from unittest.mock import Mock, patch, MagicMock
from servicenow_mcp.tools.acl_tools import (
    list_acls,
    get_acl,
    create_acl,
    update_acl,
    delete_acl,
    list_roles,
    get_role,
    create_role,
    update_role,
    list_security_attributes,
    create_security_attribute,
    ListACLsParams,
    GetACLParams,
    CreateACLParams,
    UpdateACLParams,
    DeleteACLParams,
    ListRolesParams,
    GetRoleParams,
    CreateRoleParams,
    UpdateRoleParams,
    ListSecurityAttributesParams,
    CreateSecurityAttributeParams,
)
from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import ServerConfig


@pytest.fixture
def mock_config():
    """Create a mock ServerConfig."""
    config = Mock(spec=ServerConfig)
    config.api_url = "https://instance.service-now.com/api/now"
    config.instance_url = "https://instance.service-now.com"
    config.timeout = 30
    return config


@pytest.fixture
def mock_auth_manager():
    """Create a mock AuthManager."""
    auth_manager = Mock(spec=AuthManager)
    auth_manager.get_headers.return_value = {
        "Authorization": "Bearer token",
        "Content-Type": "application/json",
    }
    return auth_manager


class TestListACLs:
    """Tests for list_acls function."""

    @patch("servicenow_mcp.tools.acl_tools.requests.get")
    def test_list_acls_success(self, mock_get, mock_config, mock_auth_manager):
        """Test successful ACL listing."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": [
                {
                    "sys_id": "acl123",
                    "name": "incident.read",
                    "type": "record",
                    "operation": "read",
                    "description": "Read access to incidents",
                    "active": "true",
                    "admin_overrides": "false",
                    "script": "gs.hasRole('itil')",
                    "sys_created_on": "2024-01-15 10:00:00",
                    "sys_updated_on": "2024-01-15 10:00:00",
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        params = ListACLsParams(limit=10, offset=0)
        result = list_acls(mock_config, mock_auth_manager, params)

        assert result["success"] is True
        assert len(result["acls"]) == 1
        assert result["acls"][0]["name"] == "incident.read"
        assert result["total"] == 1

    @patch("servicenow_mcp.tools.acl_tools.requests.get")
    def test_list_acls_with_filters(self, mock_get, mock_config, mock_auth_manager):
        """Test ACL listing with filters."""
        mock_response = Mock()
        mock_response.json.return_value = {"result": []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        params = ListACLsParams(
            limit=10, offset=0, table_name="incident", operation="read", active=True
        )
        result = list_acls(mock_config, mock_auth_manager, params)

        # Verify query parameters were constructed correctly
        call_args = mock_get.call_args
        assert "sysparm_query" in call_args[1]["params"]


class TestGetACL:
    """Tests for get_acl function."""

    @patch("servicenow_mcp.tools.acl_tools.requests.get")
    def test_get_acl_success(self, mock_get, mock_config, mock_auth_manager):
        """Test successful ACL retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": {
                "sys_id": "acl123",
                "name": "incident.read",
                "type": "record",
                "operation": "read",
                "description": "Read access to incidents",
                "active": "true",
                "admin_overrides": "false",
                "script": "gs.hasRole('itil')",
                "sys_created_on": "2024-01-15 10:00:00",
                "sys_updated_on": "2024-01-15 10:00:00",
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        params = GetACLParams(acl_id="acl123")
        result = get_acl(mock_config, mock_auth_manager, params)

        assert result.success is True
        assert result.data["name"] == "incident.read"
        assert result.data["operation"] == "read"

    @patch("servicenow_mcp.tools.acl_tools.requests.get")
    def test_get_acl_not_found(self, mock_get, mock_config, mock_auth_manager):
        """Test ACL not found."""
        mock_response = Mock()
        mock_response.json.return_value = {"result": {}}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        params = GetACLParams(acl_id="nonexistent")
        result = get_acl(mock_config, mock_auth_manager, params)

        assert result.success is False
        assert "not found" in result.message.lower()


class TestCreateACL:
    """Tests for create_acl function."""

    @patch("servicenow_mcp.tools.acl_tools.requests.post")
    def test_create_acl_success(self, mock_post, mock_config, mock_auth_manager):
        """Test successful ACL creation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": {
                "sys_id": "new_acl123",
                "name": "incident.write",
                "type": "record",
                "operation": "write",
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        params = CreateACLParams(
            name="incident.write",
            type="record",
            operation="write",
            description="Write access to incidents",
            script="gs.hasRole('itil')",
            active=True,
            admin_overrides=False,
        )
        result = create_acl(mock_config, mock_auth_manager, params)

        assert result.success is True
        assert result.data["name"] == "incident.write"
        mock_post.assert_called_once()


class TestUpdateACL:
    """Tests for update_acl function."""

    @patch("servicenow_mcp.tools.acl_tools.requests.patch")
    def test_update_acl_success(self, mock_patch, mock_config, mock_auth_manager):
        """Test successful ACL update."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": {
                "sys_id": "acl123",
                "name": "incident.read.updated",
                "type": "record",
                "operation": "read",
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_patch.return_value = mock_response

        params = UpdateACLParams(
            acl_id="acl123", name="incident.read.updated", description="Updated description"
        )
        result = update_acl(mock_config, mock_auth_manager, params)

        assert result.success is True
        assert result.data["name"] == "incident.read.updated"


class TestDeleteACL:
    """Tests for delete_acl function."""

    @patch("servicenow_mcp.tools.acl_tools.requests.delete")
    def test_delete_acl_success(self, mock_delete, mock_config, mock_auth_manager):
        """Test successful ACL deletion."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_delete.return_value = mock_response

        params = DeleteACLParams(acl_id="acl123")
        result = delete_acl(mock_config, mock_auth_manager, params)

        assert result.success is True
        assert "deleted successfully" in result.message.lower()


class TestListRoles:
    """Tests for list_roles function."""

    @patch("servicenow_mcp.tools.acl_tools.requests.get")
    def test_list_roles_success(self, mock_get, mock_config, mock_auth_manager):
        """Test successful role listing."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": [
                {
                    "sys_id": "role123",
                    "name": "admin",
                    "description": "Administrator role",
                    "elevated_privilege": "true",
                    "requires_subscription": "",
                    "sys_created_on": "2024-01-15 10:00:00",
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        params = ListRolesParams(limit=10, offset=0)
        result = list_roles(mock_config, mock_auth_manager, params)

        assert result["success"] is True
        assert len(result["roles"]) == 1
        assert result["roles"][0]["name"] == "admin"


class TestGetRole:
    """Tests for get_role function."""

    @patch("servicenow_mcp.tools.acl_tools.requests.get")
    def test_get_role_by_sys_id(self, mock_get, mock_config, mock_auth_manager):
        """Test role retrieval by sys_id."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": {
                "sys_id": "role123",
                "name": "admin",
                "description": "Administrator role",
                "elevated_privilege": "true",
                "requires_subscription": "",
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        params = GetRoleParams(role_id="12345678901234567890123456789012")
        result = get_role(mock_config, mock_auth_manager, params)

        assert result.success is True
        assert result.data["name"] == "admin"

    @patch("servicenow_mcp.tools.acl_tools.requests.get")
    def test_get_role_by_name(self, mock_get, mock_config, mock_auth_manager):
        """Test role retrieval by name."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": [
                {
                    "sys_id": "role123",
                    "name": "admin",
                    "description": "Administrator role",
                    "elevated_privilege": "true",
                    "requires_subscription": "",
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        params = GetRoleParams(role_id="admin")
        result = get_role(mock_config, mock_auth_manager, params)

        assert result.success is True
        assert result.data["name"] == "admin"


class TestCreateRole:
    """Tests for create_role function."""

    @patch("servicenow_mcp.tools.acl_tools.requests.post")
    def test_create_role_success(self, mock_post, mock_config, mock_auth_manager):
        """Test successful role creation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": {
                "sys_id": "new_role123",
                "name": "custom_role",
                "description": "Custom role for specific access",
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        params = CreateRoleParams(
            name="custom_role",
            description="Custom role for specific access",
            elevated_privilege=False,
        )
        result = create_role(mock_config, mock_auth_manager, params)

        assert result.success is True
        assert result.data["name"] == "custom_role"


class TestUpdateRole:
    """Tests for update_role function."""

    @patch("servicenow_mcp.tools.acl_tools.requests.patch")
    def test_update_role_success(self, mock_patch, mock_config, mock_auth_manager):
        """Test successful role update."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": {
                "sys_id": "role123",
                "name": "custom_role_updated",
                "description": "Updated description",
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_patch.return_value = mock_response

        params = UpdateRoleParams(
            role_id="role123",
            name="custom_role_updated",
            description="Updated description",
        )
        result = update_role(mock_config, mock_auth_manager, params)

        assert result.success is True
        assert result.data["name"] == "custom_role_updated"


class TestListSecurityAttributes:
    """Tests for list_security_attributes function."""

    @patch("servicenow_mcp.tools.acl_tools.requests.get")
    def test_list_security_attributes_success(
        self, mock_get, mock_config, mock_auth_manager
    ):
        """Test successful security attributes listing."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": [
                {
                    "sys_id": "attr123",
                    "name": "data_classification",
                    "description": "Data classification attribute",
                    "type": "string",
                    "sys_created_on": "2024-01-15 10:00:00",
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        params = ListSecurityAttributesParams(limit=10, offset=0)
        result = list_security_attributes(mock_config, mock_auth_manager, params)

        assert result["success"] is True
        assert len(result["attributes"]) == 1
        assert result["attributes"][0]["name"] == "data_classification"


class TestCreateSecurityAttribute:
    """Tests for create_security_attribute function."""

    @patch("servicenow_mcp.tools.acl_tools.requests.post")
    def test_create_security_attribute_success(
        self, mock_post, mock_config, mock_auth_manager
    ):
        """Test successful security attribute creation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": {
                "sys_id": "new_attr123",
                "name": "confidentiality",
                "type": "string",
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        params = CreateSecurityAttributeParams(
            name="confidentiality",
            description="Confidentiality level",
            type="string",
        )
        result = create_security_attribute(mock_config, mock_auth_manager, params)

        assert result.success is True
        assert result.data["name"] == "confidentiality"


class TestErrorHandling:
    """Tests for error handling in ACL tools."""

    @patch("servicenow_mcp.tools.acl_tools.requests.get")
    def test_list_acls_request_error(self, mock_get, mock_config, mock_auth_manager):
        """Test error handling in list_acls."""
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")

        params = ListACLsParams(limit=10, offset=0)
        result = list_acls(mock_config, mock_auth_manager, params)

        assert result["success"] is False
        assert "error" in result["message"].lower() or "failed" in result["message"].lower()

    @patch("servicenow_mcp.tools.acl_tools.requests.post")
    def test_create_acl_request_error(self, mock_post, mock_config, mock_auth_manager):
        """Test error handling in create_acl."""
        mock_post.side_effect = requests.exceptions.RequestException("API error")

        params = CreateACLParams(
            name="test.acl", type="record", operation="read", active=True
        )
        result = create_acl(mock_config, mock_auth_manager, params)

        assert result.success is False
        assert "error" in result.message.lower() or "failed" in result.message.lower()
