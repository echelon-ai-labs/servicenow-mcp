"""
Coverage-targeted tests for workflow_tools.py.
Targets uncovered lines: _unwrap_params, _get_auth_and_config edge cases,
missing-param checks, error paths, and delete_workflow.
"""

import unittest
from unittest.mock import MagicMock, patch

import requests as requests_lib

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.tools.workflow_tools import (
    _get_auth_and_config,
    _unwrap_params,
    activate_workflow,
    add_workflow_activity,
    create_workflow,
    deactivate_workflow,
    delete_workflow,
    delete_workflow_activity,
    get_workflow_activities,
    get_workflow_details,
    list_workflow_versions,
    list_workflows,
    reorder_workflow_activities,
    update_workflow,
    update_workflow_activity,
    ListWorkflowsParams,
)
from servicenow_mcp.utils.config import AuthConfig, AuthType, BasicAuthConfig, ServerConfig


def _make_auth_and_config():
    auth_config = AuthConfig(
        type=AuthType.BASIC,
        basic=BasicAuthConfig(username="u", password="p"),
    )
    server_config = ServerConfig(
        instance_url="https://test.service-now.com",
        auth=auth_config,
    )
    auth_manager = MagicMock(spec=AuthManager)
    auth_manager.get_headers.return_value = {"Authorization": "Bearer test"}
    return auth_manager, server_config


def _ok_response(data):
    resp = MagicMock()
    resp.json.return_value = data
    resp.headers = {"X-Total-Count": "1"}
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# _unwrap_params
# ---------------------------------------------------------------------------

class TestUnwrapParams(unittest.TestCase):

    def test_dict_passthrough(self):
        result = _unwrap_params({"a": 1}, ListWorkflowsParams)
        self.assertEqual(result, {"a": 1})

    def test_matching_model_converted_to_dict(self):
        model = ListWorkflowsParams(limit=5)
        result = _unwrap_params(model, ListWorkflowsParams)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["limit"], 5)

    def test_other_type_returned_as_is(self):
        """Line 134: non-dict, non-matching model returned unchanged."""
        obj = object()
        result = _unwrap_params(obj, ListWorkflowsParams)
        self.assertIs(result, obj)


# ---------------------------------------------------------------------------
# _get_auth_and_config edge cases
# ---------------------------------------------------------------------------

class TestGetAuthAndConfig(unittest.TestCase):

    def test_correct_order(self):
        auth_manager, server_config = _make_auth_and_config()
        am, sc = _get_auth_and_config(auth_manager, server_config)
        self.assertIs(am, auth_manager)
        self.assertIs(sc, server_config)

    def test_swapped_order(self):
        auth_manager, server_config = _make_auth_and_config()
        am, sc = _get_auth_and_config(server_config, auth_manager)
        self.assertIs(am, auth_manager)
        self.assertIs(sc, server_config)

    def test_duck_typed_get_headers_on_first_arg(self):
        """Lines 165-168: first arg has get_headers, second has instance_url."""
        first = MagicMock(spec=["get_headers"])
        first.get_headers = MagicMock(return_value={})
        second = MagicMock(spec=["instance_url"])
        second.instance_url = "https://duck.service-now.com"

        # Both are plain MagicMock (not AuthManager/ServerConfig instances)
        am, sc = _get_auth_and_config(first, second)
        self.assertIs(am, first)
        self.assertIs(sc, second)

    def test_no_get_headers_raises(self):
        """Line 170: neither has get_headers → ValueError."""
        a = MagicMock(spec=[])
        b = MagicMock(spec=["instance_url"])
        with self.assertRaises(ValueError, msg="Cannot find get_headers"):
            _get_auth_and_config(a, b)

    def test_no_instance_url_raises(self):
        """Line 177: neither has instance_url → ValueError."""
        a = MagicMock(spec=["get_headers"])
        b = MagicMock(spec=[])
        with self.assertRaises(ValueError, msg="Cannot find instance_url"):
            _get_auth_and_config(a, b)


# ---------------------------------------------------------------------------
# list_workflows additional paths
# ---------------------------------------------------------------------------

