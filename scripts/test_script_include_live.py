#!/usr/bin/env python
"""
Live end-to-end test of the ServiceNow MCP *script include* tools.

  list -> create -> get -> update -> delete

Usage:
    .venv/Scripts/python scripts/test_script_include_live.py [--keep]
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
from servicenow_mcp.tools.script_include_tools import (  # noqa: E402
    CreateScriptIncludeParams, DeleteScriptIncludeParams, GetScriptIncludeParams,
    ListScriptIncludesParams, UpdateScriptIncludeParams,
    create_script_include, delete_script_include, get_script_include,
    list_script_includes, update_script_include,
)

GREEN, RED, DIM, RST = "\033[92m", "\033[91m", "\033[2m", "\033[0m"
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()
    config = build_config()
    auth = AuthManager(config.auth, config.instance_url)
    print(f"\nInstance: {config.instance_url}  auth={config.auth.type.value}\n")
    name = "MCPe2eTestScriptInclude"

    # cleanup-first
    for row in api(config, auth, "GET", "/table/sys_script_include",
                   params={"sysparm_query": f"name={name}", "sysparm_fields": "sys_id"}).json().get("result", []):
        api(config, auth, "DELETE", f"/table/sys_script_include/{row['sys_id']}")

    print("1) list_script_includes")
    li = list_script_includes(config, auth, ListScriptIncludesParams(limit=5))
    record("list_script_includes works", succ(li), f"{get(li, 'count', '?')} script includes")

    print("2) create_script_include")
    script = f"var {name} = Class.create();\n{name}.prototype = {{\n    initialize: function() {{}},\n    type: '{name}'\n}};"
    c = create_script_include(config, auth, CreateScriptIncludeParams(
        name=name, script=script, description="e2e test", client_callable=False, active=True, access="public"))
    record("create_script_include works", succ(c), get(c, "message", ""))
    sid = get(c, "script_include_id", None)
    print(f"         {DIM}script include {sid}{RST}")
    if not sid:
        sys.exit(f"{RED}stop{RST}")

    print("3) get_script_include")
    g = get_script_include(config, auth, GetScriptIncludeParams(script_include_id=sid))
    record("get_script_include works", succ(g) or get(g, "script_include") is not None, get(g, "message", ""))

    print("4) update_script_include")
    u = update_script_include(config, auth, UpdateScriptIncludeParams(script_include_id=sid, description="updated by e2e"))
    record("update_script_include works", succ(u), get(u, "message", ""))
    desc = api(config, auth, "GET", f"/table/sys_script_include/{sid}", params={"sysparm_fields": "description"}).json()["result"]["description"]
    record("description persisted", desc == "updated by e2e", f"desc={desc!r}")

    print("5) delete_script_include")
    if not args.keep:
        d = delete_script_include(config, auth, DeleteScriptIncludeParams(script_include_id=sid))
        record("delete_script_include works", succ(d), get(d, "message", ""))
        gone = api(config, auth, "GET", f"/table/sys_script_include/{sid}")
        record("script include gone (404)", gone.status_code == 404)
    else:
        print(f"\n{DIM}--keep: script include {sid}{RST}")

    passed, total = sum(results), len(results)
    print(f"\n{(GREEN if passed == total else RED)}==== {passed}/{total} checks passed ===={RST}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
