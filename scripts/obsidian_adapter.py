#!/usr/bin/env python3
"""
ClawShell Local — Obsidian Vault Adapter v2.0
===============================================
Local-side Obsidian vault adapter: sync with OSS, knowledge graph
building, semantic search, and link discovery.

Integrates with:
  - ClawShell OSS Vault Sync (lib/services/oss_vault.py)
  - Existing Obsidian scripts (graph_builder, link_discover, semantic_analyzer)
  - ClawShell Edge Client (cloud sync)
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("ObsidianAdapter")


class ObsidianAdapter:
    """
    Local Obsidian vault adapter — bridges Obsidian vault to ClawShell ecosystem.

    Features:
      - Vault file CRUD
      - OSS bidirectional sync
      - Knowledge graph building
      - Link discovery between notes
      - Semantic search via ChromaDB (if available)
      - Auto-push to cloud via Edge Client
    """

    def __init__(self, vault_path: str = None):
        # Detect vault path
        if vault_path:
            self.vault_path = Path(vault_path)
        else:
            self.vault_path = self._detect_vault()

        self.obsidian_config = self.vault_path / ".obsidian"
        self.sync = None  # Lazy-init OSSVaultSync
        self._initialized = False

    def _detect_vault(self) -> Path:
        """Auto-detect Obsidian vault location"""
        candidates = [
            Path(os.environ.get("OBSIDIAN_VAULT_PATH", "")),
            Path.home() / "Desktop/WorkSpace/WorkSpace",
            Path.home() / "Documents/Obsidian",
            Path("/mnt/c/Users") / os.environ.get("USER", "Aorus") / "Desktop/WorkSpace/WorkSpace",
        ]
        for p in candidates:
            if (p / ".obsidian").exists():
                return p

        # Fallback: create vault directory
        fallback = Path.home() / "ClawShell Vault"
        fallback.mkdir(parents=True, exist_ok=True)
        (fallback / ".obsidian").mkdir(exist_ok=True)
        return fallback

    def initialize(self):
        """Initialize adapter and verify vault"""
        if not self.vault_path.exists():
            self.vault_path.mkdir(parents=True, exist_ok=True)

        if not self.obsidian_config.exists():
            self.obsidian_config.mkdir(exist_ok=True)
            # Create minimal Obsidian config
            (self.obsidian_config / "app.json").write_text('{"newFileLocation":"root"}')

        self._initialized = True
        logger.info(f"Obsidian adapter initialized: {self.vault_path}")
        return True

    # ═══ Vault CRUD ═══════════════════════════════════════

    def list_files(self, folder: str = "") -> List[Dict]:
        """List markdown files in vault"""
        self.initialize()
        files = []
        scan_path = self.vault_path / folder if folder else self.vault_path

        for f in scan_path.rglob("*.md"):
            if ".obsidian" in str(f) or ".trash" in str(f):
                continue
            rel = str(f.relative_to(self.vault_path))
            files.append({
                "path": rel,
                "name": f.stem,
                "size": f.stat().st_size,
                "modified": str(Path(f).stat().st_mtime),
            })

        return sorted(files, key=lambda x: x["path"])

    def read(self, path: str) -> Optional[str]:
        """Read a vault note"""
        filepath = (self.vault_path / path).resolve()
        if not str(filepath).startswith(str(self.vault_path.resolve())):
            return None
        if filepath.exists() and filepath.suffix == ".md":
            return filepath.read_text(encoding="utf-8")
        return None

    def write(self, path: str, content: str) -> bool:
        """Write a vault note"""
        filepath = (self.vault_path / path).resolve()
        if not str(filepath).startswith(str(self.vault_path.resolve())):
            return False
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")
        return True

    def create_note(self, title: str, content: str = "", folder: str = "") -> Dict:
        """Create a new note with frontmatter"""
        import datetime
        filename = title.replace(" ", "-").replace("/", "-") + ".md"
        filepath = self.vault_path / folder / filename if folder else self.vault_path / filename

        frontmatter = f"""---
title: {title}
created: {datetime.datetime.now().isoformat()[:19]}
tags: []
---

