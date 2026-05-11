#!/usr/bin/env python3
"""
ClawShell 2.0 — Ecosystem Installer
=====================================
Interactive installer for ClawShell ecosystem components.
Supports: MemPalace, ChromaDB, N8N, MemOS Cloud, Watchdog,
          Browser Runtime, Playwright, ONNX Runtime, Docker.

Usage:
  python3 ecosystem_installer.py              # Interactive
  python3 ecosystem_installer.py --all         # Install everything
  python3 ecosystem_installer.py --list        # List available
  python3 ecosystem_installer.py --install mempalace,chromadb
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Callable, Optional


# ═══════════════════════════════════════════════════════════
# Component Registry
# ═══════════════════════════════════════════════════════════

COMPONENTS = {
    "mempalace": {
        "name": "MemPalace (本地记忆宫殿)",
        "description": "SQLite + ChromaDB 向量搜索记忆系统，本地优先",
        "required": False,
        "category": "memory",
        "pip_packages": ["chromadb"],
        "install": lambda: _pip_install(["chromadb"]),
        "check": lambda: _check_import("chromadb"),
        "post_install": lambda: _init_mempalace(),
    },
    "chromadb": {
        "name": "ChromaDB (向量数据库)",
        "description": "高性能向量存储与语义搜索",
        "required": True,
        "category": "storage",
        "pip_packages": ["chromadb"],
        "install": lambda: _pip_install(["chromadb"]),
        "check": lambda: _check_import("chromadb"),
        "post_install": None,
    },
    "n8n": {
        "name": "N8N (工作流自动化引擎)",
        "description": "可视化工作流编排，支持400+集成",
        "required": False,
        "category": "automation",
        "install": lambda: _run("npx", "n8n", "--version"),
        "check": lambda: _check_command("n8n") or _check_command("npx"),
        "post_install": None,
    },
    "memos_cloud": {
        "name": "MemOS Cloud (云端记忆同步)",
        "description": "跨设备记忆同步，API: memos.memtensor.cn",
        "required": False,
        "category": "memory",
        "install": None,  # API key configuration only
        "check": lambda: bool(os.environ.get("MEMOS_API_KEY")),
        "post_install": lambda: _configure_api_key("MEMOS_API_KEY", "MemOS Cloud API Key"),
    },
    "watchdog": {
        "name": "Watchdog (文件系统监听)",
        "description": "实时文件变化监控，用于EventBus文件监听",
        "required": False,
        "category": "monitoring",
        "pip_packages": ["watchdog"],
        "install": lambda: _pip_install(["watchdog"]),
        "check": lambda: _check_import("watchdog"),
        "post_install": None,
    },
    "browser_runtime": {
        "name": "Browser Runtime (CDP浏览器控制)",
        "description": "Playwright + Chromium 浏览器自动化",
        "required": False,
        "category": "browser",
        "install": lambda: _install_playwright_chromium(),
        "check": lambda: _check_playwright_chromium(),
        "post_install": None,
    },
    "onnx_runtime": {
        "name": "ONNX Runtime (ML推理加速)",
        "description": "跨平台ML模型推理，支持CPU/GPU",
        "required": False,
        "category": "ml",
        "pip_packages": ["onnxruntime"],
        "install": lambda: _pip_install(["onnxruntime"]),
        "check": lambda: _check_import("onnxruntime"),
        "post_install": None,
    },
    "psutil": {
        "name": "psutil (系统资源监控)",
        "description": "CPU/内存/磁盘使用率监控",
        "required": True,
        "category": "monitoring",
        "pip_packages": ["psutil"],
        "install": lambda: _pip_install(["psutil"]),
        "check": lambda: _check_import("psutil"),
        "post_install": None,
    },
    "websockets": {
        "name": "websockets (实时通信)",
        "description": "WebSocket客户端，用于Cloud实时事件推送",
        "required": True,
        "category": "network",
        "pip_packages": ["websockets"],
        "install": lambda: _pip_install(["websockets"]),
        "check": lambda: _check_import("websockets"),
        "post_install": None,
    },
}


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def _pip_install(packages: List[str]) -> bool:
    """Install Python packages via pip"""
    try:
        pip = [sys.executable, "-m", "pip", "install", "--quiet"] + packages
        r = subprocess.run(pip, capture_output=True, text=True, timeout=120)
        return r.returncode == 0
    except Exception:
        return False


def _check_import(module: str) -> bool:
    """Check if Python module can be imported"""
    try:
        __import__(module)
        return True
    except ImportError:
        return False


def _check_command(cmd: str) -> bool:
    """Check if command exists in PATH"""
    try:
        r = subprocess.run(["which", cmd], capture_output=True, timeout=5)
        return r.returncode == 0
    except:
        return False


def _run(*args) -> bool:
    """Run a command"""
    try:
        r = subprocess.run(list(args), capture_output=True, timeout=30)
        return r.returncode == 0
    except:
        return False


def _init_mempalace():
    """Initialize MemPalace database directory"""
    palace_dir = Path.home() / ".claude" / "palace"
    palace_dir.mkdir(parents=True, exist_ok=True)
    print(f"   MemPalace dir: {palace_dir}")


def _configure_api_key(env_var: str, description: str):
    """Prompt user for API key configuration"""
    print(f"\n   Configure {description}:")
    key = input(f"   Enter {env_var} (press Enter to skip): ").strip()
    if key:
        os.environ[env_var] = key
        # Save to .env
        env_file = Path.home() / ".hermes" / ".env"
        env_file.parent.mkdir(parents=True, exist_ok=True)
        with open(env_file, "a") as f:
            f.write(f"\n{env_var}={key}\n")
        print(f"   ✅ {env_var} saved to {env_file}")


def _install_playwright_chromium() -> bool:
    """Install Playwright Chromium browser"""
    try:
        r = subprocess.run(
            ["npx", "playwright", "install", "chromium"],
            capture_output=True, text=True, timeout=300
        )
        return r.returncode == 0
    except:
        return False


def _check_playwright_chromium() -> bool:
    """Check if Playwright Chromium is installed"""
    import platform
    home = Path.home()
    if platform.system() == "Windows" or os.environ.get("WSL_DISTRO_NAME"):
        chromium = Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright" / "chromium-1217"
    else:
        chromium = home / ".cache" / "ms-playwright" / "chromium-1217"
    return chromium.exists()


# ═══════════════════════════════════════════════════════════
# Installer
# ═══════════════════════════════════════════════════════════

class EcosystemInstaller:
    """Interactive ecosystem component installer."""

    def __init__(self):
        self.results: Dict[str, Dict] = {}
        self.selected: List[str] = []

    def list_components(self):
        """Print available components"""
        print("\n" + "=" * 65)
        print("  ClawShell 2.0 — Ecosystem Components")
        print("=" * 65)
        for key, comp in COMPONENTS.items():
            status = "✅" if self._is_installed(key) else "⬜"
            required = "🔒" if comp["required"] else "  "
            print(f"  [{status}] {required} {comp['name']:35} [{key}]")
            print(f"         {comp['description']}")
        print()

    def interactive_select(self):
        """Interactive component selection"""
        self.list_components()

        print("Select components to install (comma-separated IDs, or 'all'):")
        print("IDs: " + ", ".join(COMPONENTS.keys()))
        choice = input("> ").strip().lower()

        if choice == "all":
            self.selected = list(COMPONENTS.keys())
        elif choice:
            self.selected = [c.strip() for c in choice.split(",") if c.strip() in COMPONENTS]

        # Always include required components
        for key, comp in COMPONENTS.items():
            if comp["required"] and key not in self.selected:
                self.selected.append(key)

    def install_selected(self):
        """Install all selected components"""
        if not self.selected:
            print("No components selected.")
            return

        print(f"\nInstalling {len(self.selected)} components...")
        print("-" * 50)

        for key in self.selected:
            comp = COMPONENTS[key]
            print(f"\n📦 {comp['name']} [{key}]")

            if self._is_installed(key):
                print(f"   ✅ Already installed")
                self.results[key] = {"status": "already_installed"}
                continue

            if comp.get("install"):
                print(f"   Installing...")
                success = comp["install"]()
                if success:
                    print(f"   ✅ Installed")
                    self.results[key] = {"status": "installed"}
                else:
                    print(f"   ❌ Failed")
                    self.results[key] = {"status": "failed"}
            else:
                # No-op install (e.g., API key config)
                print(f"   ⚙️  Configuration required")
                self.results[key] = {"status": "configured"}

            # Post-install
            if comp.get("post_install") and self.results[key]["status"] in ("installed", "configured"):
                comp["post_install"]()

        # Verify all
        print(f"\n" + "=" * 50)
        print("Verification:")
        for key in self.selected:
            comp = COMPONENTS[key]
            ok = self._is_installed(key)
            print(f"  {'✅' if ok else '❌'} {comp['name']}")

    def install_by_name(self, names: List[str]):
        """Install specific components by name"""
        for name in names:
            if name in COMPONENTS:
                self.selected.append(name)
        self.install_selected()

    def _is_installed(self, key: str) -> bool:
        comp = COMPONENTS.get(key)
        if not comp or not comp.get("check"):
            return True
        try:
            return comp["check"]()
        except:
            return False

    def get_report(self) -> Dict:
        """Generate installation report"""
        report = {}
        for key, comp in COMPONENTS.items():
            report[key] = {
                "name": comp["name"],
                "installed": self._is_installed(key),
                "required": comp["required"],
                "status": self.results.get(key, {}).get("status", "not_installed"),
            }
        return report


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="ClawShell Ecosystem Installer")
    parser.add_argument("--list", action="store_true", help="List available components")
    parser.add_argument("--all", action="store_true", help="Install all components")
    parser.add_argument("--install", type=str, help="Comma-separated component IDs to install")
    parser.add_argument("--check", action="store_true", help="Check installation status only")
    args = parser.parse_args()

    installer = EcosystemInstaller()

    if args.list:
        installer.list_components()
        return

    if args.check:
        installer.list_components()
        print("\nDetailed status:")
        for key, info in installer.get_report().items():
            print(f"  {'✅' if info['installed'] else '❌'} {info['name']}")
        return

    if args.all:
        installer.selected = list(COMPONENTS.keys())
        installer.install_selected()
    elif args.install:
        installer.install_by_name([s.strip() for s in args.install.split(",")])
    else:
        installer.interactive_select()
        installer.install_selected()


if __name__ == "__main__":
    main()
