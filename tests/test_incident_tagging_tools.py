import json
from unittest.mock import patch

from servicenow_mcp.tools.incident_tagging_tools import (
    ClassifyAndTagIncidentsParams,
    SuggestIncidentTagsParams,
    _classify_text_to_tags,
    classify_and_tag_incidents,
    suggest_incident_tags,
)


def test_classify_text_to_tags_maps_semantic_keywords():
    text = "Falha de login em producao com timeout na API e erro de certificado SSL"
    tags = _classify_text_to_tags(text, max_tags=10)
    assert "acesso-autenticacao" in tags
    assert "ambiente-producao" in tags
    assert "api-integracao" in tags
    assert "certificados-ssl" in tags


def test_suggest_incident_tags_returns_analysis_json():
    fake_incident = {
        "sys_id": "abc123",
        "number": "INC1",
        "short_description": "Erro na API",
        "description": "Timeout ao integrar",
        "comments": "",
        "work_notes": "",
        "category": "Software",
        "subcategory": "API",
        "priority": "2",
        "state": "2",
    }

    with patch("servicenow_mcp.tools.incident_tagging_tools._get_incident_by_number", return_value=fake_incident), patch(
        "servicenow_mcp.tools.incident_tagging_tools._get_incident_journal", return_value=[]
    ), patch("servicenow_mcp.tools.incident_tagging_tools._get_incident_attachments", return_value=[]):
        out = suggest_incident_tags(
            config=None,
            auth_manager=None,
            params=SuggestIncidentTagsParams(incident_numbers=["INC1"], include_attachments=False),
        )

    parsed = json.loads(out)
    assert parsed["success"] is True
    assert parsed["results"][0]["incident_number"] == "INC1"
    assert isinstance(parsed["results"][0]["tags"], list)


def test_classify_and_tag_incidents_applies_tags_with_strategy():
    fake_analysis = {
        "incident_number": "INC1",
        "incident_sys_id": "abc123",
        "success": True,
        "short_description": "Erro na API",
        "tags": ["api-integracao", "falha-aplicacao"],
        "analysis": {"journal_entries": 0, "attachments": []},
    }

    with patch(
        "servicenow_mcp.tools.incident_tagging_tools._discover_marker_strategy",
        return_value={
            "name": "sys_tag",
            "tag_table": "sys_tag",
            "entry_table": "sys_tag_entry",
            "resolved_fields": {"table": "table", "record": "document_key", "tag": "tag"},
        },
    ), patch("servicenow_mcp.tools.incident_tagging_tools._analyze_incident", return_value=fake_analysis), patch(
        "servicenow_mcp.tools.incident_tagging_tools._add_label_via_data_table",
        return_value=False,
    ), patch(
        "servicenow_mcp.tools.incident_tagging_tools._get_or_create_tag",
        side_effect=["tag1", "tag2"],
    ), patch(
        "servicenow_mcp.tools.incident_tagging_tools._ensure_tag_link",
        return_value=True,
    ), patch("servicenow_mcp.tools.incident_tagging_tools._table_patch", return_value=True):
        out = classify_and_tag_incidents(
            config=None,
            auth_manager=None,
            params=ClassifyAndTagIncidentsParams(incident_numbers=["INC1"], include_attachments=False),
        )

    parsed = json.loads(out)
    assert parsed["success"] is True
    result = parsed["results"][0]
    assert result["applied_tags"] == ["api-integracao", "falha-aplicacao"]
    assert result["marker_strategy"] == "sys_tag"
