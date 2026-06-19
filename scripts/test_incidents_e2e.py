#!/usr/bin/env python
"""
Scenario-driven end-to-end test of the ServiceNow MCP incident tools.

Mirrors a real service-desk flow against a live instance using the credentials
in ``.env``, driving the actual tool functions and independently re-fetching the
record (and the journal table) to confirm each change really persisted:

  create (caller + channel + urgency/impact) -> get -> customer comment +
  internal work note -> change urgency/impact (priority recalculates) ->
  change state -> assign group + assignee (by name) -> resolve -> reopen ->
  close -> delete.

Usage:
    .venv/Scripts/python scripts/test_incidents_e2e.py
    .venv/Scripts/python scripts/test_incidents_e2e.py --keep
"""

import argparse
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from servicenow_mcp.auth.auth_manager import AuthManager  # noqa: E402
from servicenow_mcp.utils.config import (  # noqa: E402
    ApiKeyConfig, AuthConfig, AuthType, BasicAuthConfig, OAuthConfig, ServerConfig,
)
from servicenow_mcp.tools.incident_tools import (  # noqa: E402
    AddCommentParams, CloseIncidentParams, CreateIncidentParams, DeleteIncidentParams,
    GetIncidentByNumberParams, ReopenIncidentParams, ResolveIncidentParams, UpdateIncidentParams,
    add_comment, close_incident, create_incident, delete_incident, get_incident_by_number,
    reopen_incident, resolve_incident, update_incident,
)

GREEN, RED, DIM, RST = "\033[92m", "\033[91m", "\033[2m", "\033[0m"
results = []


def record(name, ok, detail=""):
    print(f"  [{GREEN+'PASS'+RST if ok else RED+'FAIL'+RST}] {name}")
    if detail:
        print(f"         {DIM}{detail}{RST}")
    results.append(ok)


def build_config() -> ServerConfig:
    load_dotenv()
    url = os.getenv("SERVICENOW_INSTANCE_URL")
    if not url or "XXXXXX" in url:
        sys.exit(f"{RED}Set SERVICENOW_INSTANCE_URL in .env first.{RST}")
    t = AuthType(os.getenv("SERVICENOW_AUTH_TYPE", "basic").lower())
    if t == AuthType.BASIC:
        auth = AuthConfig(type=t, basic=BasicAuthConfig(
            username=os.getenv("SERVICENOW_USERNAME"), password=os.getenv("SERVICENOW_PASSWORD")))
    elif t == AuthType.OAUTH:
        auth = AuthConfig(type=t, oauth=OAuthConfig(
            client_id=os.getenv("SERVICENOW_CLIENT_ID"), client_secret=os.getenv("SERVICENOW_CLIENT_SECRET"),
            username=os.getenv("SERVICENOW_USERNAME"), password=os.getenv("SERVICENOW_PASSWORD"),
            token_url=os.getenv("SERVICENOW_TOKEN_URL")))
    else:
        auth = AuthConfig(type=t, api_key=ApiKeyConfig(
            api_key=os.getenv("SERVICENOW_API_KEY"),
            header_name=os.getenv("SERVICENOW_API_KEY_HEADER", "X-ServiceNow-API-Key")))
    return ServerConfig(instance_url=url, auth=auth, timeout=int(os.getenv("SERVICENOW_TIMEOUT", "30")))


def raw(config, auth, sys_id, field):
    """Read one field as {value, display_value} straight from the API (the oracle)."""
    r = requests.get(f"{config.api_url}/table/incident/{sys_id}",
                     params={"sysparm_display_value": "all", "sysparm_fields": field},
                     headers=auth.get_headers(), timeout=config.timeout)
    r.raise_for_status()
    v = r.json().get("result", {}).get(field)
    return v if isinstance(v, dict) else {"value": v, "display_value": v}


