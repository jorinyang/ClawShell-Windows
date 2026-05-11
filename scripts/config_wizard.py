#!/usr/bin/env python3
"""
ClawShell 2.0 — Configuration Wizard
======================================
Interactive setup: Cloud URL, Edge Token, Node ID.
Generates config.yaml for edge client.
"""

import os
import sys
import json
import socket
from pathlib import Path
from typing import Dict


DEFAULT_CLOUD_URL = os.environ.get("CLAWSHELL_CLOUD_URL", "http://localhost:8000")
DEFAULT_NODE_ID = socket.gethostname()
CONFIG_DIR = Path.home() / ".clawshell_edge"
CONFIG_FILE = CONFIG_DIR / "config.yaml"


def _test_cloud_connection(url: str, token: str = "") -> Dict:
    """Test connectivity to Cloud API"""
    import urllib.request
    result = {"reachable": False, "version": None, "error": None}
    try:
        req = urllib.request.Request(f"{url.rstrip('/')}/")
        if token:
            req.add_header("X-Edge-Token", token)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            result["reachable"] = True
            result["version"] = data.get("version", "unknown")
            result["status"] = data.get("status", "unknown")
    except Exception as e:
        result["error"] = str(e)
    return result


def run_wizard():
    """Interactive configuration wizard"""
    print("\n" + "=" * 60)
    print("  ClawShell 2.0 — Configuration Wizard")
    print("=" * 60)

    # Step 1: Cloud URL
    print(f"\n1️⃣  Cloud Server URL")
    print(f"   Enter the URL of your ClawShell Cloud server.")
    cloud_url = input(f"   Cloud URL [{DEFAULT_CLOUD_URL}]: ").strip()
    if not cloud_url:
        cloud_url = DEFAULT_CLOUD_URL

    # Test connection
    print(f"   Testing connection to {cloud_url}...")
    result = _test_cloud_connection(cloud_url)
    if result["reachable"]:
        print(f"   ✅ Connected! Version: {result['version']}, Status: {result['status']}")
    else:
        print(f"   ⚠️  Warning: {result.get('error', 'Connection failed')}")
        print(f"   Continuing anyway — you can fix this later in {CONFIG_FILE}")

    # Step 2: Edge Token
    print(f"\n2️⃣  Edge Authentication Token")
    print(f"   Enter the token provided by your Cloud server admin.")
    edge_token = input(f"   Edge Token (leave empty to auto-generate): ").strip()

    # Step 3: Node ID
    print(f"\n3️⃣  Node Identity")
    print(f"   Unique identifier for this edge node.")
    node_id = input(f"   Node ID [{DEFAULT_NODE_ID}]: ").strip()
    if not node_id:
        node_id = DEFAULT_NODE_ID

    # Step 4: Node Name
    node_name = input(f"   Node Name (friendly name) [{node_id}]: ").strip()
    if not node_name:
        node_name = node_id

    # Step 5: Sync Interval
    print(f"\n4️⃣  Sync Settings")
    batch_interval = input(f"   Cloud sync interval in seconds [5]: ").strip()
    if not batch_interval:
        batch_interval = "5"

    # Generate config
    config = {
        "node_id": node_id,
        "node_name": node_name,
        "cloud_url": cloud_url,
        "edge_token": edge_token or "auto-generated-on-first-run",
        "sync": {
            "batch_interval": int(batch_interval),
            "offline_queue_file": "~/.real/offline_events.json",
        },
        "services": {
            "mcp_bridge_port": 17655,
            "browser_runtime_port": 4240,
        },
        "created_at": __import__("datetime").datetime.now().isoformat(),
    }

    # Save
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    import yaml
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    print(f"\n✅ Configuration saved to: {CONFIG_FILE}")
    print(f"\n   Node ID:    {node_id}")
    print(f"   Cloud URL:  {cloud_url}")
    print(f"   Sync every: {batch_interval}s")
    print(f"\n   To start the edge client:")
    print(f"     clawshell-edge start")
    print(f"   To check status:")
    print(f"     clawshell-edge status")


def main():
    run_wizard()


if __name__ == "__main__":
    main()
