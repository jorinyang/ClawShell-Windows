#!/usr/bin/env python3
"""
ClawShell 2.0 — Environment Detector
=====================================
Auto-detect: OS, OpenClaw, Hermes, Wukong, Python/Node/Bun versions.
Generates a comprehensive environment report for the installer.
"""

import os
import sys
import json
import platform
import socket
import subprocess
from pathlib import Path
from typing import Dict, List, Optional


class EnvironmentDetector:
    """Detect and report the local environment for ClawShell installation."""

    def __init__(self):
        self.home = Path.home()
        self.results = {}

    def detect_all(self) -> Dict:
        """Run all detection probes and return a complete report."""
        self.results = {
            "detected_at": __import__("datetime").datetime.now().isoformat(),
            "hostname": socket.gethostname(),
            "os": self._detect_os(),
            "python": self._detect_python(),
            "node": self._detect_node(),
            "bun": self._detect_bun(),
            "openclaw": self._detect_openclaw(),
            "hermes": self._detect_hermes(),
            "wukong": self._detect_wukong(),
            "paths": self._detect_paths(),
            "recommendations": [],
        }
        self._generate_recommendations()
        return self.results

    # ── OS Detection ──────────────────────────────────────

    def _detect_os(self) -> Dict:
        """Detect OS type and WSL status."""
        info = {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "is_wsl": False,
            "windows_home": None,
        }

        # WSL detection
        if info["system"] == "Linux":
            # Check /proc/version for Microsoft
            try:
                with open("/proc/version") as f:
                    if "microsoft" in f.read().lower() or "wsl" in f.read().lower():
                        info["is_wsl"] = True
            except:
                pass

            # Check for WSL interop
            if Path("/run/WSL").exists() or "WSL_DISTRO_NAME" in os.environ:
                info["is_wsl"] = True

        # WSL Windows home detection
        if info["is_wsl"]:
            user = os.environ.get("USER", os.environ.get("USERNAME", ""))
            win_home = Path(f"/mnt/c/Users/{user}")
            if win_home.exists():
                info["windows_home"] = str(win_home)

        # macOS
        if info["system"] == "Darwin":
            info["is_macos"] = True

        return info

    # ── Python Detection ──────────────────────────────────

    def _detect_python(self) -> Dict:
        py = {
            "version": sys.version.split()[0],
            "executable": sys.executable,
            "in_venv": sys.prefix != sys.base_prefix,
            "venv_path": sys.prefix if sys.prefix != sys.base_prefix else None,
        }

        # Check Hermes venv
        hermes_venv = self.home / ".hermes" / "hermes-agent" / "venv" / "bin" / "python3"
        if hermes_venv.exists():
            py["hermes_venv"] = str(hermes_venv)
            try:
                r = subprocess.run([str(hermes_venv), "--version"], capture_output=True, text=True, timeout=5)
                py["hermes_venv_version"] = r.stdout.strip()
            except:
                pass

        return py

    # ── Node.js Detection ─────────────────────────────────

    def _detect_node(self) -> Dict:
        node = {"installed": False}

        for name in ["node", "nodejs"]:
            try:
                r = subprocess.run([name, "--version"], capture_output=True, text=True, timeout=5)
                if r.returncode == 0:
                    node["installed"] = True
                    node["version"] = r.stdout.strip()
                    node["command"] = name
                    break
            except FileNotFoundError:
                pass

        # Check Windows-side Node from WSL
        if not node["installed"] and self.results.get("os", {}).get("is_wsl"):
            win_home = self.results["os"].get("windows_home")
            if win_home:
                node_path = Path(win_home) / ".real" / ".bin" / "node" / "node.exe"
                if node_path.exists():
                    node["installed"] = True
                    node["version"] = "windows-side"
                    node["path"] = str(node_path)

        return node

    # ── Bun Detection ─────────────────────────────────────

    def _detect_bun(self) -> Dict:
        bun = {"installed": False}

        try:
            r = subprocess.run(["bun", "--version"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                bun["installed"] = True
                bun["version"] = r.stdout.strip()
        except FileNotFoundError:
            pass

        # Windows-side bun
        if not bun["installed"] and self.results.get("os", {}).get("is_wsl"):
            win_home = self.results["os"].get("windows_home")
            if win_home:
                bun_path = Path(win_home) / ".real" / ".bin" / "bun.exe"
                if bun_path.exists():
                    bun["installed"] = True
                    bun["version"] = "windows-side"
                    bun["path"] = str(bun_path)

        return bun

    # ── OpenClaw Detection ────────────────────────────────

    def _detect_openclaw(self) -> Dict:
        oc = {"found": False, "paths": [], "type": None}

        candidates = [
            self.home / ".openclaw",
            self.home / ".real",
        ]

        # WSL: check Windows side
        win_home = self.results.get("os", {}).get("windows_home")
        if win_home:
            candidates.extend([
                Path(win_home) / ".real",
                Path(win_home) / ".openclaw",
                Path(win_home) / ".ClawShell",
            ])

        for p in candidates:
            if p.exists():
                oc["paths"].append(str(p))

        if oc["paths"]:
            oc["found"] = True
            # Determine type
            for p_str in oc["paths"]:
                p = Path(p_str)
                if (p / "eventbus").exists() and (p / "users").exists():
                    oc["type"] = "wukong"  # Has users + eventbus = Wukong runtime
                    oc["primary_path"] = p_str
                    break
            if not oc.get("type"):
                oc["type"] = "openclaw_legacy"
                oc["primary_path"] = oc["paths"][0]

        return oc

    # ── Hermes Detection ──────────────────────────────────

    def _detect_hermes(self) -> Dict:
        hm = {"found": False, "paths": []}

        candidates = [
            self.home / ".hermes",
        ]
        win_home = self.results.get("os", {}).get("windows_home")
        if win_home:
            candidates.append(Path(win_home) / ".hermes")

        for p in candidates:
            if p.exists() and (p / "config.yaml").exists():
                hm["found"] = True
                hm["paths"].append(str(p))
                hm["primary_path"] = str(p)

                # Parse config for model/provider info
                config_file = p / "config.yaml"
                try:
                    import yaml
                    with open(config_file) as f:
                        cfg = yaml.safe_load(f)
                    hm["config"] = {
                        "model": cfg.get("model", {}).get("default", "unknown"),
                        "provider": cfg.get("model", {}).get("provider", "unknown"),
                    }
                except:
                    pass
                break

        return hm

    # ── Wukong Detection ──────────────────────────────────

    def _detect_wukong(self) -> Dict:
        wk = {"found": False, "paths": [], "users": []}

        win_home = self.results.get("os", {}).get("windows_home")
        if not win_home:
            return wk

        # Check dingtalk-rewind-server
        app_data = Path(win_home) / "AppData" / "Roaming" / "dingtalk-rewind-server"
        if app_data.exists():
            wk["found"] = True
            wk["paths"].append(str(app_data))
            wk["type"] = "dingtalk-rewind-server"

        # Check .real for users
        real = Path(win_home) / ".real"
        if real.exists():
            users_dir = real / "users"
            if users_dir.exists():
                wk["users"] = [d.name for d in users_dir.iterdir() if d.is_dir()]
                wk["paths"].append(str(real))
                if not wk.get("type"):
                    wk["type"] = "openclaw-real"

        return wk

    # ── Critical Paths ────────────────────────────────────

    def _detect_paths(self) -> Dict:
        paths = {
            "home": str(self.home),
            "clawshell_source": None,
            "clawshell_runtime": None,
            "hermes_home": None,
        }

        # ClawShell source
        for p in [self.home / ".ClawShell", Path("/mnt/c/Users") / os.environ.get("USER", "Aorus") / ".ClawShell"]:
            if p.exists():
                paths["clawshell_source"] = str(p)
                break

        # ClawShell runtime
        win_home = self.results.get("os", {}).get("windows_home")
        if win_home:
            real = Path(win_home) / ".real"
            if real.exists():
                paths["clawshell_runtime"] = str(real)

        # Hermes home
        hm = self.home / ".hermes"
        if hm.exists():
            paths["hermes_home"] = str(hm)

        return paths

    # ── Recommendations ───────────────────────────────────

    def _generate_recommendations(self):
        recs = self.results["recommendations"]

        if not self.results.get("openclaw", {}).get("found"):
            recs.append("OpenClaw/Wukong not detected — standalone mode recommended")
        if self.results.get("python", {}).get("version", "0") < "3.10":
            recs.append("Python 3.10+ required. Current: " + self.results["python"].get("version", "?"))
        if not self.results.get("node", {}).get("installed"):
            recs.append("Node.js not detected — N8N and Browser Runtime will be unavailable")
        if self.results.get("os", {}).get("is_wsl"):
            recs.append("WSL detected — Windows-side tools will be used where available")

    # ── Report ────────────────────────────────────────────

    def print_report(self):
        """Print a human-readable environment report."""
        r = self.results
        print("\n" + "=" * 60)
        print("  ClawShell 2.0 — Environment Detection Report")
        print("=" * 60)

        os_info = r["os"]
        wsl_tag = " (WSL)" if os_info["is_wsl"] else ""
        print(f"\n🖥  OS:      {os_info['system']} {os_info['release']}{wsl_tag}")
        print(f"🐍 Python:  {r['python']['version']} {'(venv)' if r['python']['in_venv'] else ''}")
        print(f"📦 Node.js: {r['node'].get('version', 'not found')}")
        print(f"🥟 Bun:     {r['bun'].get('version', 'not found')}")

        oc = r["openclaw"]
        print(f"\n🦾 OpenClaw: {'✅ ' + oc.get('type', 'found') if oc['found'] else '❌ not found'}")
        if oc.get("primary_path"):
            print(f"   Path: {oc['primary_path']}")

        hm = r["hermes"]
        print(f"🔮 Hermes:  {'✅' if hm['found'] else '❌ not found'}")
        if hm.get("config"):
            print(f"   Model: {hm['config'].get('model')} @ {hm['config'].get('provider')}")

        wk = r["wukong"]
        print(f"🐵 Wukong:  {'✅ ' + wk.get('type', 'found') + ' (' + str(len(wk.get('users', []))) + ' users)' if wk['found'] else '❌ not found'}")

        if r["recommendations"]:
            print(f"\n💡 Recommendations:")
            for rec in r["recommendations"]:
                print(f"   → {rec}")

        print("\n" + "=" * 60)


if __name__ == "__main__":
    detector = EnvironmentDetector()
    detector.detect_all()
    detector.print_report()
    # Also output JSON for programmatic use
    print("\n--- JSON ---")
    print(json.dumps(detector.results, indent=2, default=str))