"""
        full_content = frontmatter + content
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(full_content, encoding="utf-8")
        return {"path": str(filepath.relative_to(self.vault_path)), "status": "created"}

    # ═══ Knowledge Graph ══════════════════════════════════

    def build_graph(self) -> Dict:
        """Build knowledge graph from vault"""
        try:
            sys.path.insert(0, str(Path("/mnt/c/Users/Aorus/.ClawShell")))
            from scripts.obsidian_graph_builder import ObsidianGraphBuilder
            builder = ObsidianGraphBuilder()
            # Override vault path
            builder.vault_path = self.vault_path
            graph = builder.build()
            return {"status": "ok", "nodes": len(graph.get("nodes", [])), "edges": len(graph.get("edges", []))}
        except Exception as e:
            return {"status": "error", "reason": str(e)[:200]}

    def discover_links(self) -> List[Dict]:
        """Discover links between notes"""
        links = []
        for f in self.vault_path.rglob("*.md"):
            if ".obsidian" in str(f) or ".trash" in str(f):
                continue
            content = f.read_text(encoding="utf-8")
            rel = str(f.relative_to(self.vault_path))

            # Find [[wiki-links]]
            import re
            for match in re.finditer(r'\[\[([^\]]+)\]\]', content):
                target = match.group(1).split("|")[0].strip()
                links.append({"from": rel, "to": target + ".md", "type": "wikilink"})

        return links

    # ═══ OSS Sync ═════════════════════════════════════════

    def init_oss_sync(self, bucket: str = None, endpoint: str = None) -> Dict:
        """Initialize OSS vault sync"""
        try:
            sys.path.insert(0, str(Path("/mnt/c/Users/Aorus/.ClawShell")))
            from lib.services.oss_vault import OSSVaultConfig, OSSVaultSync

            config = OSSVaultConfig(
                bucket=bucket or "clawshell-vault",
                endpoint=endpoint or "oss-cn-hangzhou.aliyuncs.com",
                local_vault_path=str(self.vault_path),
            )
            self.sync = OSSVaultSync(config)

            return {
                "status": "ok",
                "oss_uri": config.oss_uri,
                "local_path": str(self.vault_path),
                "ossutil_available": self.sync._check_ossutil(),
            }
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def push_to_cloud(self) -> Dict:
        """Push vault to OSS"""
        if not self.sync:
            return {"status": "error", "reason": "OSS sync not initialized. Call init_oss_sync() first."}
        return self.sync.push()

    def pull_from_cloud(self) -> Dict:
        """Pull vault from OSS"""
        if not self.sync:
            return {"status": "error", "reason": "OSS sync not initialized."}
        return self.sync.pull()

    # ═══ Status ═══════════════════════════════════════════

    def status(self) -> Dict:
        self.initialize()
        md_files = len(list(self.vault_path.rglob("*.md")))
        return {
            "vault_path": str(self.vault_path),
            "files": md_files,
            "oss_sync_available": self.sync is not None,
            "ossutil_available": self.sync._check_ossutil() if self.sync else False,
        }


# ═══ CLI ══════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="ClawShell Obsidian Vault Adapter")
    parser.add_argument("--status", action="store_true", help="Show vault status")
    parser.add_argument("--list", action="store_true", help="List vault files")
    parser.add_argument("--search", type=str, help="Search vault")
    parser.add_argument("--links", action="store_true", help="Discover links")
    parser.add_argument("--push", action="store_true", help="Push to OSS")
    parser.add_argument("--pull", action="store_true", help="Pull from OSS")
    parser.add_argument("--path", type=str, help="Vault path")
    parser.add_argument("--bucket", type=str, default="clawshell-vault")
    args = parser.parse_args()

    adapter = ObsidianAdapter(vault_path=args.path)
    adapter.initialize()

    if args.status:
        print(json.dumps(adapter.status(), indent=2))
    elif args.list:
        for f in adapter.list_files():
            print(f"  {f['path']:50} {f['size']:>6}B  {f['modified'][:19]}")
    elif args.search:
        from lib.services.oss_vault import OSSVaultConfig, OSSVaultSync
        config = OSSVaultConfig(local_vault_path=str(adapter.vault_path))
        sync = OSSVaultSync(config)
        for r in sync.search(args.search):
            print(f"\n  📄 {r['path']}")
            print(f"  {r['context'][:120]}")
    elif args.links:
        links = adapter.discover_links()
        print(f"Found {len(links)} links:")
        for l in links[:20]:
            print(f"  {l['from']} → {l['to']}")
    elif args.push:
        adapter.init_oss_sync(bucket=args.bucket)
        print(json.dumps(adapter.push_to_cloud(), indent=2))
    elif args.pull:
        adapter.init_oss_sync(bucket=args.bucket)
        print(json.dumps(adapter.pull_from_cloud(), indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
