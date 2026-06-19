#!/usr/bin/env python
"""
Live end-to-end test of the ServiceNow MCP *incident* tools.

Unlike the unit tests (which mock HTTP), this drives the real tool functions in
``servicenow_mcp.tools.incident_tools`` against a live instance using the
credentials in your ``.env`` file, and then INDEPENDENTLY re-fetches each record
to confirm the change actually persisted on the ServiceNow side.

Why the re-fetch matters: the Table API often returns HTTP 200 even when it
silently ignores an invalid field value (e.g. a bad datetime) or refuses a state
transition. A tool can therefore report ``success=True`` while nothing changed.
This script verifies the *effect*, not just the status code.

Usage:
    .venv/Scripts/python scripts/test_incidents_live.py
    .venv/Scripts/python scripts/test_incidents_live.py --keep   # don't delete the test incident
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
    ApiKeyConfig,
    AuthConfig,
    AuthType,
    BasicAuthConfig,
    OAuthConfig,
    ServerConfig,
)
from servicenow_mcp.tools.incident_tools import (  # noqa: E402
    AddCommentParams,
    CloseIncidentParams,
    CreateIncidentParams,
    DeleteIncidentParams,
    GetIncidentByNumberParams,
    GetIncidentParams,
    ListIncidentsParams,
    ReopenIncidentParams,
    ResolveIncidentParams,
    UpdateIncidentParams,
    add_comment,
    close_incident,
    create_incident,
    delete_incident,
    get_incident,
    get_incident_by_number,
    list_incidents,
    reopen_incident,
    resolve_incident,
    update_incident,
)

GREEN, RED, YEL, DIM, RST = "\033[92m", "\033[91m", "\033[93m", "\033[2m", "\033[0m"
results = []


def record(name, ok, detail=""):
    tag = f"{GREEN}PASS{RST}" if ok else f"{RED}FAIL{RST}"
    print(f"  [{tag}] {name}")
    if detail:
        print(f"         {DIM}{detail}{RST}")
    results.append((name, ok, detail))


def build_config() -> ServerConfig:
    load_dotenv()
    url = os.getenv("SERVICENOW_INSTANCE_URL")
    if not url or "XXXXXX" in url or url.endswith("your-instance.service-now.com"):
        sys.exit(f"{RED}Set SERVICENOW_INSTANCE_URL in .env to your real PDI URL first.{RST}")
    auth_type = AuthType(os.getenv("SERVICENOW_AUTH_TYPE", "basic").lower())
    if auth_type == AuthType.BASIC:
        auth = AuthConfig(type=auth_type, basic=BasicAuthConfig(
            username=os.getenv("SERVICENOW_USERNAME"),
            password=os.getenv("SERVICENOW_PASSWORD"),
        ))
    elif auth_type == AuthType.OAUTH:
        auth = AuthConfig(type=auth_type, oauth=OAuthConfig(
            client_id=os.getenv("SERVICENOW_CLIENT_ID"),
            client_secret=os.getenv("SERVICENOW_CLIENT_SECRET"),
            username=os.getenv("SERVICENOW_USERNAME"),
            password=os.getenv("SERVICENOW_PASSWORD"),
            token_url=os.getenv("SERVICENOW_TOKEN_URL"),
        ))
    else:
        auth = AuthConfig(type=auth_type, api_key=ApiKeyConfig(
            api_key=os.getenv("SERVICENOW_API_KEY"),
            header_name=os.getenv("SERVICENOW_API_KEY_HEADER", "X-ServiceNow-API-Key"),
        ))
    return ServerConfig(instance_url=url, auth=auth, debug=True,
                        timeout=int(os.getenv("SERVICENOW_TIMEOUT", "30")))


def fetch_raw(config, auth, sys_id, display=False):
    """Independent oracle: read the record's raw field values straight from the API."""
    r = requests.get(
        f"{config.api_url}/table/incident/{sys_id}",
        params={"sysparm_display_value": str(display).lower(),
                "sysparm_exclude_reference_link": "true"},
        headers=auth.get_headers(), timeout=config.timeout,
    )
    r.raise_for_status()
    return r.json().get("result", {})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true", help="Do not delete the test incident at the end")
    args = ap.parse_args()

    config = build_config()
    auth = AuthManager(config.auth, config.instance_url)
    print(f"\nInstance: {config.instance_url}   auth={config.auth.type.value}\n")

    sys_id = number = None

    # 1) CREATE -----------------------------------------------------------------
    print("1) create_incident")
    resp = create_incident(config, auth, CreateIncidentParams(
        short_description="[MCP live test] please ignore",
        description="Created by scripts/test_incidents_live.py",
        urgency="3", impact="3",
    ))
    record("create returns success", resp.success, resp.message)
    if not resp.success:
        sys.exit(f"{RED}Cannot continue without a created incident.{RST}")
    sys_id, number = resp.incident_id, resp.incident_number
    print(f"         {DIM}created {number} ({sys_id}){RST}")

    # 2) GET BY NUMBER ----------------------------------------------------------
    print("2) get_incident_by_number")
    g = get_incident_by_number(config, auth, GetIncidentByNumberParams(incident_number=number))
    record("get_incident_by_number finds it", g.get("success") and g.get("incident", {}).get("number") == number)

    # 3) LIST -------------------------------------------------------------------
    print("3) list_incidents")
    lst = list_incidents(config, auth, ListIncidentsParams(limit=50))
    found = any(i.get("number") == number for i in lst.get("incidents", []))
    record("list_incidents includes it", lst.get("success") and found,
           f"{len(lst.get('incidents', []))} returned")

    # 4) UPDATE a plain field ---------------------------------------------------
    print("4) update_incident (short_description)")
    new_desc = "[MCP live test] short description UPDATED"
    u = update_incident(config, auth, UpdateIncidentParams(incident_id=number, short_description=new_desc))
    after = fetch_raw(config, auth, sys_id)
    record("update returns success", u.success, u.message)
    record("short_description actually changed", after.get("short_description") == new_desc,
           f"server now has: {after.get('short_description')!r}")

    # 5) CHANGE STATE -----------------------------------------------------------
    print("5) update_incident (state -> 2 'In Progress')")
    u2 = update_incident(config, auth, UpdateIncidentParams(incident_id=number, state="2"))
    after2 = fetch_raw(config, auth, sys_id)
    record("state-change update returns success", u2.success, u2.message)
    record("state actually became '2'", str(after2.get("state")) == "2",
           f"server now has state={after2.get('state')!r}  (this is the 'cannot change states' check)")

    # 6) COMMENT + WORK NOTE ----------------------------------------------------
    print("6) add_comment (customer comment + work note)")
    c1 = add_comment(config, auth, AddCommentParams(incident_id=number, comment="Customer-visible comment from MCP test"))
    c2 = add_comment(config, auth, AddCommentParams(incident_id=number, comment="Internal work note from MCP test", is_work_note=True))
    record("add_comment (comment) returns success", c1.success, c1.message)
    record("add_comment (work note) returns success", c2.success, c2.message)

    # 7) RESOLVE ----------------------------------------------------------------
    print("7) resolve_incident")
    r = resolve_incident(config, auth, ResolveIncidentParams(
        incident_id=number, resolution_code="Solution provided",
        resolution_notes="Resolved by MCP live test",
    ))
    after3 = fetch_raw(config, auth, sys_id)
    record("resolve returns success", r.success, r.message)
    record("state actually became '6' (Resolved)", str(after3.get("state")) == "6",
           f"server now has state={after3.get('state')!r}")
    record("resolved_at is a real timestamp (not literal 'now')",
           bool(after3.get("resolved_at")) and after3.get("resolved_at") != "now",
           f"resolved_at={after3.get('resolved_at')!r}")
    record("close_code persisted", bool(after3.get("close_code")),
           f"close_code={after3.get('close_code')!r}")

    # 8) GET (generic, by number) ----------------------------------------------
    print("8) get_incident (generic, by number or sys_id)")
    g2 = get_incident(config, auth, GetIncidentParams(incident_id=number))
    record("get_incident finds it by number", g2.get("success") and g2.get("incident", {}).get("sys_id") == sys_id)
    g3 = get_incident(config, auth, GetIncidentParams(incident_id=sys_id))
    record("get_incident finds it by sys_id", g3.get("success") and g3.get("incident", {}).get("number") == number)
    inc = g2.get("incident", {})
    record("get_incident returns state CODE + label",
           str(inc.get("state")) == "6" and inc.get("state_display") == "Resolved",
           f"state={inc.get('state')!r} state_display={inc.get('state_display')!r}")

    # 9) REOPEN -----------------------------------------------------------------
    print("9) reopen_incident")
    ro = reopen_incident(config, auth, ReopenIncidentParams(incident_id=number, reopen_notes="reopened by test"))
    after_ro = fetch_raw(config, auth, sys_id)
    record("reopen returns success", ro.success, ro.message)
    record("state actually became '2' (In Progress)", str(after_ro.get("state")) == "2",
           f"server now has state={after_ro.get('state')!r}")

    # 10) CLOSE -----------------------------------------------------------------
    print("10) close_incident")
    cl = close_incident(config, auth, CloseIncidentParams(
        incident_id=number, close_code="Solution provided", close_notes="closed by test"))
    after_cl = fetch_raw(config, auth, sys_id)
    record("close returns success", cl.success, cl.message)
    record("state actually became '7' (Closed)", str(after_cl.get("state")) == "7",
           f"server now has state={after_cl.get('state')!r}")

    # 11) DELETE ----------------------------------------------------------------
    if not args.keep:
        print("11) delete_incident")
        d = delete_incident(config, auth, DeleteIncidentParams(incident_id=number))
        record("delete returns success", d.success, d.message)
        gone = requests.get(f"{config.api_url}/table/incident/{sys_id}",
                            headers=auth.get_headers(), timeout=config.timeout)
        record("incident is actually gone (404)", gone.status_code == 404,
               f"GET after delete -> HTTP {gone.status_code}")
    else:
        print(f"\n{DIM}--keep: left test incident {number} ({sys_id}) on the instance{RST}")

    # summary -------------------------------------------------------------------
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    color = GREEN if passed == total else RED
    print(f"\n{color}==== {passed}/{total} checks passed ===={RST}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