def journal(config, auth, sys_id, element):
    r = requests.get(f"{config.api_url}/table/sys_journal_field",
                     params={"sysparm_query": f"element_id={sys_id}^element={element}",
                             "sysparm_fields": "value", "sysparm_limit": "20"},
                     headers=auth.get_headers(), timeout=config.timeout)
    r.raise_for_status()
    return [x.get("value") for x in r.json().get("result", [])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()
    config = build_config()
    auth = AuthManager(config.auth, config.instance_url)
    print(f"\nInstance: {config.instance_url}  auth={config.auth.type.value}\n")

    # 1) CREATE with caller (by name), channel, urgency/impact -----------------
    print("1) create_incident  (caller='Abel Tuter', channel='phone', urgency=2, impact=2)")
    c = create_incident(config, auth, CreateIncidentParams(
        short_description="[MCP e2e] keyboard not working", description="End-to-end test incident",
        caller_id="Abel Tuter", channel="phone", urgency="2", impact="2", category="hardware"))
    record("create returns success", c.success, c.message)
    if not c.success:
        sys.exit(f"{RED}stop: create failed{RST}")
    sid, num = c.incident_id, c.incident_number
    print(f"         {DIM}created {num} ({sid}){RST}")
    record("caller resolved to Abel Tuter", raw(config, auth, sid, "caller_id")["display_value"] == "Abel Tuter")
    record("channel set to Phone", raw(config, auth, sid, "contact_type")["display_value"] == "Phone",
           f"contact_type={raw(config, auth, sid, 'contact_type')}")
    pr = raw(config, auth, sid, "priority")
    record("priority auto-calculated from urgency*impact", pr["value"] in ("3", "4"),
           f"urgency=2,impact=2 -> priority={pr['display_value']!r}")

    # 2) GET --------------------------------------------------------------------
    print("2) get_incident_by_number")
    g = get_incident_by_number(config, auth, GetIncidentByNumberParams(incident_number=num))
    record("get_incident_by_number finds it", g.get("success") and g["incident"]["number"] == num)

    # 3) COMMENTS: customer-facing + internal work note ------------------------
    print("3) add_comment  (customer comment + internal work note)")
    add_comment(config, auth, AddCommentParams(incident_id=num, comment="Customer: I tried rebooting, no luck."))
    add_comment(config, auth, AddCommentParams(incident_id=num, comment="Internal: dispatching a replacement keyboard.", is_work_note=True))
    record("customer comment stored in journal", "Customer: I tried rebooting, no luck." in journal(config, auth, sid, "comments"))
    record("internal note stored as work_note", "Internal: dispatching a replacement keyboard." in journal(config, auth, sid, "work_notes"))

    # 4) CHANGE urgency/impact (priority recalcs) + state ----------------------
    print("4) update_incident  (urgency=1, impact=1  ->  priority recalcs; state -> In Progress)")
    update_incident(config, auth, UpdateIncidentParams(incident_id=num, urgency="1", impact="1", state="2"))
    record("urgency now 1", raw(config, auth, sid, "urgency")["value"] == "1")
    record("impact now 1", raw(config, auth, sid, "impact")["value"] == "1")
    record("priority recalculated to 1 (Critical)", raw(config, auth, sid, "priority")["value"] == "1",
           f"priority={raw(config, auth, sid, 'priority')['display_value']!r}")
    record("state now In Progress (2)", raw(config, auth, sid, "state")["value"] == "2")

    # 5) ASSIGN group + person (by name) ---------------------------------------
    # NB: this PDI has a custom "Abort changes on group" rule that rejects setting
    # a group + an assignee who isn't a member of it in one update; Beth Anglin is
    # a Service Desk member.
    print("5) update_incident  (assignment_group='Service Desk', assigned_to='Beth Anglin')")
    u = update_incident(config, auth, UpdateIncidentParams(
        incident_id=num, assignment_group="Service Desk", assigned_to="Beth Anglin"))
    record("assign update returns success", u.success, u.message)
    record("assignment_group = Service Desk", raw(config, auth, sid, "assignment_group")["display_value"] == "Service Desk",
           f"group={raw(config, auth, sid, 'assignment_group')['display_value']!r}")
    record("assigned_to = Beth Anglin", raw(config, auth, sid, "assigned_to")["display_value"] == "Beth Anglin",
           f"assignee={raw(config, auth, sid, 'assigned_to')['display_value']!r}")

    # 6) RESOLVE ----------------------------------------------------------------
    print("6) resolve_incident")
    r = resolve_incident(config, auth, ResolveIncidentParams(
        incident_id=num, resolution_code="Solution provided", resolution_notes="Replaced keyboard; verified working."))
    record("resolve returns success", r.success, r.message)
    record("state = Resolved (6)", raw(config, auth, sid, "state")["value"] == "6")
    record("resolved_at populated", bool(raw(config, auth, sid, "resolved_at")["value"]))

    # 7) REOPEN then CLOSE ------------------------------------------------------
    print("7) reopen_incident -> close_incident")
    reopen_incident(config, auth, ReopenIncidentParams(incident_id=num, reopen_notes="Customer says issue recurred."))
    record("reopened to In Progress (2)", raw(config, auth, sid, "state")["value"] == "2")
    close_incident(config, auth, CloseIncidentParams(incident_id=num, close_code="Solution provided", close_notes="Permanent fix applied."))
    record("closed (7)", raw(config, auth, sid, "state")["value"] == "7")

    # 8) DELETE -----------------------------------------------------------------
    if not args.keep:
        print("8) delete_incident")
        d = delete_incident(config, auth, DeleteIncidentParams(incident_id=num))
        record("delete returns success", d.success, d.message)
        gone = requests.get(f"{config.api_url}/table/incident/{sid}", headers=auth.get_headers(), timeout=config.timeout)
        record("incident gone (404)", gone.status_code == 404)
    else:
        print(f"\n{DIM}--keep: left {num} ({sid}) on the instance{RST}")

    passed, total = sum(results), len(results)
    print(f"\n{(GREEN if passed == total else RED)}==== {passed}/{total} checks passed ===={RST}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
