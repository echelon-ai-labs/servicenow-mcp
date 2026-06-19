#!/usr/bin/env python
"""
Live end-to-end test of the ServiceNow MCP *catalog* tools
(catalog_tools + catalog_variables + catalog_optimization).

  list_catalog_items -> get_catalog_item -> list_catalog_categories ->
  create_catalog_category -> update_catalog_category -> update_catalog_item ->
  move_catalog_items -> create/list/update_catalog_item_variable ->
  get_optimization_recommendations

A throwaway catalog item is created via the API (there is no create_catalog_item
tool) so variables/move/update can be exercised without touching real items.

Usage:
    .venv/Scripts/python scripts/test_catalog_live.py [--keep]
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
from servicenow_mcp.tools.catalog_tools import (  # noqa: E402
    CreateCatalogCategoryParams, GetCatalogItemParams, ListCatalogCategoriesParams,
    ListCatalogItemsParams, MoveCatalogItemsParams, UpdateCatalogCategoryParams,
    create_catalog_category, get_catalog_item, list_catalog_categories,
    list_catalog_items, move_catalog_items, update_catalog_category,
)
from servicenow_mcp.tools.catalog_variables import (  # noqa: E402
    CreateCatalogItemVariableParams, ListCatalogItemVariablesParams, UpdateCatalogItemVariableParams,
    create_catalog_item_variable, list_catalog_item_variables, update_catalog_item_variable,
)
from servicenow_mcp.tools.catalog_optimization import (  # noqa: E402
    OptimizationRecommendationsParams, UpdateCatalogItemParams,
    get_optimization_recommendations, update_catalog_item,
)

GREEN, RED, YEL, DIM, RST = "\033[92m", "\033[91m", "\033[93m", "\033[2m", "\033[0m"
results = []


def record(name, ok, detail=""):
    print(f"  [{GREEN+'PASS'+RST if ok else RED+'FAIL'+RST}] {name}")
    if detail:
        print(f"         {DIM}{detail}{RST}")
    results.append(bool(ok))


def get(r, key, default=None):
    """Read a field from a dict response OR a Pydantic response object.

    Check dict first — dict method names (items/get/keys) would otherwise shadow
    real fields via hasattr/getattr.
    """
    if isinstance(r, dict):
        return r.get(key, default)
    if hasattr(r, key):
        return getattr(r, key)
    return default


def succ(r):
    s = get(r, "success", None)
    return bool(s) if s is not None else isinstance(r, dict)


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
    return v.get("value") if isinstance(v, dict) else v  # unwrap reference {link, value}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()
    config = build_config()
    auth = AuthManager(config.auth, config.instance_url)
    print(f"\nInstance: {config.instance_url}  auth={config.auth.type.value}\n")
    item_id = cat_id = var_id = None

    print("1) list_catalog_items")
    li = list_catalog_items(config, auth, ListCatalogItemsParams(limit=5))
    items = get(li, "items", []) or get(li, "result", []) or []
    record("list_catalog_items works", succ(li) and len(items) > 0)
    sample = items[0].get("sys_id") if items and isinstance(items[0], dict) else None

    print("2) get_catalog_item")
    g = get_catalog_item(config, auth, GetCatalogItemParams(item_id=sample)) if sample else None
    record("get_catalog_item works", g is not None and succ(g), get(g or {}, "message", ""))

    print("3) list_catalog_categories")
    lc = list_catalog_categories(config, auth, ListCatalogCategoriesParams(limit=5))
    record("list_catalog_categories works", succ(lc))

    print("4) create_catalog_category")
    cc = create_catalog_category(config, auth, CreateCatalogCategoryParams(title="[MCP e2e] Catalog Cat", description="temp"))
    record("create_catalog_category works", succ(cc), get(cc, "message", ""))
    data = get(cc, "data", {})
    cat_id = data.get("sys_id") if isinstance(data, dict) else None

    print("5) update_catalog_category")
    if cat_id:
        uc = update_catalog_category(config, auth, UpdateCatalogCategoryParams(category_id=cat_id, description="updated desc"))
        record("update_catalog_category works", succ(uc), get(uc, "message", ""))
        record("category description persisted", field(config, auth, "sc_category", cat_id, "description") == "updated desc")
    else:
        record("update_catalog_category works", False, "no category")

    # throwaway catalog item (no create_catalog_item tool)
    created = api(config, auth, "POST", "/table/sc_cat_item",
                  json={"name": "[MCP e2e] item", "short_description": "temp e2e item", "active": "true"})
    item_id = created.json()["result"]["sys_id"] if created.status_code < 300 else None
    print(f"         {DIM}test item {item_id}{RST}")

    print("6) update_catalog_item")
    ui = update_catalog_item(config, auth, UpdateCatalogItemParams(item_id=item_id, description="updated by e2e", price="9.99"))
    record("update_catalog_item works", succ(ui), get(ui, "message", ""))
    record("price persisted", str(field(config, auth, "sc_cat_item", item_id, "price")).startswith("9.9"),
           f"price={field(config, auth, 'sc_cat_item', item_id, 'price')!r}")

    print("7) move_catalog_items")
    mv = move_catalog_items(config, auth, MoveCatalogItemsParams(item_ids=[item_id], target_category_id=cat_id))
    record("move_catalog_items works", succ(mv), get(mv, "message", ""))
    record("item category moved", field(config, auth, "sc_cat_item", item_id, "category") == cat_id,
           f"category={field(config, auth, 'sc_cat_item', item_id, 'category')!r}")

    print("8) create_catalog_item_variable")
    cv = create_catalog_item_variable(config, auth, CreateCatalogItemVariableParams(
        catalog_item_id=item_id, name="mcp_test_var", type="6", label="MCP Test Var"))
    record("create_catalog_item_variable works", succ(cv), get(cv, "message", ""))
    var_id = get(cv, "variable_id", None)

    print("9) list_catalog_item_variables")
    lv = list_catalog_item_variables(config, auth, ListCatalogItemVariablesParams(catalog_item_id=item_id))
    variables = get(lv, "variables", []) or []
    record("list_catalog_item_variables includes it", succ(lv) and any(
        (vv.get("sys_id") == var_id) for vv in variables if isinstance(vv, dict)), f"{get(lv, 'count', len(variables))} vars")

    print("10) update_catalog_item_variable")
    uv = update_catalog_item_variable(config, auth, UpdateCatalogItemVariableParams(variable_id=var_id, label="MCP Test Var Updated"))
    record("update_catalog_item_variable works", succ(uv), get(uv, "message", ""))
    record("variable label persisted", field(config, auth, "item_option_new", var_id, "question_text") == "MCP Test Var Updated")

    print("11) get_optimization_recommendations")
    opt = get_optimization_recommendations(config, auth, OptimizationRecommendationsParams(
        recommendation_types=["high_abandonment", "low_usage"]))
    record("get_optimization_recommendations works", succ(opt), get(opt, "message", ""))

    if not args.keep:
        for table, sid in (("item_option_new", var_id), ("sc_cat_item", item_id), ("sc_category", cat_id)):
            if sid:
                api(config, auth, "DELETE", f"/table/{table}/{sid}")
        print(f"\n{DIM}cleanup: removed test variable, item, category{RST}")
    else:
        print(f"\n{DIM}--keep: item={item_id} category={cat_id} var={var_id}{RST}")

    passed, total = sum(results), len(results)
    print(f"\n{(GREEN if passed == total else RED)}==== {passed}/{total} checks passed ===={RST}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
