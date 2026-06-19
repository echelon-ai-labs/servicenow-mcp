"""
Validation utilities for the ServiceNow MCP server.
"""

import re

def is_valid_sys_id(sys_id: str) -> bool:
    """Validate that the ID is a 32-character hexadecimal string."""
    if not sys_id:
        return False
    return bool(re.match(r"^[a-fA-F0-9]{32}$", sys_id))
