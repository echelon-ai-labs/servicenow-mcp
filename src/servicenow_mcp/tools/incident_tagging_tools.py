"""Tools for semantic incident tagging using ServiceNow markers."""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from collections import Counter
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import ServerConfig

logger = logging.getLogger(__name__)
_UNSUPPORTED_TABLES: set[str] = set()


class SuggestIncidentTagsParams(BaseModel):
    """Parameters to suggest tags for incidents without writing markers."""

    incident_numbers: List[str] = Field(
        ..., description="List of incident numbers (e.g. INC123,INC456)"
    )
    include_attachments: bool = Field(
        True,
        description="If true, include attachment metadata and optional OCR text in analysis",
    )
    max_tags_per_incident: int = Field(4, ge=1, le=12)


class ClassifyAndTagIncidentsParams(BaseModel):
    """Parameters to classify incidents and write markers."""

    incident_numbers: List[str] = Field(
        ..., description="List of incident numbers (e.g. INC123,INC456)"
    )
    include_attachments: bool = Field(
        True,
        description="If true, include attachment metadata and optional OCR text in analysis",
    )
    max_tags_per_incident: int = Field(4, ge=1, le=12)
    add_audit_work_note: bool = Field(
        True,
        description="If true, append a work note summarizing which tags were applied",
    )


_PT_STOPWORDS = {
    "de",
    "da",
    "do",
    "das",
    "dos",
    "para",
    "com",
    "sem",
    "por",
    "que",
    "uma",
    "um",
    "em",
    "na",
    "no",
    "as",
    "os",
    "ao",
    "aos",
    "e",
    "ou",
    "o",
    "a",
    "se",
    "foi",
    "ser",
    "sao",
    "são",
    "esta",
    "está",
    "isso",
    "essa",
    "esse",
    "como",
    "mais",
    "menos",
    "sobre",
    "entre",
    "nos",
    "nas",
    "chamado",
    "chamados",
    "comentario",
    "comentarios",
    "anotacao",
    "anotacoes",
    "anotação",
    "anotações",
    "trabalho",
    "cliente",
    "grupo",
    "atribuicao",
    "atribuido",
    "visivel",
    "visível",
    "marcadores",
    "marcador",
    "auto-tagging",
    "aplicados",
    "automaticamente",
    "analise",
    "descricao",
    "descricao",
    "anexos",
    "com-base",
    "base",
    "tag",
    "tags",
}

_KEYWORD_TAG_MAP = {
    "acesso": "acesso-autenticacao",
    "login": "acesso-autenticacao",
    "senha": "acesso-autenticacao",
    "sso": "acesso-autenticacao",
    "mfa": "acesso-autenticacao",
    "oauth": "acesso-autenticacao",
    "fraude": "fraude-risco",
    "antifraude": "fraude-risco",
    "anti": "fraude-risco",
    "anticorrupcao": "fraude-risco",
    "corrupcao": "fraude-risco",
    "erro": "falha-aplicacao",
    "falha": "falha-aplicacao",
    "bug": "falha-aplicacao",
    "exception": "falha-aplicacao",
    "stacktrace": "falha-aplicacao",
    "api": "api-integracao",
    "endpoint": "api-integracao",
    "timeout": "api-integracao",
    "latencia": "api-integracao",
    "latência": "api-integracao",
    "producao": "ambiente-producao",
    "produção": "ambiente-producao",
    "homolog": "ambiente-homologacao",
    "desempenho": "performance",
    "lento": "performance",
    "lentidao": "performance",
    "cpu": "performance",
    "memoria": "performance",
    "disco": "infraestrutura",
    "infra": "infraestrutura",
    "rede": "infraestrutura",
    "dns": "infraestrutura",
    "certificado": "certificados-ssl",
    "ssl": "certificados-ssl",
    "tls": "certificados-ssl",
    "dados": "dados-integridade",
    "duplicado": "dados-integridade",
    "inconsistente": "dados-integridade",
    "workflow": "fluxo-processo",
    "aprovação": "fluxo-processo",
    "aprovacao": "fluxo-processo",
    "javascript": "frontend-web",
    "pagina": "frontend-web",
    "web": "frontend-web",
    "imagem": "conteudo-imagem",
    "imagens": "conteudo-imagem",
}


def _slug(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-zA-Z0-9\s-]", " ", normalized.lower())
    cleaned = re.sub(r"\s+", "-", cleaned).strip("-")
    return re.sub(r"-+", "-", cleaned)


