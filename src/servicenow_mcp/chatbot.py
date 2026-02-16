"""
ServiceNow Chatbot - Web-based chat interface with pluggable LLM backend.

Supports two LLM providers:
  - anthropic: Claude API (default, requires ANTHROPIC_API_KEY)
  - nowassist: NowLLM via ServiceNow Scripted REST API (requires NowAssist installed)

Uses the same tool functions as the MCP server but calls them directly,
allowing natural language interaction with ServiceNow through a browser.
"""

import argparse
import json
import logging
import os
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

import requests as http_requests
import uvicorn
from dotenv import load_dotenv
from pydantic import ValidationError
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.cli import create_config, parse_args
from servicenow_mcp.server import serialize_tool_output
from servicenow_mcp.tools.knowledge_base import (
    create_category as create_kb_category_tool,
)
from servicenow_mcp.tools.knowledge_base import (
    list_categories as list_kb_categories_tool,
)
from servicenow_mcp.utils.tool_utils import get_tool_definitions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"
MODEL = os.environ.get("CHATBOT_MODEL", "claude-haiku-4-5-20251001")
MAX_TOOL_ROUNDS = 15
MAX_TOOL_RESULT_CHARS = 8000  # Truncate large tool results
MAX_HISTORY_MESSAGES = 20  # Keep last N messages to avoid token overflow
SYSTEM_PROMPT = (
    "You are a helpful ServiceNow assistant. You have access to tools that interact "
    "with a ServiceNow instance. Use them to answer user questions about incidents, "
    "changes, catalog items, scripts, workflows, users, knowledge articles, and more. "
    "When presenting results, format them clearly. If a tool call fails, explain "
    "the error and suggest alternatives."
)


def _strip_schema(schema: Dict) -> Dict:
    """Strip verbose fields from JSON schema to reduce token count."""
    stripped = {}
    for k, v in schema.items():
        if k in ("title", "description", "$defs", "default"):
            continue
        if k == "properties" and isinstance(v, dict):
            stripped[k] = {
                pk: _strip_schema(pv) if isinstance(pv, dict) else pv
                for pk, pv in v.items()
            }
        elif isinstance(v, dict):
            stripped[k] = _strip_schema(v)
        else:
            stripped[k] = v
    return stripped


def build_claude_tools(tool_definitions: Dict, only: List[str] = None) -> List[Dict[str, Any]]:
    """Convert internal tool definitions to Claude API tool format.

    Args:
        tool_definitions: Full tool registry.
        only: If provided, only include these tool names.
    """
    tools = []
    for tool_name, definition in tool_definitions.items():
        if only and tool_name not in only:
            continue
        _impl, params_model, _ret, description, _ser = definition
        try:
            schema = params_model.model_json_schema()
            tools.append({
                "name": tool_name,
                "description": description,
                "input_schema": _strip_schema(schema),
            })
        except Exception as e:
            logger.error(f"Failed to build schema for tool '{tool_name}': {e}")
    return tools


def execute_tool(
    tool_name: str,
    tool_input: Dict[str, Any],
    tool_definitions: Dict,
    config: Any,
    auth_manager: AuthManager,
) -> str:
    """Execute a tool function and return serialized output."""
    if tool_name not in tool_definitions:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    impl_func, params_model, _ret, _desc, _ser = tool_definitions[tool_name]

    try:
        params = params_model(**tool_input)
    except ValidationError as e:
        return json.dumps({"error": f"Invalid parameters for {tool_name}: {str(e)}"})

    try:
        result = impl_func(config, auth_manager, params)
        return serialize_tool_output(result, tool_name)
    except Exception as e:
        logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
        return json.dumps({"error": f"Tool execution failed: {str(e)}"})


