#!/usr/bin/env python3
"""
ClawShell Local — Hermes Agent Adapter v2.0
=============================================
Auto-integrates ClawShell Edge Client with Hermes Agent.

Actions performed:
  1. Register clawshell-edge skill in ~/.hermes/skills/
  2. Configure memory provider for Cloud API
  3. Register cron jobs via hermes cron create
  4. Update config.yaml with ClawShell integration settings
  5. ActionReferenceHook — inject cloud insights before agent actions (v1.1)
"""

import json
import yaml
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger("HermesAdapter")

# Action reference file for Hermes agent context
HERMES_REFERENCE_FILE = "clawshell_action_reference.md"


class HermesAdapter:
    """Adapter for Hermes Agent environment."""

    def __init__(self, hermes_home: str = None):
        self.hermes_home = Path(hermes_home or Path.home() / ".hermes")
        self.config_file = self.hermes_home / "config.yaml"
        self.skills_dir = self.hermes_home / "skills"
        self.env_file = self.hermes_home / ".env"

    def status(self) -> Dict:
        return {
            "hermes_home": str(self.hermes_home),
            "exists": self.hermes_home.exists(),
            "config": self.config_file.exists(),
            "skills": len(list(self.skills_dir.rglob("SKILL.md"))) if self.skills_dir.exists() else 0,
            "skills_dir": str(self.skills_dir),
        }

    # ═══ Skill Registration ════════════════════════════════

    def register_skill(self) -> Dict:
        """Install clawshell-edge skill for Hermes"""
        skill_dir = self.skills_dir / "clawshell" / "clawshell-edge"
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_content = """---
name: clawshell-edge
description: "ClawShell 2.0 Edge Client integration — sync tasks, events, and health with Cloud"
version: 2.0.0
author: ClawShell
metadata:
  hermes:
    tags: [clawshell, edge, cloud-sync, task-market]
    platforms: [cli]
---

# ClawShell Edge Integration

This skill connects Hermes Agent to the ClawShell 2.0 cloud-edge architecture.

## Commands

- `clawshell-edge start` — Start edge client with cloud sync
- `clawshell-edge status` — Check connection and sync status
- `clawshell-edge push` — Push local events to cloud
- `clawshell-edge pull` — Pull cloud tasks and updates
"""

        (skill_dir / "SKILL.md").write_text(skill_content)
        return {"status": "installed", "path": str(skill_dir)}

    # ═══ Config Integration ════════════════════════════════

    def update_config(self, cloud_url: str = "http://localhost:8000") -> Dict:
        """Update Hermes config.yaml with ClawShell settings"""
        if not self.config_file.exists():
            return {"status": "config not found"}

        try:
            with open(self.config_file) as f:
                cfg = yaml.safe_load(f) or {}

            # Add clawshell section
            cfg.setdefault("clawshell", {})
            cfg["clawshell"].update({
                "enabled": True,
                "cloud_url": cloud_url,
                "edge_token": cfg["clawshell"].get("edge_token", "auto-generated"),
            })

            with open(self.config_file, "w") as f:
                yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)

            return {"status": "updated", "cloud_url": cloud_url}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    # ═══ Env Setup ═════════════════════════════════════════

    def update_env(self, cloud_url: str = None, edge_token: str = None) -> Dict:
        """Update Hermes .env with ClawShell environment variables"""
        if not self.env_file.exists():
            self.env_file.write_text("# ClawShell Edge Configuration\n")

        lines = self.env_file.read_text().split("\n")
        updated = {}

        vars_to_set = {
            "CLAWSHELL_CLOUD_URL": cloud_url or "http://localhost:8000",
            "CLAWSHELL_EDGE_TOKEN": edge_token or "",
        }

        for var, val in vars_to_set.items():
            if val:
                found = False
                for i, line in enumerate(lines):
                    if line.startswith(f"{var}="):
                        lines[i] = f"{var}={val}"
                        found = True
                        break
                if not found:
                    lines.append(f"{var}={val}")
                updated[var] = val

        self.env_file.write_text("\n".join(lines))
        return {"status": "updated", "vars": updated}

    # ═══ ActionReferenceHook (v1.1) ═════════════════════════

    def inject_action_reference(self) -> Dict:
        """Inject cloud insights as Hermes agent context.

        Reads cloud_insights.json from edge_sync_daemon and writes
        a markdown reference file in ~/.hermes/ that Hermes agent
        can include as context before action execution.

        This implements: "端脑在任意行动执行前需主动拉取云端信息作为行动参考"
        """
        # Read from edge_sync_daemon cache (at .real or .hermes)
        ref_dirs = [
            self.hermes_home,
            Path.home() / ".real",
            Path(f"/mnt/c/Users/{Path.home().name}") / ".real",
        ]

        insights_data = []
        broadcasts_data = []
        available = False

        for d in ref_dirs:
            insights_file = d / "cloud_insights.json"
            if insights_file.exists():
                try:
                    data = json.loads(insights_file.read_text())
                    if isinstance(data, list):
                        insights_data = data
                    elif isinstance(data, dict):
                        insights_data = data.get("insights", [])
                    available = True
                    break
                except:
                    pass

        for d in ref_dirs:
            broadcasts_file = d / "cloud_broadcasts.json"
            if broadcasts_file.exists():
                try:
                    data = json.loads(broadcasts_file.read_text())
                    if isinstance(data, dict):
                        broadcasts_data = data.get("broadcasts", [])
                    available = True
                    break
                except:
                    pass

        ref_file = self.hermes_home / HERMES_REFERENCE_FILE

        lines = [
            "# ClawShell Cloud Action Reference (Hermes)",
            f"> Generated: {datetime.now().isoformat()}",
            f"> Source: Cloud Hub (一云多端云边协同分布式神经系统)",
            "",
        ]

        if not available:
            lines.append("⚠️ **Cloud Hub unreachable** — autonomous mode active.")
            lines.append("Using local MemPalace + MemOS Local for context.")
            ref_file.write_text("\n".join(lines))
            return {"status": "offline", "file": str(ref_file)}

        if insights_data:
            lines.append("## 📊 Cloud Insights")
            lines.append("")
            for i, insight in enumerate(insights_data[:5], 1):
                lines.append(f"### {i}. {insight.get('title', 'Insight ' + str(i))}")
                lines.append(f"Category: {insight.get('category', 'N/A')} | "
                           f"Confidence: {insight.get('confidence', 0):.0%}")
                lines.append(f"{insight.get('description', '')}")
                if insight.get('suggested_action'):
                    lines.append(f"→ {insight['suggested_action']}")
                lines.append("")

        if broadcasts_data:
            lines.append("## 📡 Cloud Broadcasts")
            lines.append("")
            for bc in broadcasts_data[:3]:
                lines.append(f"- **[{bc.get('category', 'N/A')}]** {bc.get('title', '')}")
            lines.append("")

        lines.append("---")
        lines.append("*Auto-generated. Include as pre-action context.*")

        ref_file.write_text("\n".join(lines))
        return {
            "status": "injected",
            "insights_count": len(insights_data),
            "broadcasts_count": len(broadcasts_data),
            "file": str(ref_file),
        }

    # ═══ Full Integration ══════════════════════════════════

    def integrate_all(self, cloud_url: str = None) -> Dict:
        """Run full Hermes integration"""
        result = {
            "status": self.status(),
            "skill": self.register_skill(),
            "config": self.update_config(cloud_url),
            "env": self.update_env(cloud_url),
        }
        # v1.1: Inject action reference
        try:
            result["action_reference"] = self.inject_action_reference()
        except Exception as e:
            result["action_reference"] = {"status": "error", "reason": str(e)}
        return result


def main():
    adapter = HermesAdapter()
    print(json.dumps(adapter.status(), indent=2))
    result = adapter.integrate_all()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
