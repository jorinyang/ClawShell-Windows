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
  6. ActionReferenceHook — inject cloud insights before agent actions (v1.1)
"""

import json
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List

logger = logging.getLogger("OpenClawAdapter")

# Action reference file — agent reads before executing
ACTION_REFERENCE_FILE = "clawshell_action_reference.md"

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

    # ═══ ActionReferenceHook (v1.1) ═════════════════════════
    # "端脑在任意行动执行前需主动拉取云端信息作为行动参考"

    def get_action_reference(self) -> Dict:
        """Read cloud insights and broadcasts as action reference.

        Reads files generated by edge_sync_daemon:
          - cloud_insights.json   (from pull_insights)
          - cloud_broadcasts.json (from pull_broadcasts)
        """
        reference = {"insights": [], "broadcasts": [], "best_practices": [],
                     "updated_at": None, "available": False}

        # Read insights cache
        insights_file = self.real_path / "cloud_insights.json"
        if insights_file.exists():
            try:
                insights = json.loads(insights_file.read_text())
                if isinstance(insights, list):
                    reference["insights"] = insights
                elif isinstance(insights, dict):
                    reference["insights"] = insights.get("insights", [])
                reference["available"] = True
            except:
                pass

        # Read broadcasts cache
        broadcasts_file = self.real_path / "cloud_broadcasts.json"
        if broadcasts_file.exists():
            try:
                broadcasts = json.loads(broadcasts_file.read_text())
                if isinstance(broadcasts, dict):
                    reference["broadcasts"] = broadcasts.get("broadcasts", [])
                reference["available"] = True
            except:
                pass

        if reference["available"]:
            reference["updated_at"] = datetime.fromtimestamp(
                insights_file.stat().st_mtime).isoformat()

        return reference

    def inject_action_reference(self) -> Dict:
        """Inject cloud insights as agent action reference context.

        Writes a markdown file that agents can include in their context
        before executing any task. This implements:
        "端脑在任意行动执行前需主动拉取云端信息作为行动参考"
        """
        ref = self.get_action_reference()
        workspace = self.real_path / "workspace" / "shared"
        ref_file = workspace / ACTION_REFERENCE_FILE
        workspace.mkdir(parents=True, exist_ok=True)

        lines = [
            "# ClawShell Cloud Action Reference",
            f"> Generated: {datetime.now().isoformat()}",
            f"> Source: Cloud Hub (一云多端云边协同分布式神经系统)",
            "",
        ]

        if not ref["available"]:
            lines.append("⚠️ **Cloud Hub unreachable** — operating in autonomous mode.")
            lines.append("Using local knowledge and cached skills only.")
            ref_file.write_text("\n".join(lines))
            return {"status": "offline", "file": str(ref_file)}

        # Cloud Insights section
        if ref["insights"]:
            lines.append("## 📊 Cloud Insights (行动参考)")
            lines.append(f"_Last synced: {ref['updated_at']}_")
            lines.append("")
            for i, insight in enumerate(ref["insights"][:5], 1):
                lines.append(f"### {i}. {insight.get('title', 'Insight')}")
                lines.append(f"- **Category**: {insight.get('category', 'N/A')}")
                lines.append(f"- **Confidence**: {insight.get('confidence', 0):.0%}")
                lines.append(f"- **Description**: {insight.get('description', '')}")
                if insight.get('suggested_action'):
                    lines.append(f"- **Suggested**: {insight['suggested_action']}")
                lines.append("")

        # Broadcasts section
        if ref["broadcasts"]:
            lines.append("## 📡 Cloud Broadcasts")
            lines.append("")
            for bc in ref["broadcasts"][:3]:
                lines.append(f"- **[{bc.get('category', 'N/A')}]** {bc.get('title', '')}")
                lines.append(f"  {bc.get('content', '')[:200]}")
            lines.append("")

        # Best Practices section
        if ref.get("best_practices"):
            lines.append("## ⭐ Best Practices (云端最佳实践)")
            lines.append("")
            for bp in ref["best_practices"][:3]:
                lines.append(f"- **{bp.get('name', '')}** ({bp.get('category', '')})")
                lines.append(f"  {bp.get('description', '')[:150]}")
            lines.append("")

        lines.append("---")
        lines.append("*This reference is auto-generated by ClawShell Edge Sync Daemon.*")
        lines.append("*Use as context for action planning. Cloud Hub offline → autonomous mode.*")

        ref_file.write_text("\n".join(lines))
        return {
            "status": "injected",
            "insights_count": len(ref["insights"]),
            "broadcasts_count": len(ref["broadcasts"]),
            "file": str(ref_file),
        }

    # ═══ Full Integration ══════════════════════════════════

    def integrate_all(self, user_id: str = None) -> Dict:
        """Run full OpenClaw/Wukong integration"""
        result = {
            "status": self.status(),
            "mcp": self.register_mcp_server(user_id),
            "cron": self.register_cron_tasks(),
            "workspace": self.setup_workspace(),
        }
        # v1.1: Also inject initial action reference
        try:
            result["action_reference"] = self.inject_action_reference()
        except Exception as e:
            result["action_reference"] = {"status": "error", "reason": str(e)}
        return result


def main():
    adapter = OpenClawAdapter()
    print(json.dumps(adapter.status(), indent=2))
    print("\nRunning integration...")
    result = adapter.integrate_all()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
