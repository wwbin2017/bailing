"""Small Streamable HTTP client for the anonymous Parallel Search MCP."""
import asyncio
import json

import httpx

ENDPOINT = "https://search.parallel.ai/mcp"
USER_AGENT = "Bailing (https://github.com/wwbin2017/bailing)"
PROTOCOL_VERSION = "2025-03-26"
TIMEOUT = 30


class MCPError(Exception):
    pass


async def _message(client, method, params=None, request_id=None):
    payload = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        payload["params"] = params
    if request_id is not None:
        payload["id"] = request_id
    async with client.stream("POST", ENDPOINT, json=payload) as response:
        response.raise_for_status()
        if request_id is None:
            return None, response.headers
        if response.headers.get("content-type", "").startswith("text/event-stream"):
            data = []
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    data.append(line[5:].lstrip(" "))
                elif not line and data:
                    message = json.loads("\n".join(data))
                    data = []
                    if isinstance(message, dict) and message.get("id") == request_id:
                        break
            else:
                raise MCPError("MCP response stream ended without a result")
        else:
            message = json.loads(await response.aread())
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or message.get("id") != request_id:
            raise MCPError("Invalid MCP response")
        if "error" in message:
            raise MCPError("MCP request failed")
        result = message.get("result")
        if not isinstance(result, dict):
            raise MCPError("Invalid MCP result")
        return result, response.headers


async def _call_tool(name, arguments):
    # HTTP session IDs belong to this connection; arguments.session_id belongs
    # to the caller's conversation and survives new connections and failures.
    headers = {"User-Agent": USER_AGENT,
               "Accept": "application/json, text/event-stream"}
    async with httpx.AsyncClient(headers=headers, timeout=TIMEOUT, follow_redirects=False) as client:
        initialized, response_headers = await _message(client, "initialize", {
            "protocolVersion": PROTOCOL_VERSION, "capabilities": {},
            "clientInfo": {"name": "bailing", "version": "0.1.0"}}, 1)
        if initialized.get("protocolVersion") != PROTOCOL_VERSION:
            raise MCPError("Unsupported MCP protocol version")
        client.headers["MCP-Protocol-Version"] = PROTOCOL_VERSION
        if response_headers.get("mcp-session-id"):
            client.headers["Mcp-Session-Id"] = response_headers["mcp-session-id"]
        await _message(client, "notifications/initialized")
        tools, _ = await _message(client, "tools/list", request_id=2)
        if not any(isinstance(tool, dict) and tool.get("name") == name
                   for tool in (tools.get("tools") or [])):
            raise MCPError("Requested Parallel tool is unavailable")
        result, _ = await _message(client, "tools/call", {"name": name, "arguments": arguments}, 3)
        text = "\n".join(item["text"] for item in result.get("content", [])
                         if isinstance(item, dict) and item.get("type") == "text"
                         and isinstance(item.get("text"), str))
        if result.get("isError"):
            # Preserve useful service errors, including anonymous usage limits.
            raise MCPError(text or "Parallel tool failed")
        if not text:
            raise MCPError("Parallel returned no text content")
        return text


async def call_tool(name, arguments):
    """Bound discovery, execution and stream reading by one total deadline."""
    return await asyncio.wait_for(_call_tool(name, arguments), timeout=TIMEOUT)
