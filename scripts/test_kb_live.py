#!/usr/bin/env python
"""
Live end-to-end test of the ServiceNow MCP *knowledge base* tools.

Drives the real tool functions against a live instance (creds from .env):

  create_knowledge_base -> list -> create_category -> list_categories ->
  create_article -> get (by sys_id and by number) -> list_articles ->
  update_article -> publish_article -> delete_article

NOTE: article *publishing* (workflow_state -> published) is governed by the
Knowledge state flow on most instances; publish_article re-fetches and reports
the actual resulting state honestly rather than assuming success.

Usage:
    .venv/Scripts/python scripts/test_kb_live.py [--keep]
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
from servicenow_mcp.tools.knowledge_base import (  # noqa: E402
    CreateArticleParams, CreateCategoryParams, CreateKnowledgeBaseParams, DeleteArticleParams,
    GetArticleParams, ListArticlesParams, ListCategoriesParams, ListKnowledgeBasesParams,
    PublishArticleParams, UpdateArticleParams,
    create_article, create_category, create_knowledge_base, delete_article, get_article,
    list_articles, list_categories, list_knowledge_bases, publish_article, update_article,
)

GREEN, RED, YEL, DIM, RST = "\033[92m", "\033[91m", "\033[93m", "\033[2m", "\033[0m"
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


def api(config, auth, method, path, **kw):
    return requests.request(method, f"{config.api_url}{path}", headers=auth.get_headers(), timeout=config.timeout, **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()
    config = build_config()
    auth = AuthManager(config.auth, config.instance_url)
    print(f"\nInstance: {config.instance_url}  auth={config.auth.type.value}\n")
    admin = api(config, auth, "GET", "/table/sys_user", params={"sysparm_query": "user_name=admin", "sysparm_fields": "sys_id"}).json()["result"][0]["sys_id"]

    # KBs can't be hard-deleted via the API and a "Duplicate Knowledge Base" rule
    # blocks same-titled KBs, so find-or-create: exercise create on a fresh
    # instance, reuse the existing KB on reruns.
    KB_TITLE = "[MCP e2e] KB"
    print("1) create_knowledge_base (find-or-create)")
    existing = api(config, auth, "GET", "/table/kb_knowledge_base",
                   params={"sysparm_query": f"title={KB_TITLE}", "sysparm_fields": "sys_id", "sysparm_limit": 1}).json()["result"]
    if existing:
        kbid = existing[0]["sys_id"]
        record("knowledge base available (reused existing)", True, f"reusing {kbid}")
    else:
        kb = create_knowledge_base(config, auth, CreateKnowledgeBaseParams(
            title=KB_TITLE, description="temp e2e KB", owner=admin, managers=admin))
        record("create_knowledge_base success", kb.success, kb.message)
        if not kb.success:
            sys.exit(f"{RED}stop{RST}")
        kbid = kb.kb_id
    print(f"         {DIM}KB {kbid}{RST}")

    # Cleanup-first: remove leftover test articles/categories from any interrupted
    # prior run (these ARE deletable; the KB is not, hence reuse above). Avoids the
    # "Duplicate Knowledge Category"/article rules.
    for table, field in (("kb_knowledge", "short_description"), ("kb_category", "label")):
        for row in api(config, auth, "GET", f"/table/{table}",
                       params={"sysparm_query": f"{field}LIKE[MCP e2e]", "sysparm_fields": "sys_id", "sysparm_limit": 50}).json().get("result", []):
            api(config, auth, "DELETE", f"/table/{table}/{row['sys_id']}")

    print("2) list_knowledge_bases")
    lkb = list_knowledge_bases(config, auth, ListKnowledgeBasesParams(limit=100))
    record("list includes our KB", lkb.get("success") and any(k.get("id") == kbid or k.get("sys_id") == kbid for k in lkb.get("knowledge_bases", [])))

    print("3) create_category")
    cat = create_category(config, auth, CreateCategoryParams(title="[MCP e2e] Cat", knowledge_base=kbid))
    record("create_category success", cat.success, cat.message)
    catid = cat.category_id

    print("4) list_categories (by KB)")
    lc = list_categories(config, auth, ListCategoriesParams(knowledge_base=kbid, limit=50))
    record("list_categories includes it", lc.get("success") and any(c.get("id") == catid for c in lc.get("categories", [])))

    print("5) create_article")
    art = create_article(config, auth, CreateArticleParams(
        title="[MCP e2e] How to reset VPN", text="<p>Steps...</p>",
        short_description="[MCP e2e] How to reset VPN", knowledge_base=kbid, category=catid))
    record("create_article success", art.success, art.message)
    aid = art.article_id
    number = api(config, auth, "GET", f"/table/kb_knowledge/{aid}", params={"sysparm_fields": "number"}).json()["result"]["number"]
    print(f"         {DIM}article {number} ({aid}) state={art.workflow_state}{RST}")

    print("6) get_article (by sys_id, then by NUMBER -> resolution)")
    g1 = get_article(config, auth, GetArticleParams(article_id=aid))
    record("get_article by sys_id", g1.get("success") and g1["article"]["id"] == aid)
    g2 = get_article(config, auth, GetArticleParams(article_id=number))
    record("get_article by number", g2.get("success") and g2["article"]["id"] == aid)

    print("7) list_articles (by KB)")
    la = list_articles(config, auth, ListArticlesParams(knowledge_base=kbid, limit=50))
    record("list_articles includes it", la.get("success") and any(a.get("id") == aid for a in la.get("articles", [])))

    print("8) update_article (by number)")
    u = update_article(config, auth, UpdateArticleParams(article_id=number, short_description="[MCP e2e] VPN reset (updated)"))
    record("update returns success", u.success, u.message)
    after = api(config, auth, "GET", f"/table/kb_knowledge/{aid}", params={"sysparm_fields": "short_description"}).json()["result"]["short_description"]
    record("short_description changed", after == "[MCP e2e] VPN reset (updated)", f"now: {after!r}")

    print("9) publish_article (by number)")
    p = publish_article(config, auth, PublishArticleParams(article_id=number))
    # On a governed instance this stays 'draft'; the tool reports the actual state honestly.
    record("publish_article reports a real workflow_state", p.workflow_state in ("draft", "review", "published"),
           f"workflow_state={p.workflow_state!r} (achieved={p.success})")
    if p.success:
        print(f"         {GREEN}article actually published{RST}")
    else:
        print(f"         {YEL}publishing governed by Knowledge state flow — left at {p.workflow_state!r} (expected on this PDI){RST}")

    print("10) delete_article (by number)")
    if not args.keep:
        d = delete_article(config, auth, DeleteArticleParams(article_id=number))
        record("delete_article success", d.success, d.message)
        gone = api(config, auth, "GET", f"/table/kb_knowledge/{aid}")
        record("article gone (404)", gone.status_code == 404)
        # Clean up the category (deletable). The KB is intentionally left in place
        # and reused — kb_knowledge_base records can't be deleted via the Table API.
        if catid:
            api(config, auth, "DELETE", f"/table/kb_category/{catid}")
        print(f"{DIM}cleanup: removed category (KB reused across runs){RST}")
    else:
        print(f"\n{DIM}--keep: left KB {kbid}, category {catid}, article {number}{RST}")

    passed, total = sum(results), len(results)
    print(f"\n{(GREEN if passed == total else RED)}==== {passed}/{total} checks passed ===={RST}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
