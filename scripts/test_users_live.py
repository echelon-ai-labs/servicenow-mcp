#!/usr/bin/env python
"""
Live end-to-end test of the ServiceNow MCP *user & group* tools.

Drives the real tool functions against a live instance (creds from .env) and
re-fetches each record to confirm changes persisted:

  user:  create -> get -> list -> update (all fields incl. locked_out /
         password_needs_reset) -> set_password -> unlock -> delete
  group: create -> add member -> remove member -> update -> delete

Usage:
    .venv/Scripts/python scripts/test_users_live.py [--keep]
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
from servicenow_mcp.tools.user_tools import (  # noqa: E402
    AddGroupMembersParams, CreateGroupParams, CreateUserParams, DeleteGroupParams,
    DeleteUserParams, GetUserParams, ListUsersParams, RemoveGroupMembersParams,
    SetPasswordParams, UpdateGroupParams, UpdateUserParams,
    add_group_members, create_group, create_user, delete_group, delete_user,
    get_user, list_users, remove_group_members, set_password, update_group, update_user,
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


def raw(config, auth, table, sys_id, field):
    r = requests.get(f"{config.api_url}/table/{table}/{sys_id}",
                     params={"sysparm_fields": field}, headers=auth.get_headers(), timeout=config.timeout)
    r.raise_for_status()
    return r.json().get("result", {}).get(field)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()
    config = build_config()
    auth = AuthManager(config.auth, config.instance_url)
    print(f"\nInstance: {config.instance_url}  auth={config.auth.type.value}\n")
    uname = "mcp.e2e.user"

    # ---- USER ----------------------------------------------------------------
    print("1) create_user")
    c = create_user(config, auth, CreateUserParams(
        user_name=uname, first_name="MCP", last_name="E2E", email="mcp.e2e@example.com",
        title="QA Engineer", phone="555-0100", mobile_phone="555-0101", active=True))
    record("create returns success", c.success, c.message)
    if not c.success:
        sys.exit(f"{RED}stop: create failed{RST}")
    uid = c.user_id
    print(f"         {DIM}created {uname} ({uid}){RST}")

    print("2) get_user (by username)")
    g = get_user(config, auth, GetUserParams(user_name=uname))
    record("get_user finds it", g.get("success") and g["user"]["sys_id"] == uid)

    print("3) list_users (query)")
    lst = list_users(config, auth, ListUsersParams(query="mcp.e2e", limit=10))
    record("list_users includes it", lst.get("success") and any(u.get("sys_id") == uid for u in lst.get("users", [])))

    print("4) update_user by username (title, department, locked_out, password_needs_reset)")
    u = update_user(config, auth, UpdateUserParams(
        user_id=uname, title="Senior QA", locked_out=True, password_needs_reset=True))
    record("update returns success", u.success, u.message)
    record("title changed", raw(config, auth, "sys_user", uid, "title") == "Senior QA")
    record("locked_out = true", raw(config, auth, "sys_user", uid, "locked_out") == "true")
    record("password_needs_reset = true", raw(config, auth, "sys_user", uid, "password_needs_reset") == "true")

    print("5) set_password (require_reset=True)")
    sp = set_password(config, auth, SetPasswordParams(user_id=uname, password="Chang3#Me!2026", require_reset=True))
    record("set_password returns success", sp.success, sp.message)
    record("password_needs_reset still true", raw(config, auth, "sys_user", uid, "password_needs_reset") == "true")

    print("6) update_user: unlock (locked_out=False)")
    update_user(config, auth, UpdateUserParams(user_id=uid, locked_out=False))
    record("locked_out = false", raw(config, auth, "sys_user", uid, "locked_out") == "false")

    # ---- GROUP ---------------------------------------------------------------
    print("7) create_group + add/remove member")
    gname = "MCP E2E Group"
    cg = create_group(config, auth, CreateGroupParams(name=gname, description="temp e2e group"))
    record("create_group returns success", cg.success, cg.message)
    gid = cg.group_id
    am = add_group_members(config, auth, AddGroupMembersParams(group_id=gid, members=[uname]))
    record("add_group_members success", am.success, am.message)
    rm = remove_group_members(config, auth, RemoveGroupMembersParams(group_id=gid, members=[uname]))
    record("remove_group_members success", rm.success, rm.message)

    print("8) update_group")
    ug = update_group(config, auth, UpdateGroupParams(group_id=gid, description="updated e2e group"))
    record("update_group success", ug.success, ug.message)
    record("group description updated", raw(config, auth, "sys_user_group", gid, "description") == "updated e2e group")

    # ---- DELETE --------------------------------------------------------------
    if not args.keep:
        print("9) delete_user + delete_group (by name)")
        du = delete_user(config, auth, DeleteUserParams(user_id=uname))
        record("delete_user success", du.success, du.message)
        record("user gone", not get_user(config, auth, GetUserParams(user_name=uname)).get("success"))
        dg = delete_group(config, auth, DeleteGroupParams(group_id=gname))
        record("delete_group (by name) success", dg.success, dg.message)
    else:
        print(f"\n{DIM}--keep: left user {uname} and group {gname}{RST}")

    passed, total = sum(results), len(results)
    print(f"\n{(GREEN if passed == total else RED)}==== {passed}/{total} checks passed ===={RST}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