def _truncate(text: str, max_chars: int = MAX_TOOL_RESULT_CHARS) -> str:
    """Truncate text to max_chars, appending a note if truncated."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... (truncated, {len(text)} chars total)"


def _trim_history(messages: List[Dict], max_messages: int = MAX_HISTORY_MESSAGES) -> List[Dict]:
    """Return the last max_messages from conversation, ensuring it starts with a user message."""
    if len(messages) <= max_messages:
        return messages
    trimmed = messages[-max_messages:]
    # Ensure first message is from user (required by Claude API)
    while trimmed and trimmed[0].get("role") != "user":
        trimmed = trimmed[1:]
    return trimmed


def _call_api(client, model, system, messages, tools=None, max_tokens=4096):
    """Call Claude API with retry on rate limit."""
    import anthropic

    msgs = _trim_history(messages)
    kwargs = dict(model=model, max_tokens=max_tokens, system=system, messages=msgs)
    if tools:
        kwargs["tools"] = tools
    for attempt in range(3):
        try:
            return client.messages.create(**kwargs)
        except anthropic.RateLimitError:
            wait = (attempt + 1) * 10
            logger.warning(f"Rate limited, waiting {wait}s (attempt {attempt + 1}/3)")
            time.sleep(wait)
            if attempt == 2:
                return None
        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            return None
    return None


class ConversationManager:
    """Manages chat sessions and the Claude API tool-use loop."""

    def __init__(self, config: Any, auth_manager: AuthManager):
        import anthropic

        self.config = config
        self.auth_manager = auth_manager
        self.client = anthropic.Anthropic()
        self.tool_definitions = get_tool_definitions(
            create_kb_category_tool, list_kb_categories_tool
        )
        # Build compact catalog: "tool_name - description" one per line
        self.tool_catalog = "\n".join(
            f"- {name}: {defn[3]}" for name, defn in self.tool_definitions.items()
        )
        self.sessions: Dict[str, List[Dict]] = {}
        logger.info(f"ConversationManager initialized with {len(self.tool_definitions)} tools")

    def get_or_create_session(self, session_id: str) -> List[Dict]:
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        return self.sessions[session_id]

    def clear_session(self, session_id: str) -> None:
        self.sessions.pop(session_id, None)

    def _select_tools(self, user_message: str) -> List[str]:
        """Phase 1: Ask Claude to pick relevant tools from a compact list."""
        selection_prompt = (
            "Given the user message below, select which ServiceNow tools are needed. "
            "Reply with ONLY a JSON array of tool names, nothing else.\n\n"
            "IMPORTANT rules:\n"
            "- For counting records or asking 'how many', use query_table (it has count_only mode)\n"
            "- For tables without a dedicated tool (update sets, CMDB, etc.), use query_table\n"
            "- Only use list_* tools when the user wants to see actual record details\n\n"
            f"Available tools:\n{self.tool_catalog}\n\n"
            f"User message: {user_message}\n\n"
            "Reply with a JSON array, e.g. [\"query_table\"]. "
            "Pick only the tools likely needed (max 8). If the user is just chatting "
            "and no tool is needed, reply with []."
        )
        response = _call_api(
            self.client,
            MODEL,
            "You are a tool selector. Reply ONLY with a JSON array of tool names.",
            [{"role": "user", "content": selection_prompt}],
            max_tokens=256,
        )
        if not response:
            return []

        text = "".join(b.text for b in response.content if b.type == "text").strip()
        # Strip markdown code fences if present (e.g. ```json\n[...]\n```)
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json) and last line (```)
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()
        try:
            selected = json.loads(text)
            if isinstance(selected, list):
                valid = [t for t in selected if t in self.tool_definitions]
                logger.info(f"Selected tools: {valid}")
                return valid
        except json.JSONDecodeError:
            logger.warning(f"Could not parse tool selection: {text}")
        return []

    def chat(self, session_id: str, user_message: str) -> Dict[str, Any]:
        """Process a user message through the Claude API tool-use loop."""
        messages = self.get_or_create_session(session_id)
        messages.append({"role": "user", "content": user_message})

        tools_used = []

        # Phase 1: Select relevant tools (cheap, ~1k tokens)
        selected_tool_names = self._select_tools(user_message)
        if selected_tool_names:
            claude_tools = build_claude_tools(self.tool_definitions, only=selected_tool_names)
            logger.info(f"Sending {len(claude_tools)} tool schemas (of {len(self.tool_definitions)})")
        else:
            claude_tools = None

        # Phase 2: Chat with only the selected tools
        for _round in range(MAX_TOOL_ROUNDS):
            response = _call_api(
                self.client, MODEL, SYSTEM_PROMPT, messages, tools=claude_tools
            )
            if not response:
                return {
                    "response": "Rate limited or API error. Please wait and try again.",
                    "tools_used": tools_used,
                }

            if response.stop_reason == "tool_use":
                messages.append({
                    "role": "assistant",
                    "content": [block.model_dump() for block in response.content],
                })

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        logger.info(f"Executing tool: {tool_name}")

                        result_str = execute_tool(
                            tool_name,
                            tool_input,
                            self.tool_definitions,
                            self.config,
                            self.auth_manager,
                        )
                        tools_used.append(tool_name)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": _truncate(result_str),
                        })

                messages.append({"role": "user", "content": tool_results})
            else:
                text_parts = [
                    block.text for block in response.content if block.type == "text"
                ]
                assistant_text = "\n".join(text_parts) if text_parts else ""
                messages.append({"role": "assistant", "content": assistant_text})
                return {"response": assistant_text, "tools_used": tools_used}

        return {
            "response": "Reached maximum tool rounds. Please try a simpler query.",
            "tools_used": tools_used,
        }


class NowAssistProvider:
    """Chat provider using NowLLM via ServiceNow's Scripted REST API.

    Instead of calling Anthropic's Claude API, this sends prompts to a
    Scripted REST API on the ServiceNow instance that wraps NowLLM.
    Tool calling is handled via text-based <tool_call> tags in the prompt.
    """

    TOOL_CALL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)

    def __init__(self, config: Any, auth_manager: AuthManager):
        self.config = config
        self.auth_manager = auth_manager
        self.tool_definitions = get_tool_definitions(
            create_kb_category_tool, list_kb_categories_tool
        )
        self.sessions: Dict[str, List[Dict]] = {}
        self.nowllm_path = os.environ.get(
            "NOWLLM_API_PATH", "/api/xti/nowllm_chat/generate"
        )
        self.tool_catalog = self._build_tool_catalog()
        logger.info(
            f"NowAssistProvider initialized with {len(self.tool_definitions)} tools, "
            f"NowLLM endpoint: {self.nowllm_path}"
        )

    def _build_tool_catalog(self) -> str:
        """Build compact tool descriptions for NowLLM prompt."""
        lines = []
        for name, defn in self.tool_definitions.items():
            _impl, params_model, _ret, desc, _ser = defn
            schema = params_model.model_json_schema()
            props = schema.get("properties", {})
            required = schema.get("required", [])
            params = []
            for pname, pinfo in props.items():
                ptype = pinfo.get("type", "any")
                req = " (required)" if pname in required else ""
                params.append(f"{pname}: {ptype}{req}")
            params_str = ", ".join(params)
            lines.append(f"- {name}({params_str}): {desc}")
        return "\n".join(lines)

    def _call_nowllm(self, prompt: str) -> str:
        """Call NowLLM via ServiceNow Scripted REST API."""
        url = f"{self.config.instance_url}{self.nowllm_path}"
        headers = self.auth_manager.get_headers()

        resp = http_requests.post(
            url,
            json={"prompt": prompt, "max_tokens": 4096},
            headers=headers,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        # ServiceNow REST API wraps response in "result"
        result = data.get("result", data)
        return result.get("text", str(result))

    def _build_prompt(self, messages: List[Dict]) -> str:
        """Build full prompt string from conversation messages."""
        prompt = f"""{SYSTEM_PROMPT}

