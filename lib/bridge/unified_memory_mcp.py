#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UnifiedMemory MCP Server
将 MemOS Cloud + MemPalace 封装为标准 MCP Server，供悟空调用。
协议: JSON-RPC 2.0 over stdio
"""

import sys
import json
import threading
import logging
import pathlib

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger('UnifiedMemoryMCP')

# ── 初始化统一记忆桥 ────────────────────────────────────────────────────
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from lib.bridge.unified_memory_bridge import UnifiedMemoryBridge, get_bridge

_bridge = None

def get_memory_bridge():
    global _bridge
    if _bridge is None:
        _bridge = get_bridge()
    return _bridge

# ── MCP 协议处理 ────────────────────────────────────────────────────────

def send_response(req_id, result):
    response = {"jsonrpc": "2.0", "id": req_id, "result": result}
    sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
    sys.stdout.flush()

def send_error(req_id, code, msg):
    response = {"jsonrpc": "2.0", "id": req_id,
                 "error": {"code": code, "message": msg}}
    sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
    sys.stdout.flush()

def handle_request(req):
    method = req.get("method", "")
    req_id = req.get("id")
    params = req.get("params", {})

    bridge = get_memory_bridge()

    try:
        if method == "initialize":
            send_response(req_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "UnifiedMemory", "version": "1.0.0"}
            })

        elif method == "tools/list":
            send_response(req_id, {
                "tools": [
                    {"name": "memory_search", "description": "跨 MemOS Cloud + MemPalace 统一搜索记忆，关键词和语义双重检索", "inputSchema": {"type": "object", "properties": {"query": {"type": "string", "description": "搜索关键词"}, "limit": {"type": "integer", "description": "返回数量上限，默认10", "default": 10}}, "required": ["query"]}},
                    {"name": "memory_write", "description": "写入记忆到 MemOS Cloud + MemPalace", "inputSchema": {"type": "object", "properties": {"key": {"type": "string", "description": "记忆标识键"}, "value": {"type": "string", "description": "记忆内容"}, "tags": {"type": "array", "items": {"type": "string"}, "description": "标签列表"}}, "required": ["key", "value"]}},
                    {"name": "memory_read", "description": "读取单条记忆", "inputSchema": {"type": "object", "properties": {"key": {"type": "string", "description": "记忆标识键"}}, "required": ["key"]}},
                    {"name": "memory_delete", "description": "删除记忆", "inputSchema": {"type": "object", "properties": {"memory_id": {"type": "string", "description": "记忆ID"}}, "required": ["memory_id"]}},
                    {"name": "memory_stats", "description": "获取记忆统计", "inputSchema": {"type": "object", "properties": {}}}
                ]
            })

        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})

            if tool_name == "memory_search":
                results = bridge.search_memory(tool_args.get("query", ""), tool_args.get("limit", 10))
                send_response(req_id, {"content": [{"type": "text", "text": json.dumps(results, ensure_ascii=False)}]})

            elif tool_name == "memory_write":
                result = bridge.write_memory(
                    tool_args.get("key", ""),
                    tool_args.get("value", ""),
                    tool_args.get("tags", []),
                    tool_args.get("visibility", "private")
                )
                send_response(req_id, {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]})

            elif tool_name == "memory_read":
                result = bridge.read_memory(tool_args.get("key", ""))
                send_response(req_id, {"content": [{"type": "text", "text": result or ""}]})

            elif tool_name == "memory_delete":
                ok = bridge.delete_memory(tool_args.get("memory_id", ""))
                send_response(req_id, {"content": [{"type": "text", "text": json.dumps({"success": ok})}]})

            elif tool_name == "memory_stats":
                stats = bridge.get_stats()
                send_response(req_id, {"content": [{"type": "text", "text": json.dumps(stats, ensure_ascii=False)}]})

            else:
                send_error(req_id, -32601, f"Unknown tool: {tool_name}")

        elif method == "notifications/initialized":
            pass  # 忽略

        else:
            send_error(req_id, -32601, f"Unknown method: {method}")

    except Exception as e:
        logger.error(f"Handle request error: {e}")
        send_error(req_id, -32603, str(e))

def main_loop():
    """标准输入循环，处理 JSON-RPC 请求"""
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            req = json.loads(line.strip())
            handle_request(req)
        except json.JSONDecodeError:
            continue
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            break

if __name__ == "__main__":
    main_loop()