def _tokenize(text: str) -> List[str]:
    pieces = re.findall(r"[\w\-]{3,}", text.lower())
    return [p for p in pieces if p not in _PT_STOPWORDS and not p.isdigit()]


def _safe_json(response) -> Dict[str, Any]:
    try:
        return response.json()
    except ValueError:
        return {"result": []}


def _table_get(
    config: ServerConfig,
    auth_manager: AuthManager,
    table: str,
    params: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if table in _UNSUPPORTED_TABLES:
        return []
    url = f"{config.instance_url}/api/now/table/{table}"
    response = auth_manager.make_request("GET", url, params=params, timeout=config.timeout)
    if response.status_code != 200:
        if response.status_code in (400, 401, 403, 404):
            _UNSUPPORTED_TABLES.add(table)
        logger.warning("GET %s failed with HTTP %s", table, response.status_code)
        return []
    return _safe_json(response).get("result", [])


def _table_post(
    config: ServerConfig,
    auth_manager: AuthManager,
    table: str,
    payload: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    if table in _UNSUPPORTED_TABLES:
        return None
    url = f"{config.instance_url}/api/now/table/{table}"
    response = auth_manager.make_request("POST", url, json=payload, timeout=config.timeout)
    if response.status_code not in (200, 201):
        if response.status_code in (400, 401, 403, 404):
            _UNSUPPORTED_TABLES.add(table)
        logger.warning("POST %s failed with HTTP %s", table, response.status_code)
        return None
    return _safe_json(response).get("result", {})


def _table_patch(
    config: ServerConfig,
    auth_manager: AuthManager,
    table: str,
    sys_id: str,
    payload: Dict[str, Any],
) -> bool:
    url = f"{config.instance_url}/api/now/table/{table}/{sys_id}"
    response = auth_manager.make_request("PATCH", url, json=payload, timeout=config.timeout)
    return response.status_code in (200, 204)


def _get_incident_by_number(
    config: ServerConfig, auth_manager: AuthManager, incident_number: str
) -> Optional[Dict[str, Any]]:
    # 1) Resolve sys_id by incident number
    minimal = _table_get(
        config,
        auth_manager,
        "incident",
        {
            "sysparm_query": f"number={incident_number}",
            "sysparm_limit": 1,
            "sysparm_fields": "sys_id,number",
            "sysparm_display_value": "true",
            "sysparm_exclude_reference_link": "true",
        },
    )
    if not minimal:
        return None

    # 2) Fetch full record (all fields) to enrich analysis
    inc_sys_id = minimal[0].get("sys_id")
    full = _table_get(
        config,
        auth_manager,
        "incident",
        {
            "sysparm_query": f"sys_id={inc_sys_id}",
            "sysparm_limit": 1,
            "sysparm_display_value": "true",
            "sysparm_exclude_reference_link": "true",
        },
    )
    return full[0] if full else minimal[0]


def _extract_text_from_record(record: Dict[str, Any]) -> List[str]:
    chunks: List[str] = []
    for key, value in record.items():
        if value in (None, ""):
            continue

        if isinstance(value, dict):
            display = value.get("display_value")
            raw = value.get("value")
            if display:
                chunks.append(f"{key}: {display}")
            elif raw:
                chunks.append(f"{key}: {raw}")
            continue

        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    d = item.get("display_value") or item.get("value")
                    if d:
                        chunks.append(f"{key}: {d}")
                elif item:
                    chunks.append(f"{key}: {item}")
            continue

        chunks.append(f"{key}: {value}")

    return chunks


def _get_incident_journal(
    config: ServerConfig, auth_manager: AuthManager, incident_sys_id: str
) -> List[Dict[str, Any]]:
    return _table_get(
        config,
        auth_manager,
        "sys_journal_field",
        {
            "sysparm_query": (
                f"name=incident^element_id={incident_sys_id}^"
                "elementINcomments,work_notes^ORDERBYDESCsys_created_on"
            ),
            "sysparm_limit": 50,
            "sysparm_fields": "element,value,sys_created_on",
            "sysparm_display_value": "true",
        },
    )


def _get_incident_attachments(
    config: ServerConfig, auth_manager: AuthManager, incident_sys_id: str
) -> List[Dict[str, Any]]:
    return _table_get(
        config,
        auth_manager,
        "sys_attachment",
        {
            "sysparm_query": f"table_name=incident^table_sys_id={incident_sys_id}",
            "sysparm_limit": 20,
            "sysparm_fields": "sys_id,file_name,content_type,size_bytes,sys_created_on",
            "sysparm_display_value": "true",
        },
    )


def _try_extract_ocr_text(
    config: ServerConfig,
    auth_manager: AuthManager,
    attachment_sys_id: str,
    content_type: str,
) -> str:
    if not content_type.lower().startswith("image/"):
        return ""

    try:
        import io
        from PIL import Image
        import pytesseract
    except Exception:
        return ""

    url = f"{config.instance_url}/sys_attachment.do"
    response = auth_manager.make_request(
        "GET",
        url,
        params={"sys_id": attachment_sys_id},
        timeout=max(config.timeout, 60),
    )
    if response.status_code != 200:
        return ""

    try:
        image = Image.open(io.BytesIO(response.content))
        text = pytesseract.image_to_string(image, lang="por+eng")
        return text.strip()
    except Exception:
        return ""


def _build_context_text(
    incident: Dict[str, Any], journal: List[Dict[str, Any]], attachments: List[Dict[str, Any]]
) -> str:
    chunks: List[str] = _extract_text_from_record(incident)

    for entry in journal:
        value = entry.get("value")
        if value:
            text = str(value)
            if "[auto-tagging]" in text.lower():
                continue
            chunks.append(text)

    for att in attachments:
        name = att.get("file_name")
        ctype = att.get("content_type")
        if name:
            chunks.append(str(name))
        if ctype:
            chunks.append(str(ctype))
        ocr_text = att.get("ocr_text")
        if ocr_text:
            chunks.append(str(ocr_text))

    return "\n".join(chunks)


def _data_table_labels_request(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: Dict[str, Any],
):
    url = f"{config.instance_url}/data_table.do"
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "X-Transaction-Source": "Interface=Web,Interface-Type=Classic Environment,Interface-Name=Unified Navigation App",
    }
    return auth_manager.make_request(
        "GET",
        url,
        params=params,
        headers=headers,
        timeout=max(config.timeout, 20),
    )


def _add_label_via_data_table(
    config: ServerConfig,
    auth_manager: AuthManager,
    incident_sys_id: str,
    tag_name: str,
) -> bool:
    # Call equivalent to Classic UI:
    # data_table.do?sysparm_type=labels&...&sysparm_action=add
    response = _data_table_labels_request(
        config,
        auth_manager,
        {
            "sysparm_type": "labels",
            "sysparm_table": "incident",
            "sysparm_sys_id": incident_sys_id,
            "sysparm_label": tag_name,
            "sysparm_action": "add",
        },
    )
    if response.status_code != 200:
        return False

    body = (response.text or "").lower()
    # Usually success returns 200 and payload without the word "error"
    return "error" not in body


def _classify_text_to_tags(
    text: str, max_tags: int, exclude_tokens: Optional[set[str]] = None
) -> List[str]:
    tokens = _tokenize(text)
    if exclude_tokens:
        tokens = [t for t in tokens if t not in exclude_tokens]
    token_counter = Counter(tokens)

    tags: List[str] = []
    for token in tokens:
        mapped = _KEYWORD_TAG_MAP.get(token)
        if mapped and mapped not in tags:
            tags.append(mapped)

    top_terms = [t for t, c in token_counter.most_common(40) if c >= 2 and len(t) >= 4]
    for term in top_terms:
        if term in _KEYWORD_TAG_MAP:
            continue
        candidate = _slug(term)
        if candidate and candidate not in tags:
            tags.append(candidate)
        if len(tags) >= max_tags:
            break

    return tags[:max_tags]


def _get_current_user_exclude_tokens(
    config: ServerConfig, auth_manager: AuthManager
) -> set[str]:
    exclude = set()
    try:
        session_data = auth_manager._get_session_data()
        user_id = session_data.get("user_id")
        if not user_id:
            return exclude

        rows = _table_get(
            config,
            auth_manager,
            "sys_user",
            {
                "sysparm_query": f"sys_id={user_id}",
                "sysparm_limit": 1,
                "sysparm_fields": "user_name,name,email",
                "sysparm_display_value": "true",
            },
        )
        if not rows:
            return exclude

        row = rows[0]
        for key in ("user_name", "name", "email"):
            value = row.get(key)
            if value:
                exclude.update(_tokenize(str(value)))
    except Exception:
        return exclude

    return exclude


def _discover_marker_strategy(
    config: ServerConfig, auth_manager: AuthManager
) -> Optional[Dict[str, Any]]:
    candidates = [
        {
            "name": "sys_tag",
            "entry_table": "sys_tag_entry",
            "tag_table": "sys_tag",
            "entry_field_options": {
                "table": ["table", "table_name", "short_table_name"],
                "record": ["document_key", "document_id", "document", "table_key"],
                "tag": ["tag", "label"],
            },
        },
        {
            "name": "label",
            "entry_table": "label_entry",
            "tag_table": "label",
            "entry_field_options": {
                "table": ["table", "table_name", "short_table_name"],
                "record": ["document_key", "document_id", "document", "table_key"],
                "tag": ["label", "tag"],
            },
        },
    ]

    for candidate in candidates:
        dict_rows = _table_get(
            config,
            auth_manager,
            "sys_dictionary",
            {
                "sysparm_query": f"name={candidate['entry_table']}",
                "sysparm_fields": "element",
                "sysparm_limit": 200,
            },
        )
        fields = {row.get("element") for row in dict_rows if row.get("element")}
        if not fields:
            # Fallback: keep candidate even if dictionary lookup is unavailable.
            candidate["resolved_fields"] = {}
            return candidate

        resolved: Dict[str, str] = {}
        for key, options in candidate["entry_field_options"].items():
            for option in options:
                if option in fields:
                    resolved[key] = option
                    break

        if {"table", "record", "tag"}.issubset(resolved):
            candidate["resolved_fields"] = resolved
            return candidate

        # Fallback: try field combinations at runtime.
        candidate["resolved_fields"] = {}
        return candidate

    return None


def _strategy_with_fallbacks(primary: Dict[str, Any]) -> List[Dict[str, Any]]:
    order = [primary]
    if primary.get("name") == "sys_tag":
        order.append(
            {
                "name": "label",
                "entry_table": "label_entry",
                "tag_table": "label",
                "resolved_fields": {},
            }
        )
    else:
        order.append(
            {
                "name": "sys_tag",
                "entry_table": "sys_tag_entry",
                "tag_table": "sys_tag",
                "resolved_fields": {},
            }
        )
    return order


def _get_or_create_tag(
    config: ServerConfig,
    auth_manager: AuthManager,
    tag_table: str,
    tag_name: str,
) -> Optional[str]:
    query = _table_get(
        config,
        auth_manager,
        tag_table,
        {
            "sysparm_query": f"name={tag_name}",
            "sysparm_fields": "sys_id,name",
            "sysparm_limit": 1,
        },
    )
    if query:
        return query[0].get("sys_id")

    created = _table_post(config, auth_manager, tag_table, {"name": tag_name})
    if created:
        return created.get("sys_id")
    return None


def _ensure_tag_link(
    config: ServerConfig,
    auth_manager: AuthManager,
    entry_table: str,
    fields_map: Dict[str, str],
    incident_sys_id: str,
    tag_sys_id: str,
) -> bool:
    runtime_candidates = [
        ("table", "document_key", "tag"),
        ("table_name", "document_id", "tag"),
        ("short_table_name", "document", "tag"),
        ("table", "document_key", "label"),
        ("table_name", "document_id", "label"),
        ("short_table_name", "document", "label"),
    ]

    if fields_map:
        runtime_candidates.insert(
            0,
            (
                fields_map.get("table", "table"),
                fields_map.get("record", "document_key"),
                fields_map.get("tag", "tag"),
            ),
        )

    for table_field, record_field, tag_field in runtime_candidates:
        query = (
            f"{table_field}=incident^{record_field}={incident_sys_id}^{tag_field}={tag_sys_id}"
        )
        existing = _table_get(
            config,
            auth_manager,
            entry_table,
            {"sysparm_query": query, "sysparm_fields": "sys_id", "sysparm_limit": 1},
        )
        if existing:
            return True

        payload = {
            table_field: "incident",
            record_field: incident_sys_id,
            tag_field: tag_sys_id,
        }
        created = _table_post(config, auth_manager, entry_table, payload)
        if created and created.get("sys_id"):
            return True

    return False


def _analyze_incident(
    config: ServerConfig,
    auth_manager: AuthManager,
    incident_number: str,
    include_attachments: bool,
    max_tags: int,
) -> Dict[str, Any]:
    incident = _get_incident_by_number(config, auth_manager, incident_number)
    if not incident:
        return {
            "incident_number": incident_number,
            "success": False,
            "error": "Incident not found",
            "tags": [],
        }

    incident_sys_id = incident.get("sys_id")
    journal = _get_incident_journal(config, auth_manager, incident_sys_id) if incident_sys_id else []
    attachments = _get_incident_attachments(config, auth_manager, incident_sys_id) if (incident_sys_id and include_attachments) else []

    if include_attachments:
        for att in attachments:
            att_id = att.get("sys_id")
            ctype = str(att.get("content_type") or "")
            if att_id and ctype.startswith("image/"):
                att["ocr_text"] = _try_extract_ocr_text(config, auth_manager, att_id, ctype)

    text = _build_context_text(incident, journal, attachments)
    exclude_tokens = _get_current_user_exclude_tokens(config, auth_manager)
    tags = _classify_text_to_tags(text, max_tags, exclude_tokens=exclude_tokens)

    return {
        "incident_number": incident_number,
        "incident_sys_id": incident_sys_id,
        "success": True,
        "short_description": incident.get("short_description"),
        "tags": tags,
        "analysis": {
            "journal_entries": len(journal),
            "attachments": [
                {
                    "file_name": a.get("file_name"),
                    "content_type": a.get("content_type"),
                    "ocr_used": bool(a.get("ocr_text")),
                }
                for a in attachments
            ],
        },
    }


def suggest_incident_tags(
    config: ServerConfig, auth_manager: AuthManager, params: SuggestIncidentTagsParams
) -> str:
    """Analyze incidents and return suggested marker tags without writing."""
    results = [
        _analyze_incident(
            config,
            auth_manager,
            incident_number=inc,
            include_attachments=params.include_attachments,
            max_tags=params.max_tags_per_incident,
        )
        for inc in params.incident_numbers
    ]
    return json.dumps({"success": True, "results": results}, ensure_ascii=False)


def classify_and_tag_incidents(
    config: ServerConfig, auth_manager: AuthManager, params: ClassifyAndTagIncidentsParams
) -> str:
    """Analyze incidents and write resulting tags as ServiceNow markers."""
    strategy = _discover_marker_strategy(config, auth_manager)
    if not strategy:
        return json.dumps(
            {
                "success": False,
                "error": "No supported marker strategy found (sys_tag_entry/label_entry).",
            },
            ensure_ascii=False,
        )

    strategy_order = _strategy_with_fallbacks(strategy)
    run_results: List[Dict[str, Any]] = []

    for incident_number in params.incident_numbers:
        analyzed = _analyze_incident(
            config,
            auth_manager,
            incident_number=incident_number,
            include_attachments=params.include_attachments,
            max_tags=params.max_tags_per_incident,
        )
        if not analyzed.get("success"):
            run_results.append(analyzed)
            continue

        incident_sys_id = analyzed.get("incident_sys_id")
        tags = analyzed.get("tags", [])
        applied: List[str] = []
        failed: List[str] = []

        strategy_used = None
        for tag in tags:
            if _add_label_via_data_table(config, auth_manager, incident_sys_id, tag):
                applied.append(tag)
                strategy_used = "data_table_labels"
                continue

            tagged = False
            for current_strategy in strategy_order:
                tag_sys_id = _get_or_create_tag(
                    config, auth_manager, current_strategy["tag_table"], tag
                )
                if not tag_sys_id:
                    continue

                ok = _ensure_tag_link(
                    config,
                    auth_manager,
                    current_strategy["entry_table"],
                    current_strategy.get("resolved_fields", {}),
                    incident_sys_id,
                    tag_sys_id,
                )
                if ok:
                    applied.append(tag)
                    strategy_used = current_strategy["name"]
                    tagged = True
                    break

            if not tagged:
                failed.append(tag)

        if params.add_audit_work_note and applied:
            note = (
                "[auto-tagging] Markers automatically applied based on analysis of "
                f"description/comments/attachments: {', '.join(applied)}"
            )
            _table_patch(config, auth_manager, "incident", incident_sys_id, {"work_notes": note})

        analyzed["applied_tags"] = applied
        analyzed["failed_tags"] = failed
        analyzed["marker_strategy"] = strategy_used or strategy["name"]
        run_results.append(analyzed)

    return json.dumps({"success": True, "results": run_results}, ensure_ascii=False)
