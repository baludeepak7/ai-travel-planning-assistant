import asyncio
import logging
import sys
import uuid

from langchain_mcp_adapters.client import MultiServerMCPClient

from src.config import ROOT

EXPECTED = {"weather": "get_weather_forecast", "currency": "convert_currency"}


class MCPClient:
    def __init__(self):
        self.client = MultiServerMCPClient(
            {
                name: {
                    "transport": "stdio",
                    "command": sys.executable,
                    "args": ["-m", f"src.mcp_servers.{name}_server"],
                    "cwd": str(ROOT),
                }
                for name in EXPECTED
            }
        )
        self.tools = {}
        self.status = {name: "Unavailable" for name in EXPECTED}

    async def initialize(self):
        errors = []
        for server, expected in EXPECTED.items():
            try:
                tools = await asyncio.wait_for(self.client.get_tools(server_name=server), 30)
                found = {tool.name: tool for tool in tools}
                if expected not in found:
                    raise ValueError("Expected tool missing")
                self.tools[expected] = found[expected]
                self.status[server] = "Connected"
                logging.info("[MCP] Loaded tool: %s", expected)
            except Exception:
                self.status[server] = "Unavailable"
                errors.append(server)
        if errors:
            raise RuntimeError(
                "MCP tool discovery failed: "
                + ", ".join(errors)
                + ". Check dependencies and run python scripts/verify_setup.py"
            )

    async def invoke(self, name: str, arguments: dict) -> dict:
        logging.info("[MCP] invoking=%s", name)
        try:
            # Tool-call envelope retains the MCP structuredContent in LangChain's artifact.
            message = await asyncio.wait_for(
                self.tools[name].ainvoke(
                    {"name": name, "args": arguments, "id": str(uuid.uuid4()), "type": "tool_call"}
                ),
                40,
            )
            result = message.artifact["structured_content"]
            if "result" in result and "ok" not in result:
                result = result["result"]
            if not isinstance(result.get("ok"), bool):
                raise ValueError("Invalid MCP response")
        except Exception:
            result = {"ok": False, "error": "MCP tool unavailable or returned invalid output."}
        logging.info("[MCP] %s status=%s", name, "ok" if result["ok"] else "error")
        return result