class TestListWorkflowsExtra(unittest.TestCase):

    def setUp(self):
        self.auth_manager, self.server_config = _make_auth_and_config()

    @patch("servicenow_mcp.tools.workflow_tools.requests.get")
    def test_name_filter_in_query(self, mock_get):
        """Line 220: name param adds nameLIKE to query."""
        mock_get.return_value = _ok_response({"result": []})
        list_workflows(self.auth_manager, self.server_config, {"name": "Incident"})
        _, kwargs = mock_get.call_args
        self.assertIn("nameLIKEIncident", kwargs["params"]["sysparm_query"])

    @patch("servicenow_mcp.tools.workflow_tools.requests.get")
    def test_query_filter_in_query(self, mock_get):
        """Line 223: query param appended."""
        mock_get.return_value = _ok_response({"result": []})
        list_workflows(self.auth_manager, self.server_config, {"query": "table=incident"})
        _, kwargs = mock_get.call_args
        self.assertIn("table=incident", kwargs["params"]["sysparm_query"])

    @patch("servicenow_mcp.tools.workflow_tools.requests.get")
    def test_generic_exception_returns_error(self, mock_get):
        """Lines 245-247: generic Exception returns error."""
        mock_get.side_effect = Exception("unexpected")
        result = list_workflows(self.auth_manager, self.server_config, {})
        self.assertIn("error", result)

    def test_get_auth_and_config_error_returns_error(self):
        """Lines 203-205: ValueError from _get_auth_and_config."""
        bad_a = MagicMock(spec=[])
        bad_b = MagicMock(spec=[])
        result = list_workflows(bad_a, bad_b, {})
        self.assertIn("error", result)


# ---------------------------------------------------------------------------
# get_workflow_details additional paths
# ---------------------------------------------------------------------------

class TestGetWorkflowDetailsExtra(unittest.TestCase):

    def setUp(self):
        self.auth_manager, self.server_config = _make_auth_and_config()

    def test_missing_workflow_id_returns_error(self):
        """Line 277: missing workflow_id."""
        result = get_workflow_details(self.auth_manager, self.server_config, {})
        self.assertIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.get")
    def test_generic_exception_returns_error(self, mock_get):
        """Lines 294-296: generic Exception."""
        mock_get.side_effect = Exception("boom")
        result = get_workflow_details(
            self.auth_manager, self.server_config, {"workflow_id": "wf1"}
        )
        self.assertIn("error", result)

    def test_bad_auth_config_returns_error(self):
        """Lines 271-273: ValueError from _get_auth_and_config."""
        result = get_workflow_details(MagicMock(spec=[]), MagicMock(spec=[]), {"workflow_id": "x"})
        self.assertIn("error", result)


# ---------------------------------------------------------------------------
# list_workflow_versions additional paths
# ---------------------------------------------------------------------------

class TestListWorkflowVersionsExtra(unittest.TestCase):

    def setUp(self):
        self.auth_manager, self.server_config = _make_auth_and_config()

    def test_missing_workflow_id_returns_error(self):
        """Line 327: missing workflow_id."""
        result = list_workflow_versions(self.auth_manager, self.server_config, {})
        self.assertIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.get")
    def test_generic_exception_returns_error(self, mock_get):
        """Lines 354-356: generic Exception."""
        mock_get.side_effect = Exception("boom")
        result = list_workflow_versions(
            self.auth_manager, self.server_config, {"workflow_id": "wf1"}
        )
        self.assertIn("error", result)

    def test_bad_auth_config_returns_error(self):
        """Lines 321-323."""
        result = list_workflow_versions(MagicMock(spec=[]), MagicMock(spec=[]), {"workflow_id": "x"})
        self.assertIn("error", result)


# ---------------------------------------------------------------------------
# get_workflow_activities additional paths
# ---------------------------------------------------------------------------

