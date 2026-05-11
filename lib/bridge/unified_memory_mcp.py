     1|#!/usr/bin/env python3
     2|# -*- coding: utf-8 -*-
     3|"""
     4|UnifiedMemory MCP Server
     5|将 MemOS Cloud + MemPalace 封装为标准 MCP Server，供悟空调用。
     6|协议: JSON-RPC 2.0 over stdio
     7|"""
     8|
     9|import sys
    10|import json
    11|import threading
    12|import logging
    13|import pathlib
    14|
    15|logging.basicConfig(level=logging.INFO, format='%(message)s')
    16|logger = logging.getLogger('UnifiedMemoryMCP')
    17|
    18|# ── 初始化统一记忆桥 ────────────────────────────────────────────────────
    19|sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
    20|from lib.bridge.unified_memory_bridge import UnifiedMemoryBridge, get_bridge
    21|
    22|_bridge = None
    23|
    24|def get_memory_bridge():
    25|    global _bridge
    26|    if _bridge is None:
    27|        _bridge = get_bridge()
    28|    return _bridge
    29|
    30|# ── MCP 协议处理 ────────────────────────────────────────────────────────
    31|
    32|def send_response(req_id, result):
    33|    response = {"jsonrpc": "2.0", "id": req_id, "result": result}
    34|    sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
    35|    sys.stdout.flush()
    36|
    37|def send_error(req_id, code, msg):
    38|    response = {"jsonrpc": "2.0", "id": req_id,
    39|                 "error": {"code": code, "message": msg}}
    40|    sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
    41|    sys.stdout.flush()
    42|
    43|def handle_request(req):
    44|    method = req.get("method", "")
    45|    req_id = req.get("id")
    46|    params = req.get("params", {})
    47|
    48|    bridge = get_memory_bridge()
    49|
    50|    try:
    51|        if method == "initialize":
    52|            send_response(req_id, {
    53|                "protocolVersion": "2024-11-05",
    54|                "capabilities": {"tools": {}},
    55|                "serverInfo": {"name": "UnifiedMemory", "version": "1.1.0"}
    56|            })
    57|
    58|        elif method == "tools/list":
    59|            send_response(req_id, {
    60|                "tools": [
    61|                    {"name": "memory_search", "description": "跨 MemOS Cloud + MemPalace 统一搜索记忆，关键词和语义双重检索", "inputSchema": {"type": "object", "properties": {"query": {"type": "string", "description": "搜索关键词"}, "limit": {"type": "integer", "description": "返回数量上限，默认10", "default": 10}}, "required": ["query"]}},
    62|                    {"name": "memory_write", "description": "写入记忆到 MemOS Cloud + MemPalace", "inputSchema": {"type": "object", "properties": {"key": {"type": "string", "description": "记忆标识键"}, "value": {"type": "string", "description": "记忆内容"}, "tags": {"type": "array", "items": {"type": "string"}, "description": "标签列表"}}, "required": ["key", "value"]}},
    63|                    {"name": "memory_read", "description": "读取单条记忆", "inputSchema": {"type": "object", "properties": {"key": {"type": "string", "description": "记忆标识键"}}, "required": ["key"]}},
    64|                    {"name": "memory_delete", "description": "删除记忆", "inputSchema": {"type": "object", "properties": {"memory_id": {"type": "string", "description": "记忆ID"}}, "required": ["memory_id"]}},
    65|                    {"name": "memory_stats", "description": "获取记忆统计", "inputSchema": {"type": "object", "properties": {}}}
    66|                ]
    67|            })
    68|
    69|        elif method == "tools/call":
    70|            tool_name = params.get("name", "")
    71|            tool_args = params.get("arguments", {})
    72|
    73|            if tool_name == "memory_search":
    74|                results = bridge.search_memory(tool_args.get("query", ""), tool_args.get("limit", 10))
    75|                send_response(req_id, {"content": [{"type": "text", "text": json.dumps(results, ensure_ascii=False)}]})
    76|
    77|            elif tool_name == "memory_write":
    78|                result = bridge.write_memory(
    79|                    tool_args.get("key", ""),
    80|                    tool_args.get("value", ""),
    81|                    tool_args.get("tags", []),
    82|                    tool_args.get("visibility", "private")
    83|                )
    84|                send_response(req_id, {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]})
    85|
    86|            elif tool_name == "memory_read":
    87|                result = bridge.read_memory(tool_args.get("key", ""))
    88|                send_response(req_id, {"content": [{"type": "text", "text": result or ""}]})
    89|
    90|            elif tool_name == "memory_delete":
    91|                ok = bridge.delete_memory(tool_args.get("memory_id", ""))
    92|                send_response(req_id, {"content": [{"type": "text", "text": json.dumps({"success": ok})}]})
    93|
    94|            elif tool_name == "memory_stats":
    95|                stats = bridge.get_stats()
    96|                send_response(req_id, {"content": [{"type": "text", "text": json.dumps(stats, ensure_ascii=False)}]})
    97|
    98|            else:
    99|                send_error(req_id, -32601, f"Unknown tool: {tool_name}")
   100|
   101|        elif method == "notifications/initialized":
   102|            pass  # 忽略
   103|
   104|        else:
   105|            send_error(req_id, -32601, f"Unknown method: {method}")
   106|
   107|    except Exception as e:
   108|        logger.error(f"Handle request error: {e}")
   109|        send_error(req_id, -32603, str(e))
   110|
   111|def main_loop():
   112|    """标准输入循环，处理 JSON-RPC 请求"""
   113|    while True:
   114|        try:
   115|            line = sys.stdin.readline()
   116|            if not line:
   117|                break
   118|            req = json.loads(line.strip())
   119|            handle_request(req)
   120|        except json.JSONDecodeError:
   121|            continue
   122|        except Exception as e:
   123|            logger.error(f"Main loop error: {e}")
   124|            break
   125|
   126|if __name__ == "__main__":
   127|    main_loop()
   128|