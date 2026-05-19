"""
GAIL/BAIL tools for the ServiceNow MCP server.

This module provides tools for managing GAIL engagement records
and GAIL resource records in ServiceNow.
"""

import logging
import re
from datetime import date, datetime
from typing import List, Optional, Union

import requests
from pydantic import BaseModel, Field, field_validator

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import ServerConfig

logger = logging.getLogger(__name__)

# --- Constants ---

VALID_TRACKS = {"gail", "bail", "spark"}
VALID_STAGES = {
    "1_initiate",
    "2_plan",
    "3_execute",
    "4_deliver",
    "5_close",
    "bail_active",
    "bail_live",
}
VALID_HEALTH_STATUSES = {"green", "yellow", "red", "complete"}
VALID_REGIONS = {"ams", "emea", "apac", "idc"}
VALID_AVAILABILITY_STATUSES = {
    "available",
    "unavailable",
    "unavailable_post_engagement",
}

SYS_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")

ENGAGEMENT_TABLE = "x_snc_gail_get_ai_engagement"
RESOURCE_TABLE = "x_snc_gail_get_ai_resource"


# --- Helpers ---


def _validate_sys_id(value: str) -> bool:
    return bool(SYS_ID_PATTERN.match(value))


def _normalize_sys_id_list(value: Union[str, List[str], None]) -> Optional[str]:
    """Normalize a sys_id list field to a comma-separated string.

    Accepts either a comma-separated string or a Python list of sys_ids.
    Validates each entry is 32 hex chars.
    """
    if value is None:
        return None

    if isinstance(value, list):
        ids = value
    else:
        ids = [s.strip() for s in value.split(",") if s.strip()]

    for sid in ids:
        if not _validate_sys_id(sid):
            raise ValueError(
                f"Invalid sys_id in list: '{sid}' (must be 32 hex characters)"
            )
    return ",".join(ids)