You have access to these ServiceNow tools:
{self.tool_catalog}

To call a tool, respond with EXACTLY this format (one tool at a time):
<tool_call>{{"name": "tool_name", "parameters": {{"key": "value"}}}}</tool_call>

Rules:
- Call ONE tool at a time
- After receiving tool results, either call another tool or give your final answer
- For counting records, use query_table with count_only=true
- For tables without a dedicated tool, use query_table
- Give your final answer as plain text WITHOUT <tool_call> tags

Conversation:"""

        for msg in messages[-MAX_HISTORY_MESSAGES:]:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                prompt += f"\nUser: {content}"
            elif role == "assistant":
                prompt += f"\nAssistant: {content}"
            elif role == "tool_result":
                prompt += f"\nTool result: {content}"

        prompt += "\nAssistant: "
        return prompt

    def _parse_tool_call(self, text: str) -> dict | None:
        """Extract a tool call from NowLLM response text."""
        match = self.TOOL_CALL_RE.search(text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse tool call JSON: {match.group(1)}")
        return None

    def get_or_create_session(self, session_id: str) -> List[Dict]:
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        return self.sessions[session_id]

    def clear_session(self, session_id: str) -> None:
        self.sessions.pop(session_id, None)

    def chat(self, session_id: str, user_message: str) -> Dict[str, Any]:
        """Process a user message through NowLLM with text-based tool calling."""
        messages = self.get_or_create_session(session_id)
        messages.append({"role": "user", "content": user_message})

        tools_used = []

        for _round in range(MAX_TOOL_ROUNDS):
            prompt = self._build_prompt(messages)

            try:
                response_text = self._call_nowllm(prompt)
            except Exception as e:
                logger.error(f"NowLLM API error: {e}", exc_info=True)
                return {
                    "response": f"Error calling NowLLM: {str(e)}",
                    "tools_used": tools_used,
                }

            tool_call = self._parse_tool_call(response_text)

            if tool_call:
                tool_name = tool_call.get("name", "")
                tool_params = tool_call.get("parameters", {})
                logger.info(f"NowLLM requested tool: {tool_name}")
                messages.append({"role": "assistant", "content": response_text})

                result_str = execute_tool(
                    tool_name, tool_params, self.tool_definitions,
                    self.config, self.auth_manager,
                )
                tools_used.append(tool_name)
                messages.append({"role": "tool_result", "content": _truncate(result_str)})
            else:
                # No tool call — final answer
                clean = response_text.strip()
                messages.append({"role": "assistant", "content": clean})
                return {"response": clean, "tools_used": tools_used}

        return {
            "response": "Reached maximum tool rounds. Please try a simpler query.",
            "tools_used": tools_used,
        }


def create_chatbot_app(config: Any, auth_manager: AuthManager, provider: str = "anthropic") -> Starlette:
    """Create the Starlette web application.

    Args:
        config: ServiceNow server config.
        auth_manager: ServiceNow auth manager.
        provider: LLM provider - "anthropic", "nowassist", or None (proxy-only).
    """
    if provider == "nowassist":
        manager = NowAssistProvider(config, auth_manager)
    elif provider == "anthropic":
        manager = ConversationManager(config, auth_manager)
    else:
        manager = None
    tool_definitions = get_tool_definitions(create_kb_category_tool, list_kb_categories_tool)

    async def homepage(request: Request) -> HTMLResponse:
        html_path = STATIC_DIR / "chat.html"
        return HTMLResponse(html_path.read_text())

    async def chat_endpoint(request: Request) -> JSONResponse:
        if not manager:
            return JSONResponse(
                {"error": "Chat not available. Running in proxy-only mode. "
                 "Set ANTHROPIC_API_KEY or LLM_PROVIDER=nowassist to enable chat."},
                status_code=503,
            )
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        user_message = body.get("message", "").strip()
        if not user_message:
            return JSONResponse({"error": "Empty message"}, status_code=400)

        session_id = body.get("session_id") or str(uuid.uuid4())
        result = manager.chat(session_id, user_message)
        result["session_id"] = session_id
        return JSONResponse(result)

    async def clear_endpoint(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        session_id = body.get("session_id", "")
        if session_id and manager:
            manager.clear_session(session_id)
        return JSONResponse({"status": "cleared"})

    async def list_tools_endpoint(request: Request) -> JSONResponse:
        """GET /api/tools - List all available tools and their parameters."""
        tools_list = []
        for tool_name, definition in tool_definitions.items():
            _impl, params_model, _ret, description, _ser = definition
            try:
                schema = params_model.model_json_schema()
            except Exception:
                schema = {}
            tools_list.append({
                "name": tool_name,
                "description": description,
                "parameters": schema,
            })
        return JSONResponse({"tools": tools_list, "count": len(tools_list)})

    async def execute_tool_endpoint(request: Request) -> JSONResponse:
        """POST /api/tools/{tool_name} - Execute a single tool with given parameters.

        Request body: { "parameters": { ... } }
        Response: { "tool": "tool_name", "result": ... }

        This is the endpoint NowAssist Skills can call via RESTMessageV2.
        """
        tool_name = request.path_params["tool_name"]

        if tool_name not in tool_definitions:
            return JSONResponse(
                {"error": f"Unknown tool: {tool_name}"},
                status_code=404,
            )

        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        tool_input = body.get("parameters", {})
        result_str = execute_tool(
            tool_name,
            tool_input,
            tool_definitions,
            config,
            auth_manager,
        )

        try:
            result_obj = json.loads(result_str)
        except (json.JSONDecodeError, TypeError):
            result_obj = result_str

        return JSONResponse({"tool": tool_name, "result": result_obj})

    routes = [
        Route("/", homepage),
        Route("/api/chat", chat_endpoint, methods=["POST"]),
        Route("/api/clear", clear_endpoint, methods=["POST"]),
        Route("/api/tools", list_tools_endpoint, methods=["GET"]),
        Route("/api/tools/{tool_name}", execute_tool_endpoint, methods=["POST"]),
    ]

    return Starlette(routes=routes)


def main():
    """Entry point for the chatbot server."""
    load_dotenv()

    # Reuse CLI config parsing for ServiceNow auth
    try:
        args = parse_args()
    except SystemExit:
        # parse_args may fail because of extra --port arg; handle manually
        args = _parse_chatbot_args()

    try:
        config = create_config(args)
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    auth_manager = AuthManager(config.auth, config.instance_url)

    # Determine LLM provider
    llm_provider = os.environ.get("LLM_PROVIDER", "").lower()
    if llm_provider == "nowassist":
        provider = "nowassist"
        logger.info("LLM_PROVIDER=nowassist. Using NowLLM via ServiceNow Scripted REST API.")
    elif os.environ.get("ANTHROPIC_API_KEY"):
        provider = "anthropic"
        logger.info("ANTHROPIC_API_KEY found. Using Claude as LLM provider.")
    else:
        provider = None
        logger.info("No LLM provider configured. Running in PROXY-ONLY mode (/api/tools/* only).")

    port = getattr(args, "port", None) or int(os.environ.get("CHATBOT_PORT", "8501"))

    app = create_chatbot_app(config, auth_manager, provider=provider)
    logger.info(f"Starting ServiceNow Chatbot on http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)


def _parse_chatbot_args():
    """Parse args with --port support for chatbot mode."""
    parser = argparse.ArgumentParser(description="ServiceNow Chatbot")
    parser.add_argument("--port", type=int, default=8501, help="Port to run the chatbot on")
    parser.add_argument(
        "--instance-url",
        default=os.environ.get("SERVICENOW_INSTANCE_URL"),
    )
    parser.add_argument("--debug", action="store_true", default=False)
    parser.add_argument("--timeout", type=int, default=int(os.environ.get("SERVICENOW_TIMEOUT", "30")))
    parser.add_argument(
        "--auth-type",
        choices=["basic", "oauth", "api_key"],
        default=os.environ.get("SERVICENOW_AUTH_TYPE", "basic"),
    )
    parser.add_argument("--username", default=os.environ.get("SERVICENOW_USERNAME"))
    parser.add_argument("--password", default=os.environ.get("SERVICENOW_PASSWORD"))
    parser.add_argument("--client-id", default=os.environ.get("SERVICENOW_CLIENT_ID"))
    parser.add_argument("--client-secret", default=os.environ.get("SERVICENOW_CLIENT_SECRET"))
    parser.add_argument("--token-url", default=os.environ.get("SERVICENOW_TOKEN_URL"))
    parser.add_argument("--api-key", default=os.environ.get("SERVICENOW_API_KEY"))
    parser.add_argument(
        "--api-key-header",
        default=os.environ.get("SERVICENOW_API_KEY_HEADER", "X-ServiceNow-API-Key"),
    )
    parser.add_argument(
        "--script-execution-api-resource-path",
        default=os.environ.get("SCRIPT_EXECUTION_API_RESOURCE_PATH"),
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
