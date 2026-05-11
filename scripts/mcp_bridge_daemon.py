#!/usr/bin/env python3
"""
ClawShell MCP HTTP Bridge Daemon
================================
Listens on the configured port and provides MCP JSON-RPC tools
for EventBus publish/subscribe/query/stats.

Port: From ~/.real/.mcp/http-bridge-port.json (default 17655)

Tools provided:
  - eventbus_publish: Publish event to EventBus
  - eventbus_subscribe: Subscribe to event patterns
  - eventbus_query: Query past events
  - eventbus_stats: Get EventBus statistics
  - health_check: Health check endpoint
"""

import os
import sys
import json
import time
import signal
import socket
import logging
import threading
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional

# ── Path setup ──────────────────────────────────────────────
# On WSL, the Wukong runtime is at the Windows-side .real
_win_home = Path("/mnt/c") / "Users" / os.environ.get("USER", os.environ.get("USERNAME", "Aorus"))
REAL_BASE = Path(os.environ.get("REAL_BASE", str(_win_home / ".real")))
CLAWSHELL_SRC = Path(os.environ.get("CLAWSHELL_ROOT", str(_win_home / ".ClawShell")))
sys.path.insert(0, str(CLAWSHELL_SRC))

# ── Configuration ───────────────────────────────────────────
def load_port():
    port_file = REAL_BASE / ".mcp" / "http-bridge-port.json"
    try:
        if port_file.exists():
            return json.loads(port_file.read_text())
    except:
        pass
    return 17655

BRIDGE_PORT = load_port()
BRIDGE_HOST = "127.0.0.1"

# ── Logging ─────────────────────────────────────────────────
LOG_DIR = REAL_BASE / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [MCP-Bridge] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "mcp_bridge.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("mcp_bridge")

# ── EventBus Integration ────────────────────────────────────
EVENTBUS_DIR = REAL_BASE / "eventbus" / "events"
EVENTBUS_DIR.mkdir(parents=True, exist_ok=True)

stats = {
    "events_published": 0,
    "events_queried": 0,
    "subscriptions": 0,
    "uptime_start": datetime.now().isoformat()
}


def publish_event(event_type: str, payload: Dict, source: str = "mcp_bridge") -> str:
    """Publish an event to the file-system EventBus"""
    today = datetime.now().strftime("%Y-%m-%d")
    ts = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    event_id = f"{ts}_{source}_{event_type.replace('.', '_')}"

    event_dir = EVENTBUS_DIR / today
    event_dir.mkdir(parents=True, exist_ok=True)

    event_file = event_dir / f"{event_id}.json"
    event_data = {
        "event_id": event_id,
        "event_type": event_type,
        "source": source,
        "timestamp": datetime.now().isoformat(),
        "payload": payload,
        "tags": event_type.split(".")
    }

    event_file.write_text(json.dumps(event_data, ensure_ascii=False, indent=2))
    stats["events_published"] += 1
    logger.info(f"Published: {event_type} -> {event_file.name}")
    return event_id


def query_events(pattern: str = None, limit: int = 20) -> list:
    """Query recent events from EventBus"""
    events = []
    for date_dir in sorted(EVENTBUS_DIR.iterdir(), reverse=True):
        if not date_dir.is_dir():
            continue
        for event_file in sorted(date_dir.iterdir(), reverse=True):
            if event_file.suffix != ".json":
                continue
            try:
                ev = json.loads(event_file.read_text())
                if pattern is None or pattern in ev.get("event_type", ""):
                    events.append({
                        "event_id": ev.get("event_id"),
                        "event_type": ev.get("event_type"),
                        "source": ev.get("source"),
                        "timestamp": ev.get("timestamp"),
                    })
            except:
                pass
            if len(events) >= limit:
                break
        if len(events) >= limit:
            break

    stats["events_queried"] += 1
    return events


def get_stats() -> Dict:
    """Get EventBus and bridge statistics"""
    event_count = 0
    for date_dir in EVENTBUS_DIR.iterdir():
        if date_dir.is_dir():
            event_count += len(list(date_dir.glob("*.json")))

    return {
        **stats,
        "total_events": event_count,
        "eventbus_path": str(EVENTBUS_DIR),
        "bridge_port": BRIDGE_PORT,
    }


# ── JSON-RPC Handler ────────────────────────────────────────
class MCPRequestHandler(BaseHTTPRequestHandler):

    def _send_json(self, data: Dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            request = json.loads(body)

            method = request.get("method", "")
            params = request.get("params", {})
            req_id = request.get("id", "")

            if method == "tools/list":
                result = self._handle_tools_list()
            elif method == "tools/call":
                tool_name = params.get("name", "")
                arguments = params.get("arguments", {})
                result = self._handle_tool_call(tool_name, arguments)
            elif method == "health/check":
                result = {"status": "healthy", "port": BRIDGE_PORT}
            else:
                result = {"error": f"Unknown method: {method}"}

            self._send_json({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": result
            })

        except Exception as e:
            logger.error(f"Request error: {e}")
            self._send_json({
                "jsonrpc": "2.0",
                "error": str(e)
            }, 500)

    def do_GET(self):
        """Health check endpoint"""
        if self.path == "/health":
            self._send_json({
                "status": "ok",
                "bridge": "clawshell-mcp",
                "port": BRIDGE_PORT,
                "uptime": get_stats()
            })
        else:
            self._send_json({"error": "Not found"}, 404)

    def _handle_tools_list(self) -> Dict:
        return {
            "tools": [
                {
                    "name": "eventbus_publish",
                    "description": "Publish an event to the ClawShell EventBus",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "event_type": {"type": "string"},
                            "payload": {"type": "object"},
                            "source": {"type": "string", "default": "mcp_bridge"}
                        },
                        "required": ["event_type", "payload"]
                    }
                },
                {
                    "name": "eventbus_query",
                    "description": "Query recent events from the EventBus",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string"},
                            "limit": {"type": "integer", "default": 20}
                        }
                    }
                },
                {
                    "name": "eventbus_stats",
                    "description": "Get EventBus statistics",
                    "inputSchema": {"type": "object", "properties": {}}
                },
                {
                    "name": "health_check",
                    "description": "Check bridge health",
                    "inputSchema": {"type": "object", "properties": {}}
                }
            ]
        }

    def _handle_tool_call(self, tool_name: str, args: Dict) -> Any:
        if tool_name == "eventbus_publish":
            event_id = publish_event(
                event_type=args.get("event_type", "unknown"),
                payload=args.get("payload", {}),
                source=args.get("source", "mcp_bridge")
            )
            return {"event_id": event_id, "status": "published"}

        elif tool_name == "eventbus_query":
            events = query_events(
                pattern=args.get("pattern"),
                limit=args.get("limit", 20)
            )
            return {"events": events, "count": len(events)}

        elif tool_name == "eventbus_stats":
            return get_stats()

        elif tool_name == "health_check":
            return {"status": "healthy", "port": BRIDGE_PORT}

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    def log_message(self, format, *args):
        logger.debug(f"HTTP {args}")


# ── Main ────────────────────────────────────────────────────
def main():
    server = HTTPServer((BRIDGE_HOST, BRIDGE_PORT), MCPRequestHandler)
    logger.info(f"ClawShell MCP Bridge started on {BRIDGE_HOST}:{BRIDGE_PORT}")

    def shutdown(sig, frame):
        logger.info("Shutting down...")
        server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()