def _normalize_date(value: Union[str, date, datetime, None]) -> Optional[str]:
    """Normalize a date value to YYYY-MM-DD string."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.isoformat()
    # Validate string format
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise ValueError(
            f"Invalid date format: '{value}' (expected YYYY-MM-DD)"
        )
    return value


# --- Parameter Models ---


class CreateGailEngagementParams(BaseModel):
    """Parameters for creating a GAIL engagement record."""

    customer_name: str = Field(
        ..., max_length=200, description="Customer name (mandatory)"
    )
    track: str = Field(
        "gail",
        description="Engagement track: gail, bail, or spark",
    )
    stage: str = Field(
        "1_initiate",
        description="Engagement stage: 1_initiate, 2_plan, 3_execute, 4_deliver, 5_close, bail_active, bail_live",
    )
    health_status: str = Field(
        "green",
        description="Health status: green, yellow, red, complete",
    )
    customer_geo: Optional[str] = Field(
        None, max_length=300, description="Customer geography (free text)"
    )
    engineers: Optional[Union[str, List[str]]] = Field(
        None,
        description="Comma-separated sys_ids or list of sys_ids for engineer resources",
    )
    engagement_managers: Optional[Union[str, List[str]]] = Field(
        None,
        description="Comma-separated sys_ids or list of sys_ids for engagement manager resources",
    )
    architects: Optional[Union[str, List[str]]] = Field(
        None,
        description="Comma-separated sys_ids or list of sys_ids for architect resources",
    )
    ai_agents_itsm: Optional[bool] = Field(None, description="AI Agents ITSM flag")
    ai_agents_csm: Optional[bool] = Field(None, description="AI Agents CSM flag")
    ai_agents_hr: Optional[bool] = Field(None, description="AI Agents HR flag")
    ai_agents_va: Optional[bool] = Field(None, description="AI Agents VA flag")
    scope_details: Optional[str] = Field(
        None, max_length=4000, description="Scope details"
    )
    notes_escalation_log: Optional[str] = Field(
        None, max_length=4000, description="Notes / escalation log"
    )
    sn_release_version: Optional[str] = Field(
        None, max_length=100, description="ServiceNow release version"
    )
    exit_criteria: Optional[str] = Field(
        None, max_length=4000, description="Exit criteria"
    )
    intake_request: Optional[str] = Field(
        None, max_length=200, description="Intake request reference"
    )
    date_customer_intro: Optional[Union[str, date, datetime]] = Field(
        None, description="Customer intro date (YYYY-MM-DD)"
    )
    date_assess_kickoff: Optional[Union[str, date, datetime]] = Field(
        None, description="Assessment kickoff date (YYYY-MM-DD)"
    )
    date_workshop_dev_test: Optional[Union[str, date, datetime]] = Field(
        None, description="Workshop/dev/test date (YYYY-MM-DD)"
    )
    date_target_golive: Optional[Union[str, date, datetime]] = Field(
        None, description="Target go-live date (YYYY-MM-DD)"
    )
    date_uat: Optional[Union[str, date, datetime]] = Field(
        None, description="UAT date (YYYY-MM-DD)"
    )
    date_internal_kt: Optional[Union[str, date, datetime]] = Field(
        None, description="Internal KT date (YYYY-MM-DD)"
    )

    @field_validator("customer_name")
    @classmethod
    def customer_name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("customer_name must not be empty")
        return v

    @field_validator("track")
    @classmethod
    def validate_track(cls, v: str) -> str:
        if v not in VALID_TRACKS:
            raise ValueError(
                f"Invalid track: '{v}'. Must be one of: {', '.join(sorted(VALID_TRACKS))}"
            )
        return v

    @field_validator("stage")
    @classmethod
    def validate_stage(cls, v: str) -> str:
        if v not in VALID_STAGES:
            raise ValueError(
                f"Invalid stage: '{v}'. Must be one of: {', '.join(sorted(VALID_STAGES))}"
            )
        return v

    @field_validator("health_status")
    @classmethod
    def validate_health_status(cls, v: str) -> str:
        if v not in VALID_HEALTH_STATUSES:
            raise ValueError(
                f"Invalid health_status: '{v}'. Must be one of: {', '.join(sorted(VALID_HEALTH_STATUSES))}"
            )
        return v


class UpdateGailEngagementParams(BaseModel):
    """Parameters for updating an existing GAIL engagement record.

    Partial update — only fields explicitly provided are modified;
    omitted/None fields are left alone on the instance. To clear a
    glide_list field (e.g., remove all engineers), pass an empty string
    or empty list.
    """

    sys_id: str = Field(
        ..., description="sys_id of the engagement record to update (32 hex characters)"
    )
    customer_name: Optional[str] = Field(
        None, max_length=200, description="Customer name"
    )
    track: Optional[str] = Field(
        None,
        description="Engagement track: gail, bail, or spark",
    )
    stage: Optional[str] = Field(
        None,
        description="Engagement stage: 1_initiate, 2_plan, 3_execute, 4_deliver, 5_close, bail_active, bail_live",
    )
    health_status: Optional[str] = Field(
        None,
        description="Health status: green, yellow, red, complete",
    )
    customer_geo: Optional[str] = Field(
        None, max_length=300, description="Customer geography (free text)"
    )
    engineers: Optional[Union[str, List[str]]] = Field(
        None,
        description="Comma-separated sys_ids or list of sys_ids for engineer resources. Empty string or empty list clears the field.",
    )
    engagement_managers: Optional[Union[str, List[str]]] = Field(
        None,
        description="Comma-separated sys_ids or list of sys_ids for engagement manager resources. Empty string or empty list clears the field.",
    )
    architects: Optional[Union[str, List[str]]] = Field(
        None,
        description="Comma-separated sys_ids or list of sys_ids for architect resources. Empty string or empty list clears the field.",
    )
    ai_agents_itsm: Optional[bool] = Field(None, description="AI Agents ITSM flag")
    ai_agents_csm: Optional[bool] = Field(None, description="AI Agents CSM flag")
    ai_agents_hr: Optional[bool] = Field(None, description="AI Agents HR flag")
    ai_agents_va: Optional[bool] = Field(None, description="AI Agents VA flag")
    scope_details: Optional[str] = Field(
        None, max_length=4000, description="Scope details"
    )
    notes_escalation_log: Optional[str] = Field(
        None, max_length=4000, description="Notes / escalation log"
    )
    sn_release_version: Optional[str] = Field(
        None, max_length=100, description="ServiceNow release version"
    )
    exit_criteria: Optional[str] = Field(
        None, max_length=4000, description="Exit criteria"
    )
    intake_request: Optional[str] = Field(
        None, max_length=200, description="Intake request reference"
    )
    date_customer_intro: Optional[Union[str, date, datetime]] = Field(
        None, description="Customer intro date (YYYY-MM-DD)"
    )
    date_assess_kickoff: Optional[Union[str, date, datetime]] = Field(
        None, description="Assessment kickoff date (YYYY-MM-DD)"
    )
    date_workshop_dev_test: Optional[Union[str, date, datetime]] = Field(
        None, description="Workshop/dev/test date (YYYY-MM-DD)"
    )
    date_target_golive: Optional[Union[str, date, datetime]] = Field(
        None, description="Target go-live date (YYYY-MM-DD)"
    )
    date_uat: Optional[Union[str, date, datetime]] = Field(
        None, description="UAT date (YYYY-MM-DD)"
    )
    date_internal_kt: Optional[Union[str, date, datetime]] = Field(
        None, description="Internal KT date (YYYY-MM-DD)"
    )

    @field_validator("sys_id")
    @classmethod
    def validate_sys_id(cls, v: str) -> str:
        if not _validate_sys_id(v):
            raise ValueError(
                f"Invalid sys_id: '{v}' (must be 32 hex characters)"
            )
        return v

    @field_validator("track")
    @classmethod
    def validate_track(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.lower() not in VALID_TRACKS:
            raise ValueError(
                f"Invalid track: '{v}'. Must be one of: {', '.join(sorted(VALID_TRACKS))}"
            )
        return v.lower() if v is not None else v

    @field_validator("stage")
    @classmethod
    def validate_stage(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.lower() not in VALID_STAGES:
            raise ValueError(
                f"Invalid stage: '{v}'. Must be one of: {', '.join(sorted(VALID_STAGES))}"
            )
        return v.lower() if v is not None else v

    @field_validator("health_status")
    @classmethod
    def validate_health_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.lower() not in VALID_HEALTH_STATUSES:
            raise ValueError(
                f"Invalid health_status: '{v}'. Must be one of: {', '.join(sorted(VALID_HEALTH_STATUSES))}"
            )
        return v.lower() if v is not None else v


class UpdateGailResourceParams(BaseModel):
    """Parameters for updating a GAIL resource record."""

    sys_id: str = Field(
        ..., description="sys_id of the resource record (32 hex characters)"
    )
    name: Optional[str] = Field(None, max_length=200, description="Resource name")
    region: Optional[str] = Field(
        None, description="Region: ams, emea, apac, idc"
    )
    availability_status: Optional[str] = Field(
        None,
        description="Availability status: available, unavailable, unavailable_post_engagement",
    )
    bail_live_count: Optional[int] = Field(None, description="BAIL live count")
    bail_active_count: Optional[int] = Field(None, description="BAIL active count")
    stage_initiate_count: Optional[int] = Field(None, description="Stage initiate count")
    stage_plan_count: Optional[int] = Field(None, description="Stage plan count")
    stage_execute_count: Optional[int] = Field(None, description="Stage execute count")
    stage_deliver_count: Optional[int] = Field(None, description="Stage deliver count")
    stage_close_count: Optional[int] = Field(None, description="Stage close count")
    total_active_count: Optional[int] = Field(None, description="Total active count")
    email: Optional[str] = Field(None, description="Email address")
    title: Optional[str] = Field(None, description="Job title")
    department: Optional[str] = Field(None, description="Department")
    role: Optional[str] = Field(None, description="Role")
    employer: Optional[str] = Field(None, description="Employer")
    location: Optional[str] = Field(None, max_length=300, description="Location")
    languages_spoken: Optional[str] = Field(None, description="Languages spoken")
    areas_of_expertise: Optional[str] = Field(
        None, max_length=4000, description="Areas of expertise"
    )
    time_off: Optional[str] = Field(
        None, max_length=4000, description="Notes/Concerns (time off)"
    )
    active_accounts: Optional[str] = Field(
        None, max_length=4000, description="Active accounts"
    )
    accounts_gone_live: Optional[str] = Field(
        None, max_length=4000, description="Accounts gone live"
    )
    date_added: Optional[Union[str, date, datetime]] = Field(
        None, description="Date added (YYYY-MM-DD)"
    )
    date_added_to_program: Optional[Union[str, date, datetime]] = Field(
        None, description="Date added to program (YYYY-MM-DD)"
    )

    @field_validator("sys_id")
    @classmethod
    def validate_sys_id(cls, v: str) -> str:
        if not _validate_sys_id(v):
            raise ValueError(
                f"Invalid sys_id: '{v}' (must be 32 hex characters)"
            )
        return v

    @field_validator("region")
    @classmethod
    def validate_region(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_REGIONS:
            raise ValueError(
                f"Invalid region: '{v}'. Must be one of: {', '.join(sorted(VALID_REGIONS))}"
            )
        return v

    @field_validator("availability_status")
    @classmethod
    def validate_availability_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_AVAILABILITY_STATUSES:
            raise ValueError(
                f"Invalid availability_status: '{v}'. Must be one of: {', '.join(sorted(VALID_AVAILABILITY_STATUSES))}"
            )
        return v


# --- Tool Implementations ---


def create_gail_engagement(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: CreateGailEngagementParams,
) -> dict:
    """
    Create a new GAIL engagement record in ServiceNow.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for creating the engagement.

    Returns:
        Dictionary with success status, sys_id, and record data.
    """
    api_url = f"{config.api_url}/table/{ENGAGEMENT_TABLE}"

    # Build request data - start with required/defaulted fields
    data = {
        "customer_name": params.customer_name,
        "track": params.track,
        "stage": params.stage,
        "health_status": params.health_status,
    }

    # Optional string fields
    if params.customer_geo is not None:
        data["customer_geo"] = params.customer_geo
    if params.scope_details is not None:
        data["scope_details"] = params.scope_details
    if params.notes_escalation_log is not None:
        data["notes_escalation_log"] = params.notes_escalation_log
    if params.sn_release_version is not None:
        data["sn_release_version"] = params.sn_release_version
    if params.exit_criteria is not None:
        data["exit_criteria"] = params.exit_criteria
    if params.intake_request is not None:
        data["intake_request"] = params.intake_request

    # List-reference fields (normalize to comma-separated sys_ids)
    try:
        for field_name in ("engineers", "engagement_managers", "architects"):
            value = getattr(params, field_name)
            normalized = _normalize_sys_id_list(value)
            if normalized is not None:
                data[field_name] = normalized
    except ValueError as e:
        return {"success": False, "error": str(e)}

    # Boolean fields
    if params.ai_agents_itsm is not None:
        data["ai_agents_itsm"] = str(params.ai_agents_itsm).lower()
    if params.ai_agents_csm is not None:
        data["ai_agents_csm"] = str(params.ai_agents_csm).lower()
    if params.ai_agents_hr is not None:
        data["ai_agents_hr"] = str(params.ai_agents_hr).lower()
    if params.ai_agents_va is not None:
        data["ai_agents_va"] = str(params.ai_agents_va).lower()

    # Date fields
    date_fields = [
        "date_customer_intro",
        "date_assess_kickoff",
        "date_workshop_dev_test",
        "date_target_golive",
        "date_uat",
        "date_internal_kt",
    ]
    try:
        for field_name in date_fields:
            value = getattr(params, field_name)
            normalized = _normalize_date(value)
            if normalized is not None:
                data[field_name] = normalized
    except ValueError as e:
        return {"success": False, "error": str(e)}

    # Make request
    try:
        response = requests.post(
            api_url,
            json=data,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )

        if not response.ok:
            error_body = response.text
            try:
                error_body = response.json().get("error", {}).get("message", response.text)
            except Exception:
                pass
            return {
                "success": False,
                "status_code": response.status_code,
                "error": error_body,
            }

        result = response.json().get("result", {})

        return {
            "success": True,
            "sys_id": result.get("sys_id"),
            "record": result,
        }

    except requests.RequestException as e:
        logger.error(f"Failed to create GAIL engagement: {e}")
        return {
            "success": False,
            "error": f"Failed to create GAIL engagement: {str(e)}",
        }


def update_gail_engagement(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: UpdateGailEngagementParams,
) -> dict:
    """
    Update an existing GAIL engagement record in ServiceNow.

    Partial update — only fields explicitly provided in the call are modified;
    omitted/None fields are left alone on the instance. To clear a glide_list
    field (e.g., remove all engineers), pass an empty string or empty list.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for updating the engagement.

    Returns:
        Dictionary with success status, sys_id, and record data.
    """
    api_url = f"{config.api_url}/table/{ENGAGEMENT_TABLE}/{params.sys_id}"

    # Build request data from all non-None optional fields
    data = {}

    # String fields (including customer_name which is optional on update)
    string_fields = [
        "customer_name",
        "customer_geo",
        "scope_details",
        "notes_escalation_log",
        "sn_release_version",
        "exit_criteria",
        "intake_request",
    ]
    for field_name in string_fields:
        value = getattr(params, field_name)
        if value is not None:
            data[field_name] = value

    # Choice fields (already validated by Pydantic)
    if params.track is not None:
        data["track"] = params.track
    if params.stage is not None:
        data["stage"] = params.stage
    if params.health_status is not None:
        data["health_status"] = params.health_status

    # List-reference fields (normalize to comma-separated sys_ids)
    try:
        for field_name in ("engineers", "engagement_managers", "architects"):
            value = getattr(params, field_name)
            if value is None:
                continue
            # Handle empty list → clear directive
            if isinstance(value, list) and len(value) == 0:
                data[field_name] = ""
                continue
            # Handle empty string → clear directive
            if isinstance(value, str) and value.strip() == "":
                data[field_name] = ""
                continue
            normalized = _normalize_sys_id_list(value)
            if normalized is not None:
                data[field_name] = normalized
    except ValueError as e:
        return {"success": False, "error": str(e)}

    # Boolean fields
    if params.ai_agents_itsm is not None:
        data["ai_agents_itsm"] = str(params.ai_agents_itsm).lower()
    if params.ai_agents_csm is not None:
        data["ai_agents_csm"] = str(params.ai_agents_csm).lower()
    if params.ai_agents_hr is not None:
        data["ai_agents_hr"] = str(params.ai_agents_hr).lower()
    if params.ai_agents_va is not None:
        data["ai_agents_va"] = str(params.ai_agents_va).lower()

    # Date fields
    date_fields = [
        "date_customer_intro",
        "date_assess_kickoff",
        "date_workshop_dev_test",
        "date_target_golive",
        "date_uat",
        "date_internal_kt",
    ]
    try:
        for field_name in date_fields:
            value = getattr(params, field_name)
            normalized = _normalize_date(value)
            if normalized is not None:
                data[field_name] = normalized
    except ValueError as e:
        return {"success": False, "error": str(e)}

    # Reject if nothing to update
    if not data:
        return {
            "success": False,
            "error": "Nothing to update — at least one updatable field must be provided",
        }

    # Make request
    try:
        response = requests.patch(
            api_url,
            json=data,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )

        if not response.ok:
            error_body = response.text
            try:
                error_body = response.json().get("error", {}).get("message", response.text)
            except Exception:
                pass
            return {
                "success": False,
                "status_code": response.status_code,
                "error": error_body,
            }

        result = response.json().get("result", {})

        return {
            "success": True,
            "sys_id": result.get("sys_id"),
            "record": result,
        }

    except requests.RequestException as e:
        logger.error(f"Failed to update GAIL engagement: {e}")
        return {
            "success": False,
            "error": f"Failed to update GAIL engagement: {str(e)}",
        }


def update_gail_resource(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: UpdateGailResourceParams,
) -> dict:
    """
    Update an existing GAIL resource record in ServiceNow.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for updating the resource.

    Returns:
        Dictionary with success status, sys_id, and record data.
    """
    api_url = f"{config.api_url}/table/{RESOURCE_TABLE}/{params.sys_id}"

    # Build request data from all non-None optional fields
    data = {}

    # String fields
    string_fields = [
        "name",
        "email",
        "title",
        "department",
        "role",
        "employer",
        "location",
        "languages_spoken",
        "areas_of_expertise",
        "time_off",
        "active_accounts",
        "accounts_gone_live",
    ]
    for field_name in string_fields:
        value = getattr(params, field_name)
        if value is not None:
            data[field_name] = value

    # Choice fields (already validated by Pydantic)
    if params.region is not None:
        data["region"] = params.region
    if params.availability_status is not None:
        data["availability_status"] = params.availability_status

    # Integer fields
    int_fields = [
        "bail_live_count",
        "bail_active_count",
        "stage_initiate_count",
        "stage_plan_count",
        "stage_execute_count",
        "stage_deliver_count",
        "stage_close_count",
        "total_active_count",
    ]
    for field_name in int_fields:
        value = getattr(params, field_name)
        if value is not None:
            data[field_name] = value

    # Date fields
    try:
        for field_name in ("date_added", "date_added_to_program"):
            value = getattr(params, field_name)
            normalized = _normalize_date(value)
            if normalized is not None:
                data[field_name] = normalized
    except ValueError as e:
        return {"success": False, "error": str(e)}

    # Reject if nothing to update
    if not data:
        return {"success": False, "error": "Nothing to update: no fields provided"}

    # Make request
    try:
        response = requests.patch(
            api_url,
            json=data,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )

        if not response.ok:
            error_body = response.text
            try:
                error_body = response.json().get("error", {}).get("message", response.text)
            except Exception:
                pass
            return {
                "success": False,
                "status_code": response.status_code,
                "error": error_body,
            }

        result = response.json().get("result", {})

        return {
            "success": True,
            "sys_id": result.get("sys_id"),
            "record": result,
        }

    except requests.RequestException as e:
        logger.error(f"Failed to update GAIL resource: {e}")
        return {
            "success": False,
            "error": f"Failed to update GAIL resource: {str(e)}",
        }
