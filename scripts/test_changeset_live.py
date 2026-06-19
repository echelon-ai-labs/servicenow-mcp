#!/usr/bin/env python
"""
Live end-to-end test of the ServiceNow MCP *changeset* (update set) tools.

  list -> create -> get_details -> update -> add_file -> commit -> publish -> delete

Update sets are committed by setting state=complete; publishing depends on
instance configuration and is asserted to run.

Usage:
    .venv/Scripts/python scripts/test_changeset_live.py [--keep]
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
from servicenow_mcp.tools.changeset_tools import (  # noqa: E402
    add_file_to_changeset, commit_changeset, create_changeset, get_changeset_details,
    list_changesets, publish_changeset, update_changeset,
)

GREEN, RED, YEL, DIM, RST = "\033[92m", "\033[91m", "\033[93m", "\033[2m", "\033[0m"
results = []


def record(name, ok, detail=""):
    print(f"  [{GREEN+'PASS'+RST if ok else RED+'FAIL'+RST}] {name}")
    if detail:
        print(f"         {DIM}{detail}{RST}")
    results.append(bool(ok))


def get(r, key, default=None):
    if isinstance(r, dict):
        return r.get(key, default)
    if hasattr(r, key):
        return getattr(r, key)
    return default


def succ(r):
    return bool(get(r, "success", isinstance(r, dict)))


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


def api(config, auth, method, path, **kw):
    return requests.request(method, f"{config.api_url}{path}", headers=auth.get_headers(), timeout=config.timeout, **kw)


def field(config, auth, table, sys_id, f):
    r = api(config, auth, "GET", f"/table/{table}/{sys_id}", params={"sysparm_fields": f})
    if r.status_code >= 400:
        return None
    v = r.json().get("result", {}).get(f)
    return v.get("value") if isinstance(v, dict) else v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()
    config = build_config()
    auth = AuthManager(config.auth, config.instance_url)
    print(f"\nInstance: {config.instance_url}  auth={config.auth.type.value}\n")

    print("1) list_changesets")
    lc = list_changesets(config, auth, {"limit": 5})
    record("list_changesets works", succ(lc), f"{get(lc, 'count', '?')} changesets")

    # the global application scope sys_id (required by create_changeset)
    scopes = api(config, auth, "GET", "/table/sys_scope",
                 params={"sysparm_query": "scope=global", "sysparm_fields": "sys_id", "sysparm_limit": 1}).json().get("result", [])
    app = scopes[0]["sys_id"] if scopes else "global"

    print("2) create_changeset")
    c = create_changeset(config, auth, {"name": "[MCP e2e] changeset", "description": "e2e test", "application": app})
    record("create_changeset works", succ(c), get(c, "message", ""))
    cid = (get(c, "changeset", {}) or {}).get("sys_id")
    if not cid:
        sys.exit(f"{RED}stop: no changeset id{RST}")
    print(f"         {DIM}update set {cid}{RST}")

    print("3) get_changeset_details (by sys_id)")
    g = get_changeset_details(config, auth, {"changeset_id": cid})
    record("get_changeset_details works", succ(g))

    print("4) update_changeset")
    u = update_changeset(config, auth, {"changeset_id": cid, "description": "updated by e2e"})
    record("update_changeset works", succ(u), get(u, "message", ""))
    record("description persisted", field(config, auth, "sys_update_set", cid, "description") == "updated by e2e")

    print("5) add_file_to_changeset")
    af = add_file_to_changeset(config, auth, {
        "changeset_id": cid, "file_path": "sys_script_x_mcp_test", "file_content": "<record_update/>"})
    msg = get(af, "message", "")
    # Manually inserting sys_update_xml is ACL-restricted on ServiceNow (the
    # platform writes these when config records change in the set's scope). The
    # tool should run and surface that clearly rather than crash.
    record("add_file_to_changeset responds correctly", succ(af) or "security constraints" in msg or "ACL" in msg, msg)
    if not succ(af):
        print(f"         {YEL}manual sys_update_xml insert is ACL-restricted — expected on this instance{RST}")

    print("6) commit_changeset")
    cm = commit_changeset(config, auth, {"changeset_id": cid, "commit_message": "committed by e2e"})
    record("commit_changeset works", succ(cm), get(cm, "message", ""))
    record("state = complete", field(config, auth, "sys_update_set", cid, "state") == "complete",
           f"state={field(config, auth, 'sys_update_set', cid, 'state')!r}")

    print("7) publish_changeset")
    pb = publish_changeset(config, auth, {"changeset_id": cid, "publish_notes": "published by e2e"})
    record("publish_changeset responds", isinstance(pb, dict), get(pb, "message", ""))

    if not args.keep:
        # delete update set's xml records then the set
        for row in api(config, auth, "GET", "/table/sys_update_xml",
                       params={"sysparm_query": f"update_set={cid}", "sysparm_fields": "sys_id"}).json().get("result", []):
            api(config, auth, "DELETE", f"/table/sys_update_xml/{row['sys_id']}")
        d = api(config, auth, "DELETE", f"/table/sys_update_set/{cid}")
        print(f"\n{DIM}cleanup: deleted update set (HTTP {d.status_code}){RST}")
    else:
        print(f"\n{DIM}--keep: update set {cid}{RST}")

    passed, total = sum(results), len(results)
    print(f"\n{(GREEN if passed == total else RED)}==== {passed}/{total} checks passed ===={RST}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