class TestGetWorkflowActivitiesExtra(unittest.TestCase):

    def setUp(self):
        self.auth_manager, self.server_config = _make_auth_and_config()

    def test_bad_auth_config_returns_error(self):
        """Lines 381-383."""
        result = get_workflow_activities(MagicMock(spec=[]), MagicMock(spec=[]), {"workflow_id": "x"})
        self.assertIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.get")
    def test_no_published_versions_returns_error(self, mock_get):
        """Line 409: no published versions found."""
        mock_get.return_value = _ok_response({"result": []})
        result = get_workflow_activities(
            self.auth_manager, self.server_config, {"workflow_id": "wf1"}
        )
        self.assertIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.get")
    def test_request_exception_during_version_fetch(self, mock_get):
        """Lines 415-417: RequestException during version fetch."""
        mock_get.side_effect = requests_lib.RequestException("net err")
        result = get_workflow_activities(
            self.auth_manager, self.server_config, {"workflow_id": "wf1"}
        )
        self.assertIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.get")
    def test_request_exception_during_activities_fetch(self, mock_get):
        """Lines 441-443: RequestException during activities fetch."""
        def side_effect(*args, **kwargs):
            url = args[0]
            if "wf_workflow_version" in url:
                return _ok_response({"result": [{"sys_id": "ver1"}]})
            raise requests_lib.RequestException("activities err")

        mock_get.side_effect = side_effect
        result = get_workflow_activities(
            self.auth_manager, self.server_config, {"workflow_id": "wf1"}
        )
        self.assertIn("error", result)


# ---------------------------------------------------------------------------
# create_workflow additional paths
# ---------------------------------------------------------------------------

class TestCreateWorkflowExtra(unittest.TestCase):

    def setUp(self):
        self.auth_manager, self.server_config = _make_auth_and_config()

    def test_missing_name_returns_error(self):
        """Line 477: missing name."""
        result = create_workflow(self.auth_manager, self.server_config, {})
        self.assertIn("error", result)

    def test_bad_auth_config_returns_error(self):
        """Lines 471-473."""
        result = create_workflow(MagicMock(spec=[]), MagicMock(spec=[]), {"name": "x"})
        self.assertIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.post")
    def test_generic_exception_returns_error(self, mock_post):
        """Lines 513-515."""
        mock_post.side_effect = Exception("boom")
        result = create_workflow(
            self.auth_manager, self.server_config, {"name": "WF"}
        )
        self.assertIn("error", result)


# ---------------------------------------------------------------------------
# update_workflow additional paths
# ---------------------------------------------------------------------------

class TestUpdateWorkflowExtra(unittest.TestCase):

    def setUp(self):
        self.auth_manager, self.server_config = _make_auth_and_config()

    def test_missing_workflow_id_returns_error(self):
        """Line 546."""
        result = update_workflow(self.auth_manager, self.server_config, {})
        self.assertIn("error", result)

    def test_no_update_params_returns_error(self):
        """Line 568: data dict is empty."""
        result = update_workflow(
            self.auth_manager, self.server_config, {"workflow_id": "wf1"}
        )
        self.assertIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.patch")
    def test_table_and_active_and_attributes(self, mock_patch):
        """Lines 558, 561, 565: table, active, attributes included."""
        mock_patch.return_value = _ok_response({"result": {"sys_id": "wf1"}})
        result = update_workflow(
            self.auth_manager,
            self.server_config,
            {
                "workflow_id": "wf1",
                "table": "incident",
                "active": True,
                "attributes": {"custom_field": "val"},
            },
        )
        self.assertIn("workflow", result)
        _, kwargs = mock_patch.call_args
        self.assertEqual(kwargs["json"]["table"], "incident")
        self.assertEqual(kwargs["json"]["active"], "true")
        self.assertEqual(kwargs["json"]["custom_field"], "val")

    @patch("servicenow_mcp.tools.workflow_tools.requests.patch")
    def test_generic_exception_returns_error(self, mock_patch):
        """Lines 586-588."""
        mock_patch.side_effect = Exception("boom")
        result = update_workflow(
            self.auth_manager, self.server_config, {"workflow_id": "wf1", "name": "N"}
        )
        self.assertIn("error", result)

    def test_bad_auth_config_returns_error(self):
        """Lines 540-542."""
        result = update_workflow(
            MagicMock(spec=[]), MagicMock(spec=[]), {"workflow_id": "x", "name": "n"}
        )
        self.assertIn("error", result)


# ---------------------------------------------------------------------------
# activate/deactivate_workflow additional paths
# ---------------------------------------------------------------------------

