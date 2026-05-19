"""
Unit tests for GAIL/BAIL tools.
"""

import unittest
from datetime import date, datetime
from unittest.mock import MagicMock, patch

from pydantic import ValidationError

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.tools.gail_tools import (
    CreateGailEngagementParams,
    UpdateGailEngagementParams,
    UpdateGailResourceParams,
    create_gail_engagement,
    update_gail_engagement,
    update_gail_resource,
    _normalize_date,
    _normalize_sys_id_list,
)
from servicenow_mcp.utils.config import AuthConfig, AuthType, BasicAuthConfig, ServerConfig


class TestCreateGailEngagement(unittest.TestCase):

    def setUp(self):
        self.auth_config = AuthConfig(
            type=AuthType.BASIC,
            basic=BasicAuthConfig(username="test", password="test"),
        )
        self.config = ServerConfig(
            instance_url="https://bassamgail.service-now.com",
            auth=self.auth_config,
        )
        self.auth_manager = MagicMock(spec=AuthManager)
        self.auth_manager.get_headers.return_value = {
            "Authorization": "Bearer FAKE_TOKEN"
        }

    @patch("servicenow_mcp.tools.gail_tools.requests.post")
    def test_create_required_fields_only(self, mock_post):
        """Happy path: create with only required field (customer_name)."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "result": {
                "sys_id": "a" * 32,
                "customer_name": "Acme Corp",
                "track": "gail",
                "stage": "1_initiate",
                "health_status": "green",
            }
        }
        mock_post.return_value = mock_response

        params = CreateGailEngagementParams(customer_name="Acme Corp")
        result = create_gail_engagement(self.config, self.auth_manager, params)

        self.assertTrue(result["success"])
        self.assertEqual(result["sys_id"], "a" * 32)
        self.assertIn("record", result)

        # Verify the POST payload
        call_kwargs = mock_post.call_args
        sent_data = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        self.assertEqual(sent_data["customer_name"], "Acme Corp")
        self.assertEqual(sent_data["track"], "gail")
        self.assertEqual(sent_data["stage"], "1_initiate")
        self.assertEqual(sent_data["health_status"], "green")

    @patch("servicenow_mcp.tools.gail_tools.requests.post")
    def test_create_all_fields(self, mock_post):
        """Happy path: create with all fields populated."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "result": {"sys_id": "b" * 32, "customer_name": "Big Corp"}
        }
        mock_post.return_value = mock_response

        params = CreateGailEngagementParams(
            customer_name="Big Corp",
            track="bail",
            stage="bail_active",
            health_status="red",
            customer_geo="US West",
            engineers=["a" * 32, "b" * 32],
            engagement_managers="c" * 32,
            architects=["d" * 32],
            ai_agents_itsm=True,
            ai_agents_csm=False,
            ai_agents_hr=True,
            ai_agents_va=False,
            scope_details="Scope text",
            notes_escalation_log="Notes text",
            sn_release_version="Xanadu",
            exit_criteria="Exit text",
            intake_request="REQ001",
            date_customer_intro="2025-01-15",
            date_assess_kickoff=date(2025, 2, 1),
            date_workshop_dev_test=datetime(2025, 3, 10, 14, 30),
            date_target_golive="2025-06-01",
            date_uat="2025-05-01",
            date_internal_kt="2025-04-15",
        )
        result = create_gail_engagement(self.config, self.auth_manager, params)

        self.assertTrue(result["success"])
        call_kwargs = mock_post.call_args
        sent_data = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        self.assertEqual(sent_data["track"], "bail")
        self.assertEqual(sent_data["stage"], "bail_active")
        self.assertEqual(sent_data["engineers"], f"{'a' * 32},{'b' * 32}")
        self.assertEqual(sent_data["engagement_managers"], "c" * 32)
        self.assertEqual(sent_data["ai_agents_itsm"], "true")
        self.assertEqual(sent_data["ai_agents_csm"], "false")
        self.assertEqual(sent_data["date_customer_intro"], "2025-01-15")
        self.assertEqual(sent_data["date_assess_kickoff"], "2025-02-01")
        self.assertEqual(sent_data["date_workshop_dev_test"], "2025-03-10")

    def test_create_missing_customer_name(self):
        """Validation: customer_name is required."""
        with self.assertRaises(ValidationError):
            CreateGailEngagementParams()

    def test_create_empty_customer_name(self):
        """Validation: customer_name must not be empty."""
        with self.assertRaises(ValidationError):
            CreateGailEngagementParams(customer_name="   ")

    def test_create_invalid_track(self):
        """Validation: track must be a valid choice."""
        with self.assertRaises(ValidationError):
            CreateGailEngagementParams(customer_name="Acme", track="invalid")

    def test_create_invalid_stage(self):
        """Validation: stage must be a valid choice."""
        with self.assertRaises(ValidationError):
            CreateGailEngagementParams(customer_name="Acme", stage="BAIL - Active")

    def test_create_invalid_health_status(self):
        """Validation: health_status must be a valid choice."""
        with self.assertRaises(ValidationError):
            CreateGailEngagementParams(customer_name="Acme", health_status="blue")

    def test_create_malformed_sys_id_in_list(self):
        """Validation: sys_ids in list fields must be 32 hex chars."""
        params = CreateGailEngagementParams(
            customer_name="Acme", engineers=["not_a_valid_sysid"]
        )
        result = create_gail_engagement(self.config, self.auth_manager, params)
        self.assertFalse(result["success"])
        self.assertIn("Invalid sys_id", result["error"])

    def test_create_mixed_format_list(self):
        """List normalization: comma-string input."""
        params = CreateGailEngagementParams(
            customer_name="Acme",
            engineers=f"{'a' * 32},{'b' * 32}",
        )
        # Just validate params parse correctly - the normalize happens at call time
        self.assertEqual(params.engineers, f"{'a' * 32},{'b' * 32}")

    @patch("servicenow_mcp.tools.gail_tools.requests.post")
    def test_create_error_passthrough(self, mock_post):
        """Error pass-through: 400 response propagates status and message."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_response.json.return_value = {
            "error": {"message": "Invalid field value"}
        }
        mock_post.return_value = mock_response

        params = CreateGailEngagementParams(customer_name="Acme")
        result = create_gail_engagement(self.config, self.auth_manager, params)

        self.assertFalse(result["success"])
        self.assertEqual(result["status_code"], 400)
        self.assertEqual(result["error"], "Invalid field value")

    @patch("servicenow_mcp.tools.gail_tools.requests.post")
    def test_create_invalid_date_string(self, mock_post):
        """Validation: invalid date string is rejected."""
        params = CreateGailEngagementParams(
            customer_name="Acme", date_customer_intro="not-a-date"
        )
        result = create_gail_engagement(self.config, self.auth_manager, params)
        self.assertFalse(result["success"])
        self.assertIn("Invalid date format", result["error"])


class TestUpdateGailEngagement(unittest.TestCase):

    def setUp(self):
        self.auth_config = AuthConfig(
            type=AuthType.BASIC,
            basic=BasicAuthConfig(username="test", password="test"),
        )
        self.config = ServerConfig(
            instance_url="https://bassamgail.service-now.com",
            auth=self.auth_config,
        )
        self.auth_manager = MagicMock(spec=AuthManager)
        self.auth_manager.get_headers.return_value = {
            "Authorization": "Bearer FAKE_TOKEN"
        }
        self.valid_sys_id = "a" * 32

    @patch("servicenow_mcp.tools.gail_tools.requests.patch")
    def test_update_single_field(self, mock_patch):
        """Happy path: update notes_escalation_log only."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "result": {
                "sys_id": self.valid_sys_id,
                "notes_escalation_log": "updated note",
            }
        }
        mock_patch.return_value = mock_response

        params = UpdateGailEngagementParams(
            sys_id=self.valid_sys_id, notes_escalation_log="updated note"
        )
        result = update_gail_engagement(self.config, self.auth_manager, params)

        self.assertTrue(result["success"])
        self.assertEqual(result["sys_id"], self.valid_sys_id)
        self.assertIn("record", result)

        call_kwargs = mock_patch.call_args
        sent_data = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        self.assertEqual(sent_data["notes_escalation_log"], "updated note")
        self.assertNotIn("sys_id", sent_data)
        # Only notes_escalation_log should be in the body
        self.assertEqual(len(sent_data), 1)

    @patch("servicenow_mcp.tools.gail_tools.requests.patch")
    def test_update_multi_field(self, mock_patch):
        """Happy path: update engineers + health_status + notes_escalation_log."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "result": {"sys_id": self.valid_sys_id}
        }
        mock_patch.return_value = mock_response

        params = UpdateGailEngagementParams(
            sys_id=self.valid_sys_id,
            engineers=["a" * 32, "b" * 32],
            health_status="yellow",
            notes_escalation_log="multi-field update",
        )
        result = update_gail_engagement(self.config, self.auth_manager, params)

        self.assertTrue(result["success"])
        call_kwargs = mock_patch.call_args
        sent_data = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        self.assertEqual(sent_data["engineers"], f"{'a' * 32},{'b' * 32}")
        self.assertEqual(sent_data["health_status"], "yellow")
        self.assertEqual(sent_data["notes_escalation_log"], "multi-field update")

    def test_update_invalid_sys_id(self):
        """Validation: sys_id must be 32 hex chars — error before HTTP."""
        with self.assertRaises(ValidationError):
            UpdateGailEngagementParams(
                sys_id="not-a-real-sys-id", notes_escalation_log="test"
            )

    def test_update_invalid_choice_stage(self):
        """Validation: stage must be a valid choice."""
        with self.assertRaises(ValidationError):
            UpdateGailEngagementParams(
                sys_id=self.valid_sys_id, stage="banana"
            )

    def test_update_invalid_choice_track(self):
        """Validation: track must be a valid choice."""
        with self.assertRaises(ValidationError):
            UpdateGailEngagementParams(
                sys_id=self.valid_sys_id, track="foo"
            )

    def test_update_invalid_choice_health_status(self):
        """Validation: health_status must be a valid choice."""
        with self.assertRaises(ValidationError):
            UpdateGailEngagementParams(
                sys_id=self.valid_sys_id, health_status="bar"
            )

    @patch("servicenow_mcp.tools.gail_tools.requests.patch")
    def test_update_glide_list_as_list(self, mock_patch):
        """Glide_list as list: engineers=[...] serializes to comma string."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "result": {"sys_id": self.valid_sys_id}
        }
        mock_patch.return_value = mock_response

        params = UpdateGailEngagementParams(
            sys_id=self.valid_sys_id,
            engineers=["a" * 32, "b" * 32],
        )
        result = update_gail_engagement(self.config, self.auth_manager, params)

        self.assertTrue(result["success"])
        call_kwargs = mock_patch.call_args
        sent_data = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        self.assertEqual(sent_data["engineers"], f"{'a' * 32},{'b' * 32}")

    @patch("servicenow_mcp.tools.gail_tools.requests.patch")
    def test_update_glide_list_as_string(self, mock_patch):
        """Glide_list as string: comma-separated sys_ids."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "result": {"sys_id": self.valid_sys_id}
        }
        mock_patch.return_value = mock_response

        params = UpdateGailEngagementParams(
            sys_id=self.valid_sys_id,
            engineers=f"{'a' * 32},{'b' * 32}",
        )
        result = update_gail_engagement(self.config, self.auth_manager, params)

        self.assertTrue(result["success"])
        call_kwargs = mock_patch.call_args
        sent_data = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        self.assertEqual(sent_data["engineers"], f"{'a' * 32},{'b' * 32}")

    @patch("servicenow_mcp.tools.gail_tools.requests.patch")
    def test_update_glide_list_with_whitespace(self, mock_patch):
        """Glide_list with whitespace: entries are trimmed."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "result": {"sys_id": self.valid_sys_id}
        }
        mock_patch.return_value = mock_response

        params = UpdateGailEngagementParams(
            sys_id=self.valid_sys_id,
            engineers=f" {'a' * 32} , {'b' * 32} ",
        )
        result = update_gail_engagement(self.config, self.auth_manager, params)

        self.assertTrue(result["success"])
        call_kwargs = mock_patch.call_args
        sent_data = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        self.assertEqual(sent_data["engineers"], f"{'a' * 32},{'b' * 32}")

    def test_update_glide_list_invalid_entry(self):
        """Glide_list with invalid entry: error identifies the bad entry."""
        params = UpdateGailEngagementParams(
            sys_id=self.valid_sys_id,
            engineers=["a" * 32, "not-hex-32"],
        )
        result = update_gail_engagement(self.config, self.auth_manager, params)

        self.assertFalse(result["success"])
        self.assertIn("Invalid sys_id", result["error"])
        self.assertIn("not-hex-32", result["error"])

    @patch("servicenow_mcp.tools.gail_tools.requests.patch")
    def test_update_clear_glide_list_empty_string(self, mock_patch):
        """Clear glide_list with empty string."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "result": {"sys_id": self.valid_sys_id}
        }
        mock_patch.return_value = mock_response

        params = UpdateGailEngagementParams(
            sys_id=self.valid_sys_id, engineers=""
        )
        result = update_gail_engagement(self.config, self.auth_manager, params)

        self.assertTrue(result["success"])
        call_kwargs = mock_patch.call_args
        sent_data = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        self.assertEqual(sent_data["engineers"], "")

    @patch("servicenow_mcp.tools.gail_tools.requests.patch")
    def test_update_clear_glide_list_empty_list(self, mock_patch):
        """Clear glide_list with empty list."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "result": {"sys_id": self.valid_sys_id}
        }
        mock_patch.return_value = mock_response

        params = UpdateGailEngagementParams(
            sys_id=self.valid_sys_id, engineers=[]
        )
        result = update_gail_engagement(self.config, self.auth_manager, params)

        self.assertTrue(result["success"])
        call_kwargs = mock_patch.call_args
        sent_data = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        self.assertEqual(sent_data["engineers"], "")

    def test_update_no_fields_provided(self):
        """Validation: at least one updatable field must be provided."""
        params = UpdateGailEngagementParams(sys_id=self.valid_sys_id)
        result = update_gail_engagement(self.config, self.auth_manager, params)

        self.assertFalse(result["success"])
        self.assertIn("Nothing to update", result["error"])

    @patch("servicenow_mcp.tools.gail_tools.requests.patch")
    def test_update_date_normalization(self, mock_patch):
        """Date normalization: date object → YYYY-MM-DD string."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "result": {"sys_id": self.valid_sys_id}
        }
        mock_patch.return_value = mock_response

        params = UpdateGailEngagementParams(
            sys_id=self.valid_sys_id,
            date_customer_intro=date(2026, 5, 18),
        )
        result = update_gail_engagement(self.config, self.auth_manager, params)

        self.assertTrue(result["success"])
        call_kwargs = mock_patch.call_args
        sent_data = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        self.assertEqual(sent_data["date_customer_intro"], "2026-05-18")

    @patch("servicenow_mcp.tools.gail_tools.requests.patch")
    def test_update_empty_string_preserves_field_clear(self, mock_patch):
        """Empty string for a string field is sent, not silently dropped."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "result": {"sys_id": self.valid_sys_id}
        }
        mock_patch.return_value = mock_response

        params = UpdateGailEngagementParams(
            sys_id=self.valid_sys_id, customer_geo=""
        )
        result = update_gail_engagement(self.config, self.auth_manager, params)

        self.assertTrue(result["success"])
        call_kwargs = mock_patch.call_args
        sent_data = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        self.assertIn("customer_geo", sent_data)
        self.assertEqual(sent_data["customer_geo"], "")

    @patch("servicenow_mcp.tools.gail_tools.requests.patch")
    def test_update_none_skips_field(self, mock_patch):
        """None/missing field is NOT in the request body."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "result": {"sys_id": self.valid_sys_id}
        }
        mock_patch.return_value = mock_response

        params = UpdateGailEngagementParams(
            sys_id=self.valid_sys_id,
            notes_escalation_log="test",
            customer_geo=None,
        )
        result = update_gail_engagement(self.config, self.auth_manager, params)

        self.assertTrue(result["success"])
        call_kwargs = mock_patch.call_args
        sent_data = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        self.assertNotIn("customer_geo", sent_data)
        self.assertIn("notes_escalation_log", sent_data)


class TestUpdateGailResource(unittest.TestCase):

    def setUp(self):
        self.auth_config = AuthConfig(
            type=AuthType.BASIC,
            basic=BasicAuthConfig(username="test", password="test"),
        )
        self.config = ServerConfig(
            instance_url="https://bassamgail.service-now.com",
            auth=self.auth_config,
        )
        self.auth_manager = MagicMock(spec=AuthManager)
        self.auth_manager.get_headers.return_value = {
            "Authorization": "Bearer FAKE_TOKEN"
        }
        self.valid_sys_id = "a" * 32

    @patch("servicenow_mcp.tools.gail_tools.requests.patch")
    def test_update_single_field(self, mock_patch):
        """Happy path: update bail_live_count only."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "result": {"sys_id": self.valid_sys_id, "bail_live_count": "5"}
        }
        mock_patch.return_value = mock_response

        params = UpdateGailResourceParams(
            sys_id=self.valid_sys_id, bail_live_count=5
        )
        result = update_gail_resource(self.config, self.auth_manager, params)

        self.assertTrue(result["success"])
        self.assertEqual(result["sys_id"], self.valid_sys_id)

        call_kwargs = mock_patch.call_args
        sent_data = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        self.assertEqual(sent_data["bail_live_count"], 5)
        self.assertNotIn("sys_id", sent_data)

    @patch("servicenow_mcp.tools.gail_tools.requests.patch")
    def test_update_all_fields(self, mock_patch):
        """Happy path: update with all optional fields populated."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "result": {"sys_id": self.valid_sys_id}
        }
        mock_patch.return_value = mock_response

        params = UpdateGailResourceParams(
            sys_id=self.valid_sys_id,
            name="Jane Doe",
            region="emea",
            availability_status="unavailable",
            bail_live_count=3,
            bail_active_count=2,
            stage_initiate_count=1,
            stage_plan_count=1,
            stage_execute_count=0,
            stage_deliver_count=0,
            stage_close_count=0,
            total_active_count=5,
            email="jane@example.com",
            title="Senior Engineer",
            department="Engineering",
            role="Engineer",
            employer="ServiceNow",
            location="London, UK",
            languages_spoken="English, French",
            areas_of_expertise="ITSM, CSM",
            time_off="OOO July 1-15",
            active_accounts="Acme, BigCo",
            accounts_gone_live="SmallCo",
            date_added="2025-01-01",
            date_added_to_program=date(2025, 2, 1),
        )
        result = update_gail_resource(self.config, self.auth_manager, params)

        self.assertTrue(result["success"])
        call_kwargs = mock_patch.call_args
        sent_data = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        self.assertEqual(sent_data["name"], "Jane Doe")
        self.assertEqual(sent_data["region"], "emea")
        self.assertEqual(sent_data["date_added"], "2025-01-01")
        self.assertEqual(sent_data["date_added_to_program"], "2025-02-01")

    def test_update_invalid_sys_id(self):
        """Validation: sys_id must be 32 hex chars."""
        with self.assertRaises(ValidationError):
            UpdateGailResourceParams(sys_id="bad_id", bail_live_count=1)

    def test_update_nothing_to_update(self):
        """Validation: at least one optional field required."""
        params = UpdateGailResourceParams(sys_id=self.valid_sys_id)
        result = update_gail_resource(self.config, self.auth_manager, params)
        self.assertFalse(result["success"])
        self.assertIn("Nothing to update", result["error"])

    def test_update_invalid_region(self):
        """Validation: region must be a valid choice."""
        with self.assertRaises(ValidationError):
            UpdateGailResourceParams(
                sys_id=self.valid_sys_id, region="antarctica"
            )

    def test_update_invalid_availability_status(self):
        """Validation: availability_status must be a valid choice."""
        with self.assertRaises(ValidationError):
            UpdateGailResourceParams(
                sys_id=self.valid_sys_id, availability_status="on_vacation"
            )

    @patch("servicenow_mcp.tools.gail_tools.requests.patch")
    def test_update_error_passthrough(self, mock_patch):
        """Error pass-through: 400 response propagates status and message."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_response.json.return_value = {
            "error": {"message": "Record not found"}
        }
        mock_patch.return_value = mock_response

        params = UpdateGailResourceParams(
            sys_id=self.valid_sys_id, bail_live_count=5
        )
        result = update_gail_resource(self.config, self.auth_manager, params)

        self.assertFalse(result["success"])
        self.assertEqual(result["status_code"], 400)
        self.assertEqual(result["error"], "Record not found")

    @patch("servicenow_mcp.tools.gail_tools.requests.patch")
    def test_update_date_normalization(self, mock_patch):
        """Date normalization: date, datetime, and string inputs."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "result": {"sys_id": self.valid_sys_id}
        }
        mock_patch.return_value = mock_response

        params = UpdateGailResourceParams(
            sys_id=self.valid_sys_id,
            date_added=datetime(2025, 6, 15, 10, 30),
            date_added_to_program="2025-07-01",
        )
        result = update_gail_resource(self.config, self.auth_manager, params)

        self.assertTrue(result["success"])
        call_kwargs = mock_patch.call_args
        sent_data = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        self.assertEqual(sent_data["date_added"], "2025-06-15")
        self.assertEqual(sent_data["date_added_to_program"], "2025-07-01")


class TestHelpers(unittest.TestCase):

    def test_normalize_sys_id_list_from_list(self):
        ids = ["a" * 32, "b" * 32]
        result = _normalize_sys_id_list(ids)
        self.assertEqual(result, f"{'a' * 32},{'b' * 32}")

    def test_normalize_sys_id_list_from_string(self):
        s = f"{'a' * 32}, {'b' * 32}"
        result = _normalize_sys_id_list(s)
        self.assertEqual(result, f"{'a' * 32},{'b' * 32}")

    def test_normalize_sys_id_list_none(self):
        self.assertIsNone(_normalize_sys_id_list(None))

    def test_normalize_sys_id_list_invalid(self):
        with self.assertRaises(ValueError):
            _normalize_sys_id_list(["bad"])

    def test_normalize_date_string(self):
        self.assertEqual(_normalize_date("2025-01-15"), "2025-01-15")

    def test_normalize_date_date_object(self):
        self.assertEqual(_normalize_date(date(2025, 1, 15)), "2025-01-15")

    def test_normalize_date_datetime_object(self):
        self.assertEqual(
            _normalize_date(datetime(2025, 1, 15, 10, 30)), "2025-01-15"
        )

    def test_normalize_date_none(self):
        self.assertIsNone(_normalize_date(None))

    def test_normalize_date_invalid_string(self):
        with self.assertRaises(ValueError):
            _normalize_date("Jan 15 2025")


if __name__ == "__main__":
    unittest.main()
