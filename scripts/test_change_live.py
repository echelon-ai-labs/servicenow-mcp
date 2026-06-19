#!/usr/bin/env python
"""
Live end-to-end test of the ServiceNow MCP *change management* tools.

Drives the real tool functions against a live instance (creds from .env) and
re-fetches each record to confirm changes persisted:

  create -> get_details (by number) -> list -> update -> add_change_task ->
  submit_for_approval -> approve -> reject -> delete

Change *state* transitions are governed by the Change Model state machine and
are not settable via the Table API; the approval lifecycle is driven through the
writable `approval` field, which is what these tools do.

Usage:
    .venv/Scripts/python scripts/test_change_live.py [--keep]
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
from servicenow_mcp.tools.change_tools import (  # noqa: E402
    add_change_task, approve_change, create_change_request, get_change_request_details,
    list_change_requests, reject_change, submit_change_for_approval, update_change_request,
)

GREEN, RED, DIM, RST = "\033[92m", "\033[91m", "\033[2m", "\033[0m"
results = []


def record(name, ok, detail=""):
    print(f"  [{GREEN+'PASS'+RST if ok else RED+'FAIL'+RST}] {name}")
    if detail:
        print(f"         {DIM}{detail}{RST}")
    results.append(ok)


def build_config():
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
    r = requests.get(f"{config.api_url}/table/change_request/{sys_id}",
                     params={"sysparm_fields": field}, headers=auth.get_headers(), timeout=config.timeout)
    r.raise_for_status()
    return r.json().get("result", {}).get(field)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()
    config = build_config()
    auth = AuthManager(config.auth, config.instance_url)
    # change tools are invoked the same way the server invokes them: (config, auth, params)
    print(f"\nInstance: {config.instance_url}  auth={config.auth.type.value}\n")

    print("1) create_change_request (type=normal)")
    c = create_change_request(config, auth, {
        "short_description": "[MCP e2e] upgrade database server", "type": "normal",
        "description": "End-to-end test change", "risk": "3", "impact": "3", "category": "Hardware"})
    record("create returns success", c.get("success"), c.get("message", ""))
    if not c.get("success"):
        sys.exit(f"{RED}stop: create failed{RST}")
    cr = c["change_request"]
    num, sid = cr["number"], cr["sys_id"]
    print(f"         {DIM}created {num} ({sid}) state={cr.get('state')}{RST}")

    print("2) get_change_request_details (by NUMBER -> exercises resolution)")
    g = get_change_request_details(config, auth, {"change_id": num})
    record("get_details by number works", g.get("success") and g["change_request"]["number"] == num)

    print("3) list_change_requests (query)")
    lst = list_change_requests(config, auth, {"query": "short_descriptionLIKEMCP e2e", "limit": 20})
    record("list includes it", lst.get("success") and any(x.get("number") == num for x in lst.get("change_requests", [])))

    print("4) update_change_request by number (description/risk/impact)")
    u = update_change_request(config, auth, {"change_id": num, "description": "Updated by e2e", "risk": "2", "impact": "2"})
    record("update returns success", u.get("success"), u.get("message", ""))
    record("risk changed to 2", raw(config, auth, sid, "risk") == "2", f"risk={raw(config, auth, sid, 'risk')!r}")

    print("5) add_change_task (by number)")
    t = add_change_task(config, auth, {"change_id": num, "short_description": "Take DB backup", "description": "pre-change backup"})
    record("add_change_task success", t.get("success"), t.get("message", ""))
    g2 = get_change_request_details(config, auth, {"change_id": sid})
    record("task appears on the change", any(tk.get("short_description") == "Take DB backup" for tk in g2.get("tasks", [])),
           f"{len(g2.get('tasks', []))} task(s)")

    print("6) submit_change_for_approval")
    s = submit_change_for_approval(config, auth, {"change_id": num, "approval_comments": "Please review"})
    record("submit returns success", s.get("success"), s.get("message", ""))
    record("approval = requested", raw(config, auth, sid, "approval") == "requested",
           f"approval={raw(config, auth, sid, 'approval')!r}")

    print("7) approve_change")
    a = approve_change(config, auth, {"change_id": num, "approval_comments": "LGTM"})
    record("approve returns success", a.get("success"), a.get("message", ""))
    record("approval = approved", raw(config, auth, sid, "approval") == "approved",
           f"approval={raw(config, auth, sid, 'approval')!r}")

    print("8) reject_change")
    r = reject_change(config, auth, {"change_id": num, "rejection_reason": "Insufficient backout plan"})
    record("reject returns success", r.get("success"), r.get("message", ""))
    record("approval = rejected", raw(config, auth, sid, "approval") == "rejected",
           f"approval={raw(config, auth, sid, 'approval')!r}")

    if not args.keep:
        d = requests.delete(f"{config.api_url}/table/change_request/{sid}", headers=auth.get_headers(), timeout=config.timeout)
        print(f"\n{DIM}cleanup: deleted {num} (HTTP {d.status_code}){RST}")
    else:
        print(f"\n{DIM}--keep: left {num} ({sid}){RST}")

    passed, total = sum(results), len(results)
    print(f"\n{(GREEN if passed == total else RED)}==== {passed}/{total} checks passed ===={RST}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
