"""
Tests for catalog task tools.
"""

import pytest
from unittest.mock import Mock, patch

from servicenow_mcp.tools.catalog_task_tools import (
    list_catalog_tasks,
    get_catalog_task,
    update_catalog_task,
    ListCatalogTasksParams,
    GetCatalogTaskParams,
    UpdateCatalogTaskParams,
)
from servicenow_mcp.utils.config import ServerConfig
from servicenow_mcp.auth.auth_manager import AuthManager


@pytest.fixture
def mock_config():
    """Mock configuration for tests."""
    config = Mock(spec=ServerConfig)
    config.api_url = "https://test.service-now.com/api/now"
    config.timeout = 30
    return config


@pytest.fixture
def mock_auth_manager():
    """Mock authentication manager for tests."""
    auth_manager = Mock(spec=AuthManager)
    auth_manager.get_headers.return_value = {"Authorization": "Bearer test_token"}
    return auth_manager


@patch("servicenow_mcp.tools.catalog_task_tools.requests.get")
def test_list_catalog_tasks_success(mock_get, mock_config, mock_auth_manager):
    """Test successful listing of catalog tasks."""
    # Mock response data
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "result": [
            {
                "sys_id": "task123",
                "number": "SCTASK0001639213",
                "short_description": "Test Task",
                "description": "Test Description",
                "state": "2",
                "assigned_to": "user123",
                "assignment_group": "group123",
                "request": "REQ123",
                "sys_created_on": "2023-01-01 12:00:00",
                "sys_updated_on": "2023-01-01 13:00:00",
                "due_date": "2023-01-02 12:00:00",
                "priority": "3",
            }
        ]
    }
    mock_get.return_value = mock_response

    # Test parameters
    params = ListCatalogTasksParams(limit=10, offset=0)

    # Call function
    result = list_catalog_tasks(mock_config, mock_auth_manager, params)

    # Assertions
    assert result["success"] is True
    assert len(result["tasks"]) == 1
    assert result["tasks"][0]["number"] == "SCTASK0001639213"
    assert result["tasks"][0]["short_description"] == "Test Task"
    
    # Verify API call
    mock_get.assert_called_once()
    call_args = mock_get.call_args
    assert "table/sc_task" in call_args[0][0]


@patch("servicenow_mcp.tools.catalog_task_tools.requests.get")
def test_get_catalog_task_by_number(mock_get, mock_config, mock_auth_manager):
    """Test getting a catalog task by task number."""
    # Mock response data
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "result": [
            {
                "sys_id": "task123",
                "number": "SCTASK0001639213",
                "short_description": "Test Task",
                "description": "Test Description",
                "state": "2",
                "assigned_to": "user123",
                "assignment_group": "group123",
                "request": "REQ123",
                "sys_created_on": "2023-01-01 12:00:00",
                "sys_updated_on": "2023-01-01 13:00:00",
                "due_date": "2023-01-02 12:00:00",
                "priority": "3",
                "work_notes": "Test notes",
                "close_notes": "Test close notes",
            }
        ]
    }
    mock_get.return_value = mock_response

    # Test parameters
    params = GetCatalogTaskParams(task_id="SCTASK0001639213")

    # Call function
    result = get_catalog_task(mock_config, mock_auth_manager, params)

    # Assertions
    assert result["success"] is True
    assert result["task"]["number"] == "SCTASK0001639213"
    assert result["task"]["short_description"] == "Test Task"
    assert result["task"]["work_notes"] == "Test notes"
    
    # Verify API call
    mock_get.assert_called_once()
    call_args = mock_get.call_args
    assert "table/sc_task" in call_args[0][0]


@patch("servicenow_mcp.tools.catalog_task_tools.requests.get")
@patch("servicenow_mcp.tools.catalog_task_tools.requests.put")
def test_update_catalog_task_by_number(mock_put, mock_get, mock_config, mock_auth_manager):
    """Test updating a catalog task by task number."""
    # Mock GET response for finding task by number
    mock_get_response = Mock()
    mock_get_response.raise_for_status.return_value = None
    mock_get_response.json.return_value = {
        "result": [{"sys_id": "task123"}]
    }
    mock_get.return_value = mock_get_response

    # Mock PUT response for updating task
    mock_put_response = Mock()
    mock_put_response.raise_for_status.return_value = None
    mock_put_response.json.return_value = {
        "result": {
            "sys_id": "task123",
            "number": "SCTASK0001639213",
        }
    }
    mock_put.return_value = mock_put_response

    # Test parameters
    params = UpdateCatalogTaskParams(
        task_id="SCTASK0001639213", 
        state="3", 
        work_notes="Updated notes"
    )

    # Call function
    result = update_catalog_task(mock_config, mock_auth_manager, params)

    # Assertions
    assert result.success is True
    assert result.task_number == "SCTASK0001639213"
    assert result.message == "Catalog task updated successfully"
    
    # Verify API calls
    mock_get.assert_called_once()
    mock_put.assert_called_once()


@patch("servicenow_mcp.tools.catalog_task_tools.requests.get")
def test_get_catalog_task_not_found(mock_get, mock_config, mock_auth_manager):
    """Test getting a catalog task that doesn't exist."""
    # Mock response data
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"result": []}
    mock_get.return_value = mock_response

    # Test parameters
    params = GetCatalogTaskParams(task_id="SCTASK0000000000")

    # Call function
    result = get_catalog_task(mock_config, mock_auth_manager, params)

    # Assertions
    assert result["success"] is False
    assert "not found" in result["message"]