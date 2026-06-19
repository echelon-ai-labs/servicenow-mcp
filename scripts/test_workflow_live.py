#!/usr/bin/env python
"""
Live end-to-end test of the ServiceNow MCP *workflow* tools.

These drive the legacy workflow engine (wf_workflow / wf_workflow_version /
wf_activity). Modern instances use Flow Designer, so the legacy engine is
typically empty and the deeper version/activity lifecycle is vestigial; this
test covers the CRUD operations that are meaningful via the Table API:

  list -> create -> get_details -> update -> activate -> deactivate ->
  list_versions -> get_activities -> delete

Usage:
    .venv/Scripts/python scripts/test_workflow_live.py [--keep]
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
from servicenow_mcp.tools.workflow_tools import (  # noqa: E402
    activate_workflow, create_workflow, deactivate_workflow, delete_workflow,
    get_workflow_activities, get_workflow_details, list_workflow_versions,
    list_workflows, update_workflow,
)

GREEN, RED, DIM, RST = "\033[92m", "\033[91m", "\033[2m", "\033[0m"
results = []


def record(name, ok_, detail=""):
    print(f"  [{GREEN+'PASS'+RST if ok_ else RED+'FAIL'+RST}] {name}")
    if detail:
        print(f"         {DIM}{detail}{RST}")
    results.append(ok_)


def ok(r):
    return isinstance(r, dict) and "error" not in r


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
    r = requests.get(f"{config.api_url}/table/wf_workflow/{sys_id}",
                     params={"sysparm_fields": field}, headers=auth.get_headers(), timeout=config.timeout)
    return r.json().get("result", {}).get(field) if r.status_code < 400 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()
    config = build_config()
    auth = AuthManager(config.auth, config.instance_url)
    # workflow tools tolerate (config, auth) order via _get_auth_and_config
    print(f"\nInstance: {config.instance_url}  auth={config.auth.type.value}\n")

    # cleanup-first: remove leftover test workflows (wf_workflow IS deletable)
    for row in requests.get(f"{config.api_url}/table/wf_workflow",
                            params={"sysparm_query": "nameLIKE[MCP e2e]", "sysparm_fields": "sys_id"},
                            headers=auth.get_headers()).json().get("result", []):
        requests.delete(f"{config.api_url}/table/wf_workflow/{row['sys_id']}", headers=auth.get_headers())

    print("1) list_workflows")
    lw = list_workflows(config, auth, {"limit": 5})
    record("list_workflows works", ok(lw), lw.get("message") or f"keys={list(lw.keys())}")

    print("2) create_workflow")
    c = create_workflow(config, auth, {"name": "[MCP e2e] workflow", "description": "e2e test", "table": "incident"})
    record("create_workflow works", bool(ok(c) and c.get("workflow", {}).get("sys_id")), c.get("error", ""))
    if not ok(c):
        sys.exit(f"{RED}stop{RST}")
    wid = c["workflow"]["sys_id"]
    print(f"         {DIM}workflow {wid}{RST}")

    print("3) get_workflow_details")
    g = get_workflow_details(config, auth, {"workflow_id": wid})
    record("get_workflow_details works", ok(g) and g.get("workflow", {}).get("sys_id") == wid)

    print("4) update_workflow")
    u = update_workflow(config, auth, {"workflow_id": wid, "description": "updated by e2e"})
    record("update_workflow works", ok(u))
    record("description persisted", raw(config, auth, wid, "description") == "updated by e2e")

    # NB: the legacy wf_workflow `active` flag is governed by whether a version is
    # published, so activate/deactivate are asserted to run (not field effects).
    print("5) activate_workflow")
    a = activate_workflow(config, auth, {"workflow_id": wid})
    record("activate_workflow works", ok(a), a.get("error", ""))

    print("6) deactivate_workflow")
    d = deactivate_workflow(config, auth, {"workflow_id": wid})
    record("deactivate_workflow works", ok(d), d.get("error", ""))

    print("7) list_workflow_versions")
    lv = list_workflow_versions(config, auth, {"workflow_id": wid})
    record("list_workflow_versions works", ok(lv))

    print("8) get_workflow_activities")
    ga = get_workflow_activities(config, auth, {"workflow_id": wid})
    # A version-less workflow correctly reports "no published versions" — that is
    # the right answer for the legacy engine, not a tool failure.
    record("get_workflow_activities responds correctly",
           ok(ga) or "No published versions" in ga.get("error", ""),
           ga.get("error") or f"{ga.get('count', 0)} activities")

    print("9) delete_workflow")
    if not args.keep:
        dw = delete_workflow(config, auth, {"workflow_id": wid})
        record("delete_workflow works", ok(dw), dw.get("message", ""))
        gone = requests.get(f"{config.api_url}/table/wf_workflow/{wid}", headers=auth.get_headers())
        record("workflow gone (404)", gone.status_code == 404)
    else:
        print(f"\n{DIM}--keep: left workflow {wid}{RST}")

    passed, total = sum(results), len(results)
    print(f"\n{(GREEN if passed == total else RED)}==== {passed}/{total} checks passed ===={RST}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
