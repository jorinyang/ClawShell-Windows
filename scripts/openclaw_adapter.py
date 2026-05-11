#!/usr/bin/env python3
"""
ClawShell Local — OpenClaw / Wukong Adapter v2.0
==================================================
Auto-integrates ClawShell Edge Client with existing
OpenClaw (.real/.openclaw) or Wukong runtime.

Actions performed:
  1. Register clawshell-mcp in Wukong mcpServerConfig.json
  2. Configure EventBus path to ~/.real/eventbus/
  3. Add clawshell-edge to cron_tasks.json
  4. Configure dual-channel (MCP + FileSystem)
  5. Create shared workspace directories
"""

import json
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger("OpenClawAdapter")


class OpenClawAdapter:
    """Adapter for OpenClaw / Wukong runtime environments."""

    def __init__(self, real_path: str = None):
        # Auto-detect .real path
        if real_path:
            self.real_path = Path(real_path)
        else:
            self.real_path = self._detect_real()

        self.user_dirs = []
        self._discover_users()

    def _detect_real(self) -> Path:
        """Auto-detect the .real runtime directory"""
        candidates = [
            Path.home() / ".real",
            Path("/mnt/c/Users") / (__import__('os').environ.get('USER', 'Aorus')) / ".real",
        ]
        for p in candidates:
            if p.exists() and (p / "eventbus").exists():
                return p
        return candidates[0]  # Default

    def _discover_users(self):
        """Find user directories in .real/users/"""
        users_dir = self.real_path / "users"
        if users_dir.exists():
            self.user_dirs = [d for d in users_dir.iterdir() if d.is_dir()]
            logger.info(f"Found {len(self.user_dirs)} Wukong users")

    def status(self) -> Dict:
        return {
            "real_path": str(self.real_path),
            "exists": self.real_path.exists(),
            "users": len(self.user_dirs),
            "eventbus": (self.real_path / "eventbus").exists(),
            "user_ids": [d.name for d in self.user_dirs],
        }

    # ═══ MCP Server Registration ═══════════════════════════

    def register_mcp_server(self, user_id: str = None) -> Dict:
        """Register clawshell-mcp in Wukong's mcpServerConfig.json"""
        results = {}
        users = [user_id] if user_id else [d.name for d in self.user_dirs]

        for uid in users:
            mcp_cfg = self.real_path / "users" / uid / ".mcp" / "mcpServerConfig.json"
            if not mcp_cfg.exists():
                results[uid] = "mcpServerConfig.json not found"
                continue

            try:
                cfg = json.loads(mcp_cfg.read_text())
                servers = cfg.get("mcpServers", {})

                if "clawshell-mcp" not in servers:
                    servers["clawshell-mcp"] = {
                        "isActive": True,
                        "name": "ClawShell MCP Bridge",
                        "type": "streamableHttp",
                        "timeout": 60,
                        "isBuiltin": False,
                        "isRemovable": True,
                        "url": "http://127.0.0.1:17655/",
                        "description": "ClawShell EventBus + TaskMarket MCP Bridge"
                    }
                    mcp_cfg.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
                    results[uid] = "registered"
                else:
                    results[uid] = "already_registered"
            except Exception as e:
                results[uid] = f"error: {e}"

        return results

    # ═══ Cron Task Registration ════════════════════════════

    def register_cron_tasks(self) -> Dict:
        """Add clawshell-edge tasks to cron_tasks.json"""
        cron_file = self.real_path / "cron_tasks.json"
        if not cron_file.exists():
            return {"status": "cron_tasks.json not found"}

        try:
            cron = json.loads(cron_file.read_text())
            tasks = cron.get("tasks", [])

            existing_names = {t.get("name") for t in tasks}
            added = 0

            new_tasks = [
                {"id": "clawshell_edge_sync", "name": "ClawShell Edge Sync",
                 "schedule": "*/5 * * * *", "script": "scripts/edge_client.py",
                 "enabled": True, "description": "每5分钟同步到ClawShell Cloud"},
                {"id": "clawshell_edge_health", "name": "ClawShell Edge Health",
                 "schedule": "*/10 * * * *", "script": "scripts/edge_client.py --health",
                 "enabled": True, "description": "每10分钟上报健康状态"},
            ]

            for t in new_tasks:
                if t["name"] not in existing_names:
                    tasks.append(t)
                    added += 1

            if added > 0:
                cron["tasks"] = tasks
                cron["last_updated"] = datetime.now().isoformat()
                cron_file.write_text(json.dumps(cron, indent=2, ensure_ascii=False))

            return {"status": "ok", "added": added, "total": len(tasks)}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    # ═══ Workspace Setup ═══════════════════════════════════

    def setup_workspace(self) -> Dict:
        """Create shared workspace directories"""
        dirs = [
            self.real_path / "workspace" / "shared" / "hermes_bridge" / "inbox",
            self.real_path / "workspace" / "shared" / "hermes_bridge" / "outbox",
            self.real_path / "workspace" / "shared" / "hermes_bridge" / "archive",
            self.real_path / "workspace" / "shared" / "scripts",
            self.real_path / "workspace" / "health_logs",
            self.real_path / "workspace" / "task_logs",
        ]

        created = []
        for d in dirs:
            if not d.exists():
                d.mkdir(parents=True, exist_ok=True)
                created.append(str(d.relative_to(self.real_path)))

        return {"created": len(created), "paths": created}

    # ═══ Full Integration ══════════════════════════════════

    def integrate_all(self, user_id: str = None) -> Dict:
        """Run full OpenClaw/Wukong integration"""
        return {
            "status": self.status(),
            "mcp": self.register_mcp_server(user_id),
            "cron": self.register_cron_tasks(),
            "workspace": self.setup_workspace(),
        }


def main():
    adapter = OpenClawAdapter()
    print(json.dumps(adapter.status(), indent=2))
    print("\nRunning integration...")
    result = adapter.integrate_all()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