class TestActivateDeactivateExtra(unittest.TestCase):

    def setUp(self):
        self.auth_manager, self.server_config = _make_auth_and_config()

    def test_activate_missing_workflow_id(self):
        """Line 619."""
        result = activate_workflow(self.auth_manager, self.server_config, {})
        self.assertIn("error", result)

    def test_activate_bad_auth_config(self):
        """Lines 613-615."""
        result = activate_workflow(MagicMock(spec=[]), MagicMock(spec=[]), {"workflow_id": "x"})
        self.assertIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.patch")
    def test_activate_generic_exception(self, mock_patch):
        """Lines 642-644."""
        mock_patch.side_effect = Exception("boom")
        result = activate_workflow(
            self.auth_manager, self.server_config, {"workflow_id": "wf1"}
        )
        self.assertIn("error", result)

    def test_deactivate_missing_workflow_id(self):
        """Line 675."""
        result = deactivate_workflow(self.auth_manager, self.server_config, {})
        self.assertIn("error", result)

    def test_deactivate_bad_auth_config(self):
        """Lines 669-671."""
        result = deactivate_workflow(MagicMock(spec=[]), MagicMock(spec=[]), {"workflow_id": "x"})
        self.assertIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.patch")
    def test_deactivate_generic_exception(self, mock_patch):
        """Lines 698-700."""
        mock_patch.side_effect = Exception("boom")
        result = deactivate_workflow(
            self.auth_manager, self.server_config, {"workflow_id": "wf1"}
        )
        self.assertIn("error", result)


# ---------------------------------------------------------------------------
# add_workflow_activity additional paths
# ---------------------------------------------------------------------------

class TestAddWorkflowActivityExtra(unittest.TestCase):

    def setUp(self):
        self.auth_manager, self.server_config = _make_auth_and_config()

    def test_bad_auth_config_returns_error(self):
        """Lines 725-727."""
        result = add_workflow_activity(
            MagicMock(spec=[]), MagicMock(spec=[]),
            {"workflow_version_id": "v1", "name": "act", "activity_type": "approval"},
        )
        self.assertIn("error", result)

    def test_missing_workflow_version_id(self):
        """Line 732: missing workflow_version_id."""
        result = add_workflow_activity(
            self.auth_manager, self.server_config,
            {"name": "act", "activity_type": "approval"},
        )
        self.assertIn("error", result)

    def test_missing_activity_name(self):
        """Line 736: missing activity name."""
        result = add_workflow_activity(
            self.auth_manager, self.server_config,
            {"workflow_version_id": "v1", "activity_type": "approval"},
        )
        self.assertIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.post")
    def test_generic_exception_returns_error(self, mock_post):
        """Lines 768-769."""
        mock_post.side_effect = Exception("boom")
        result = add_workflow_activity(
            self.auth_manager, self.server_config,
            {"workflow_version_id": "v1", "name": "act", "activity_type": "approval"},
        )
        self.assertIn("error", result)


# ---------------------------------------------------------------------------
# update_workflow_activity additional paths
# ---------------------------------------------------------------------------

class TestUpdateWorkflowActivityExtra(unittest.TestCase):

    def setUp(self):
        self.auth_manager, self.server_config = _make_auth_and_config()

    def test_bad_auth_config_returns_error(self):
        """Lines 797-799."""
        result = update_workflow_activity(
            MagicMock(spec=[]), MagicMock(spec=[]),
            {"activity_id": "a1", "name": "n"},
        )
        self.assertIn("error", result)

    def test_missing_activity_id(self):
        """Line 816: missing activity_id."""
        result = update_workflow_activity(self.auth_manager, self.server_config, {})
        self.assertIn("error", result)

    def test_no_update_params_returns_error(self):
        """Line 819: no update fields."""
        result = update_workflow_activity(
            self.auth_manager, self.server_config, {"activity_id": "a1"}
        )
        self.assertIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.patch")
    def test_generic_exception_returns_error(self, mock_patch):
        """Lines 837-839."""
        mock_patch.side_effect = Exception("boom")
        result = update_workflow_activity(
            self.auth_manager, self.server_config, {"activity_id": "a1", "name": "n"}
        )
        self.assertIn("error", result)


# ---------------------------------------------------------------------------
# delete_workflow_activity additional paths
# ---------------------------------------------------------------------------

class TestDeleteWorkflowActivityExtra(unittest.TestCase):

    def setUp(self):
        self.auth_manager, self.server_config = _make_auth_and_config()

    def test_bad_auth_config_returns_error(self):
        """Lines 864-866."""
        result = delete_workflow_activity(
            MagicMock(spec=[]), MagicMock(spec=[]), {"activity_id": "a1"}
        )
        self.assertIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.delete")
    def test_generic_exception_returns_error(self, mock_delete):
        """Lines 885-886."""
        mock_delete.side_effect = Exception("boom")
        result = delete_workflow_activity(
            self.auth_manager, self.server_config, {"activity_id": "a1"}
        )
        self.assertIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.delete")
    def test_request_exception_returns_error(self, mock_delete):
        """Lines 884-886."""
        mock_delete.side_effect = requests_lib.RequestException("net")
        result = delete_workflow_activity(
            self.auth_manager, self.server_config, {"activity_id": "a1"}
        )
        self.assertIn("error", result)


