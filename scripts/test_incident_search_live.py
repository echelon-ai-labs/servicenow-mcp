#!/usr/bin/env python
"""
Live test of incident date / last-response search via list_incidents:
creation date, between two dates, and last-updated (last response) filters,
plus a combined free-text + date query (verifies correct ^OR grouping).

Usage:
    .venv/Scripts/python scripts/test_incident_search_live.py [--keep]
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from servicenow_mcp.auth.auth_manager import AuthManager  # noqa: E402
from servicenow_mcp.utils.config import (  # noqa: E402
    ApiKeyConfig, AuthConfig, AuthType, BasicAuthConfig, OAuthConfig, ServerConfig,
)
from servicenow_mcp.tools.incident_tools import (  # noqa: E402
    AddCommentParams, CreateIncidentParams, DeleteIncidentParams, ListIncidentsParams,
    add_comment, create_incident, delete_incident, list_incidents,
)

GREEN, RED, DIM, RST = "\033[92m", "\033[91m", "\033[2m", "\033[0m"
results = []


def record(name, ok, detail=""):
    print(f"  [{GREEN+'PASS'+RST if ok else RED+'FAIL'+RST}] {name}")
    if detail:
        print(f"         {DIM}{detail}{RST}")
    results.append(bool(ok))


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


def has(result, number):
    return result.get("success") and any(i.get("number") == number for i in result.get("incidents", []))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()
    config = build_config()
    auth = AuthManager(config.auth, config.instance_url)
    print(f"\nInstance: {config.instance_url}  auth={config.auth.type.value}\n")

    today = datetime.now()
    yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    next_year = (today + timedelta(days=365)).strftime("%Y-%m-%d")
    uniq = "MCPdatesearch" + today.strftime("%H%M%S")

    print("0) create test incident (urgency=1, impact=1 -> priority=1)")
    c = create_incident(config, auth, CreateIncidentParams(
        short_description=f"[{uniq}] date search test", urgency="1", impact="1"))
    record("create returns success", c.success, c.message)
    if not c.success:
        sys.exit(f"{RED}stop{RST}")
    num, sid = c.incident_number, c.incident_id
    # severity isn't a create param; set it directly so we can exercise the filter
    requests.patch(f"{config.api_url}/table/incident/{sid}", json={"severity": "1"},
                   headers=auth.get_headers(), timeout=config.timeout)
    print(f"         {DIM}created {num}{RST}")

    print("1) created_after (>= yesterday) -> includes new incident")
    record("found via created_after", has(list_incidents(config, auth,
           ListIncidentsParams(created_after=yesterday, limit=100)), num))

    print("2) created_before (<= 2000-01-01) -> excludes new incident")
    record("excluded by created_before", not has(list_incidents(config, auth,
           ListIncidentsParams(created_before="2000-01-01", limit=100)), num))

    print("3) BETWEEN two dates (2000-01-01 .. tomorrow) -> includes")
    record("found in date range", has(list_incidents(config, auth,
           ListIncidentsParams(created_after="2000-01-01", created_before=tomorrow, limit=100)), num))

    print("4) created_after (future) -> excludes")
    record("excluded by future created_after", not has(list_incidents(config, auth,
           ListIncidentsParams(created_after=next_year, limit=100)), num))

    print("5) last response: add_comment then updated_after (>= yesterday) -> includes")
    add_comment(config, auth, AddCommentParams(incident_id=num, comment="response from test"))
    record("found via updated_after", has(list_incidents(config, auth,
           ListIncidentsParams(updated_after=yesterday, limit=100)), num))
    record("excluded by updated_before 2000-01-01", not has(list_incidents(config, auth,
           ListIncidentsParams(updated_before="2000-01-01", limit=100)), num))

    print("6) field filters: urgency / severity / impact / priority")
    record("found via urgency=1", has(list_incidents(config, auth, ListIncidentsParams(urgency="1", limit=100)), num))
    record("excluded by urgency=3", not has(list_incidents(config, auth, ListIncidentsParams(urgency="3", limit=100)), num))
    record("found via severity=1", has(list_incidents(config, auth, ListIncidentsParams(severity="1", limit=100)), num))
    record("found via impact=1", has(list_incidents(config, auth, ListIncidentsParams(impact="1", limit=100)), num))
    record("found via priority=1", has(list_incidents(config, auth, ListIncidentsParams(priority="1", limit=100)), num))

    print("7) keyword search via query")
    record("found via keyword query", has(list_incidents(config, auth, ListIncidentsParams(query=uniq, limit=100)), num))

    print("8) combined free-text query + created_after (verifies ^OR grouping)")
    record("found via text + date", has(list_incidents(config, auth,
           ListIncidentsParams(query=uniq, created_after=yesterday, limit=100)), num))
    record("text + future date excludes", not has(list_incidents(config, auth,
           ListIncidentsParams(query=uniq, created_after=next_year, limit=100)), num))

    if not args.keep:
        delete_incident(config, auth, DeleteIncidentParams(incident_id=num))
        print(f"\n{DIM}cleanup: deleted {num}{RST}")
    else:
        print(f"\n{DIM}--keep: left {num}{RST}")

    passed, total = sum(results), len(results)
    print(f"\n{(GREEN if passed == total else RED)}==== {passed}/{total} checks passed ===={RST}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
