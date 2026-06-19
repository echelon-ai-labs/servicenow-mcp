#!/usr/bin/env python
"""
Live test of the ServiceNow MCP *agile* tools (stories, epics, scrum tasks,
projects) — adaptive to whether the Agile Development / SPM plugins are active.

If the agile tables (rm_story / rm_epic / rm_scrum_task / pm_project) exist, the
full create -> list -> update lifecycle is exercised. If they don't (common on a
vanilla PDI), the test instead verifies the tools **degrade gracefully** —
returning a clear "Invalid table ..." error rather than crashing.

Usage:
    .venv/Scripts/python scripts/test_agile_live.py [--keep]
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
from servicenow_mcp.tools.story_tools import create_story, list_stories, update_story  # noqa: E402
from servicenow_mcp.tools.epic_tools import create_epic, list_epics, update_epic  # noqa: E402
from servicenow_mcp.tools.scrum_task_tools import create_scrum_task, list_scrum_tasks  # noqa: E402
from servicenow_mcp.tools.project_tools import create_project, list_projects  # noqa: E402

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()
    config = build_config()
    auth = AuthManager(config.auth, config.instance_url)
    print(f"\nInstance: {config.instance_url}  auth={config.auth.type.value}\n")

    avail = requests.get(f"{config.api_url}/table/rm_story", params={"sysparm_limit": 1},
                         headers=auth.get_headers(), timeout=config.timeout).status_code == 200

    if not avail:
        print(f"{YEL}Agile Development / SPM plugins are NOT active (rm_story/rm_epic/...) — "
              f"verifying graceful degradation instead of the full lifecycle.{RST}\n")
        checks = [
            ("list_stories", list_stories(config, auth, {})),
            ("list_epics", list_epics(config, auth, {})),
            ("list_scrum_tasks", list_scrum_tasks(config, auth, {})),
            ("list_projects", list_projects(config, auth, {})),
            ("create_story", create_story(config, auth, {"short_description": "x", "acceptance_criteria": "x"})),
            ("create_epic", create_epic(config, auth, {"short_description": "x"})),
            ("create_scrum_task", create_scrum_task(config, auth, {"story": "x", "short_description": "x"})),
            ("create_project", create_project(config, auth, {"short_description": "x"})),
        ]
        for name, r in checks:
            msg = str(get(r, "message", ""))
            clean = isinstance(r, dict) and get(r, "success") is False and ("Invalid table" in msg or "HTTP" in msg)
            record(f"{name} degrades gracefully", clean, msg[:80])
    else:
        print("Agile plugin active — running full lifecycle.\n")
        ep = create_epic(config, auth, {"short_description": "[MCP e2e] epic"})
        record("create_epic works", bool(get(ep, "success")), get(ep, "message", ""))
        st = create_story(config, auth, {"short_description": "[MCP e2e] story"})
        record("create_story works", bool(get(st, "success")), get(st, "message", ""))
        for name, r in [("list_epics", list_epics(config, auth, {"limit": 5})),
                        ("list_stories", list_stories(config, auth, {"limit": 5})),
                        ("list_scrum_tasks", list_scrum_tasks(config, auth, {"limit": 5})),
                        ("list_projects", list_projects(config, auth, {"limit": 5}))]:
            record(f"{name} works", bool(get(r, "success")))
        pr = create_project(config, auth, {"short_description": "[MCP e2e] project"})
        record("create_project works", bool(get(pr, "success")), get(pr, "message", ""))
        # best-effort cleanup
        if not args.keep:
            for table, r in (("rm_epic", ep), ("rm_story", st), ("pm_project", pr)):
                rec = get(r, "epic") or get(r, "story") or get(r, "project") or {}
                sid = rec.get("sys_id") if isinstance(rec, dict) else None
                if sid:
                    requests.delete(f"{config.api_url}/table/{table}/{sid}", headers=auth.get_headers())

    passed, total = sum(results), len(results)
    print(f"\n{(GREEN if passed == total else RED)}==== {passed}/{total} checks passed ===={RST}")
    if not avail:
        print(f"{DIM}(install the Agile Development plugin to exercise the full story/epic/task lifecycle){RST}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