# ---------------------------------------------------------------------------
# reorder_workflow_activities additional paths
# ---------------------------------------------------------------------------

class TestReorderWorkflowActivitiesExtra(unittest.TestCase):

    def setUp(self):
        self.auth_manager, self.server_config = _make_auth_and_config()

    def test_bad_auth_config_returns_error(self):
        """Lines 914-916."""
        result = reorder_workflow_activities(
            MagicMock(spec=[]), MagicMock(spec=[]),
            {"workflow_id": "wf1", "activity_ids": ["a1"]},
        )
        self.assertIn("error", result)

    def test_missing_workflow_id_returns_error(self):
        """Line 920."""
        result = reorder_workflow_activities(
            self.auth_manager, self.server_config, {"activity_ids": ["a1"]}
        )
        self.assertIn("error", result)

    def test_missing_activity_ids_returns_error(self):
        """Line 924."""
        result = reorder_workflow_activities(
            self.auth_manager, self.server_config, {"workflow_id": "wf1"}
        )
        self.assertIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.patch")
    def test_per_item_request_exception_recorded(self, mock_patch):
        """Lines 947-953: per-item RequestException is recorded in results."""
        mock_patch.side_effect = requests_lib.RequestException("item err")
        result = reorder_workflow_activities(
            self.auth_manager, self.server_config,
            {"workflow_id": "wf1", "activity_ids": ["a1", "a2"]},
        )
        self.assertIn("results", result)
        self.assertFalse(result["results"][0]["success"])
        self.assertIn("item err", result["results"][0]["error"])

    @patch("servicenow_mcp.tools.workflow_tools.requests.patch")
    def test_generic_exception_in_outer_try(self, mock_patch):
        """Lines 960-962: generic Exception in outer try."""
        mock_patch.side_effect = Exception("outer boom")
        result = reorder_workflow_activities(
            self.auth_manager, self.server_config,
            {"workflow_id": "wf1", "activity_ids": ["a1"]},
        )
        # The per-item exception is caught and recorded as a failure (not outer)
        # but the outer generic exception catch is at line 960
        # The per-item catch at line 947 catches RequestException, not general Exception
        # So a general Exception in requests.patch IS caught by the outer try
        self.assertIn("error", result)


# ---------------------------------------------------------------------------
# delete_workflow (entirely untested before)
# ---------------------------------------------------------------------------

class TestDeleteWorkflow(unittest.TestCase):

    def setUp(self):
        self.auth_manager, self.server_config = _make_auth_and_config()

    def test_bad_auth_config_returns_error(self):
        """Lines 985-989."""
        result = delete_workflow(
            MagicMock(spec=[]), MagicMock(spec=[]), {"workflow_id": "wf1"}
        )
        self.assertIn("error", result)

    def test_missing_workflow_id_returns_error(self):
        """Line 993."""
        result = delete_workflow(self.auth_manager, self.server_config, {})
        self.assertIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.delete")
    def test_delete_success(self, mock_delete):
        """Lines 996-1006."""
        mock_delete.return_value = _ok_response({})
        result = delete_workflow(
            self.auth_manager, self.server_config, {"workflow_id": "wf1"}
        )
        self.assertIn("message", result)
        self.assertIn("wf1", result["message"])

    @patch("servicenow_mcp.tools.workflow_tools.requests.delete")
    def test_request_exception(self, mock_delete):
        """Lines 1007-1009."""
        mock_delete.side_effect = requests_lib.RequestException("net err")
        result = delete_workflow(
            self.auth_manager, self.server_config, {"workflow_id": "wf1"}
        )
        self.assertIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.delete")
    def test_generic_exception(self, mock_delete):
        """Lines 1010-1012."""
        mock_delete.side_effect = Exception("boom")
        result = delete_workflow(
            self.auth_manager, self.server_config, {"workflow_id": "wf1"}
        )
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
