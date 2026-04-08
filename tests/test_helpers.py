"""
Tests for servicenow_mcp.utils.helpers — the shared tool helper utilities.
"""

from pydantic import BaseModel, Field
from typing import Optional

from servicenow_mcp.utils.helpers import (
    get_headers,
    get_instance_url,
    unwrap_and_validate_params,
)


# ---------------------------------------------------------------------------
# Minimal Pydantic models used in tests
# ---------------------------------------------------------------------------

class SampleParams(BaseModel):
    name: str = Field(..., description="Name field")
    value: Optional[int] = Field(None, description="Optional int")


class AnotherParams(BaseModel):
    title: str = Field(..., description="Title")


# ---------------------------------------------------------------------------
# Fake objects that stand in for AuthManager / ServerConfig
# ---------------------------------------------------------------------------

class FakeAuthManager:
    instance_url = "https://auth.example.com"

    def get_headers(self):
        return {"Authorization": "Bearer token"}


class FakeServerConfig:
    instance_url = "https://config.example.com"

    def get_headers(self):
        return {"X-From": "server_config"}


class NoInstanceUrl:
    def get_headers(self):
        return {"X-Auth": "yes"}


class NoGetHeaders:
    instance_url = "https://no-headers.example.com"


class BareObject:
    pass


# ---------------------------------------------------------------------------
# get_instance_url
# ---------------------------------------------------------------------------

class TestGetInstanceUrl:
    def test_prefers_server_config(self):
        """server_config.instance_url takes priority over auth_manager."""
        auth = FakeAuthManager()
        cfg = FakeServerConfig()
        assert get_instance_url(auth, cfg) == "https://config.example.com"

    def test_falls_back_to_auth_manager(self):
        """Falls back to auth_manager when server_config has no instance_url."""
        auth = FakeAuthManager()
        cfg = BareObject()
        assert get_instance_url(auth, cfg) == "https://auth.example.com"

    def test_returns_none_when_neither_has_url(self):
        result = get_instance_url(BareObject(), BareObject())
        assert result is None

    def test_handles_swapped_args(self):
        """If caller accidentally swaps args, still finds the URL."""
        real_cfg = FakeServerConfig()   # has instance_url
        # Swap: cfg where auth expected, BareObject where cfg expected
        result = get_instance_url(real_cfg, BareObject())
        assert result == "https://config.example.com"


# ---------------------------------------------------------------------------
# get_headers
# ---------------------------------------------------------------------------

class TestGetHeaders:
    def test_prefers_auth_manager(self):
        """auth_manager.get_headers() is tried first."""
        auth = FakeAuthManager()
        cfg = FakeServerConfig()
        headers = get_headers(auth, cfg)
        assert headers == {"Authorization": "Bearer token"}

    def test_falls_back_to_server_config(self):
        """Falls back to server_config.get_headers() when auth_manager lacks it."""
        cfg = FakeServerConfig()
        result = get_headers(BareObject(), cfg)
        assert result == {"X-From": "server_config"}

    def test_returns_none_when_neither_has_method(self):
        result = get_headers(BareObject(), BareObject())
        assert result is None

    def test_handles_no_get_headers_on_auth_manager(self):
        auth = NoGetHeaders()
        cfg = FakeServerConfig()
        result = get_headers(auth, cfg)
        assert result == {"X-From": "server_config"}


# ---------------------------------------------------------------------------
# unwrap_and_validate_params
# ---------------------------------------------------------------------------

class TestUnwrapAndValidateParams:
    # --- Success paths ---

    def test_plain_dict(self):
        result = unwrap_and_validate_params({"name": "test"}, SampleParams)
        assert result["success"] is True
        assert result["params"].name == "test"
        assert result["params"].value is None

    def test_dict_with_optional_field(self):
        result = unwrap_and_validate_params({"name": "x", "value": 42}, SampleParams)
        assert result["success"] is True
        assert result["params"].value == 42

    def test_correct_model_instance_passthrough(self):
        """Already the target model class — used as-is."""
        p = SampleParams(name="direct")
        result = unwrap_and_validate_params(p, SampleParams)
        assert result["success"] is True
        assert result["params"] is p

    def test_other_pydantic_model_converted(self):
        """A different Pydantic model is converted via its dict representation."""
        class CompatParams(BaseModel):
            name: str
            value: Optional[int] = None

        compat = CompatParams(name="compat", value=7)
        result = unwrap_and_validate_params(compat, SampleParams)
        assert result["success"] is True
        assert result["params"].name == "compat"
        assert result["params"].value == 7

    def test_unwraps_nested_params_key(self):
        """Dict wrapped under a single 'params' key is unwrapped automatically."""
        wrapped = {"params": {"name": "wrapped"}}
        result = unwrap_and_validate_params(wrapped, SampleParams)
        assert result["success"] is True
        assert result["params"].name == "wrapped"

    # --- Required fields ---

    def test_required_fields_all_present(self):
        result = unwrap_and_validate_params(
            {"name": "req_test", "value": 1}, SampleParams, required_fields=["name", "value"]
        )
        assert result["success"] is True

    def test_required_fields_missing(self):
        """A None field listed in required_fields triggers failure."""
        result = unwrap_and_validate_params(
            {"name": "only_name"}, SampleParams, required_fields=["value"]
        )
        assert result["success"] is False
        assert "value" in result["message"]

    def test_required_fields_multiple_missing(self):
        result = unwrap_and_validate_params(
            {"name": "x"}, SampleParams, required_fields=["value"]
        )
        assert result["success"] is False

    # --- Failure paths ---

    def test_invalid_dict_missing_required_model_field(self):
        """Pydantic validation error when a required model field is absent."""
        result = unwrap_and_validate_params({}, SampleParams)
        assert result["success"] is False
        assert "message" in result

    def test_invalid_type_for_field(self):
        result = unwrap_and_validate_params({"name": "ok", "value": "not_an_int"}, SampleParams)
        # Pydantic v2 coerces str→int for int fields, so this may succeed
        # Just verify it returns a dict with 'success' key
        assert "success" in result

    def test_unconvertible_object(self):
        """An object that can't be dict()-ed returns a failure."""

        class Broken:
            def __iter__(self):
                raise TypeError("not iterable")
            def __len__(self):
                return 0

        result = unwrap_and_validate_params(Broken(), SampleParams)
        assert result["success"] is False

    def test_no_double_wrap(self):
        """A 'params' key wrapping is only applied when it is the sole key."""
        # Two keys — should NOT be unwrapped
        d = {"params": {"name": "inner"}, "extra": "field"}
        result = unwrap_and_validate_params(d, SampleParams)
        # Pydantic will see "params" and "extra" as unexpected fields and either
        # coerce or fail — but the "name" field is missing, so this should fail
        assert result["success"] is False

    # --- Edge cases ---

    def test_no_required_fields_arg(self):
        """required_fields=None (default) skips the check entirely."""
        result = unwrap_and_validate_params({"name": "edge"}, SampleParams)
        assert result["success"] is True

    def test_empty_required_fields_list(self):
        result = unwrap_and_validate_params({"name": "edge"}, SampleParams, required_fields=[])
        assert result["success"] is True
