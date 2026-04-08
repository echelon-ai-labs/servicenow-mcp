"""
Shared helper utilities for ServiceNow MCP tool functions.

These helpers are extracted from the individual tool modules to eliminate
duplication across change_tools, changeset_tools, epic_tools, project_tools,
scrum_task_tools, sctask_tools, story_tools, and time_card_tools.
"""

import logging
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def get_instance_url(auth_manager: Any, server_config: Any) -> Optional[str]:
    """
    Get the instance URL from either server_config or auth_manager.

    Checks server_config first (preferred), then auth_manager as fallback.
    This also handles the case where the two arguments were accidentally swapped
    by the caller.

    Args:
        auth_manager: The authentication manager (or accidentally a ServerConfig).
        server_config: The server configuration (or accidentally an AuthManager).

    Returns:
        The instance URL string, or None if it cannot be found.
    """
    if hasattr(server_config, "instance_url"):
        return server_config.instance_url
    if hasattr(auth_manager, "instance_url"):
        return auth_manager.instance_url
    logger.error("Cannot find instance_url in either server_config or auth_manager")
    return None


def get_headers(auth_manager: Any, server_config: Any) -> Optional[Dict[str, str]]:
    """
    Get HTTP headers from either auth_manager or server_config.

    Checks auth_manager first (preferred), then server_config as fallback.
    This also handles the case where the two arguments were accidentally swapped
    by the caller.

    Args:
        auth_manager: The authentication manager (or accidentally a ServerConfig).
        server_config: The server configuration (or accidentally an AuthManager).

    Returns:
        A dict of HTTP headers, or None if get_headers() cannot be found.
    """
    if hasattr(auth_manager, "get_headers"):
        return auth_manager.get_headers()
    if hasattr(server_config, "get_headers"):
        return server_config.get_headers()
    logger.error("Cannot find get_headers method in either auth_manager or server_config")
    return None


def unwrap_and_validate_params(
    params: Any,
    model_class: Type[T],
    required_fields: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Unwrap and validate tool parameters against a Pydantic model.

    Handles several input forms that arise in MCP tool dispatch:
    - Already the correct Pydantic model instance → used directly.
    - Another Pydantic model → converted via model_dump() / dict().
    - A plain dict, optionally nested under a ``{"params": {...}}`` wrapper.
    - Any other object with a ``.dict()`` or built-in ``dict()`` conversion.

    After construction the model instance is checked for any ``required_fields``
    whose value is ``None``.

    Args:
        params: The raw parameter value received by the tool function.
        model_class: The Pydantic model class to validate against.
        required_fields: Optional list of field names that must not be None.

    Returns:
        ``{"success": True, "params": <model_instance>}`` on success, or
        ``{"success": False, "message": <error string>}`` on failure.
    """
    # Unwrap dict nested under a single "params" key (common MCP dispatch artifact)
    if (
        isinstance(params, dict)
        and len(params) == 1
        and "params" in params
        and isinstance(params["params"], dict)
    ):
        logger.warning("Detected params wrapped in a 'params' key. Unwrapping...")
        params = params["params"]

    # Already the exact target model — use as-is
    if isinstance(params, model_class):
        model_instance = params

    # Another Pydantic model — convert to target via dict
    elif isinstance(params, BaseModel):
        raw = params.model_dump() if hasattr(params, "model_dump") else params.dict()
        try:
            model_instance = model_class(**raw)
        except Exception as e:
            logger.error("Failed to convert Pydantic model to %s: %s", model_class.__name__, e)
            return {"success": False, "message": f"Error validating parameters: {e}"}

    # Plain dict — construct directly
    elif isinstance(params, dict):
        try:
            model_instance = model_class(**params)
        except Exception as e:
            logger.error("Failed to instantiate %s from dict: %s", model_class.__name__, e)
            return {"success": False, "message": f"Error validating parameters: {e}"}

    # Fallback: try dict-like conversion (legacy .dict() or dict())
    else:
        try:
            raw = params.dict() if hasattr(params, "dict") else dict(params)
            model_instance = model_class(**raw)
        except Exception:
            return {
                "success": False,
                "message": (
                    f"Invalid parameters format. Expected a dictionary, "
                    f"got {type(params).__name__}"
                ),
            }

    # Check required fields on the instantiated model
    if required_fields:
        missing = [f for f in required_fields if getattr(model_instance, f, None) is None]
        if missing:
            return {
                "success": False,
                "message": f"Missing required fields: {', '.join(missing)}",
            }

    return {"success": True, "params": model_instance}
