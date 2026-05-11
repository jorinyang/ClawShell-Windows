#!/usr/bin/env python3
"""
ClawShell Cloud — OSS Vault Sync Service v2.0
===============================================
Alibaba Cloud OSS-backed Obsidian vault with bidirectional sync.
Local Obsidian reads/writes vault → ossutil sync → OSS bucket.

Architecture:
  Obsidian Desktop ──→ Local Vault ──ossutil sync──→ OSS Bucket
       ↑                                              ↓
       └──────── ClawShell Cloud API ─────────────────┘
                    (vault CRUD + search)

Dependencies:
  - ossutil (Alibaba Cloud CLI): https://www.alibabacloud.com/help/en/oss/
  - OSS Bucket with proper ACL
  - Alibaba Cloud AccessKey (AK/SK)
"""

import os
import json
import hashlib
import logging
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger("OSSVault")


class OSSVaultConfig:
    """OSS Vault configuration"""

    def __init__(self,
                 bucket: str = None,
                 endpoint: str = None,
                 access_key_id: str = None,
                 access_key_secret: str = None,
                 vault_prefix: str = "obsidian-vault/",
                 local_vault_path: str = None):
        self.bucket = bucket or os.environ.get("OSS_BUCKET", "clawshell-vault")
        self.endpoint = endpoint or os.environ.get("OSS_ENDPOINT", "oss-cn-hangzhou.aliyuncs.com")
        self.access_key_id = access_key_id or os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID", "")
        self.access_key_secret = access_key_secret or os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET", "")
        self.vault_prefix = vault_prefix.rstrip("/") + "/"
        self.local_vault_path = Path(local_vault_path or os.environ.get("OBSIDIAN_VAULT_PATH",
                                  str(Path.home() / "Desktop/WorkSpace/WorkSpace")))

    @property
    def oss_uri(self) -> str:
        return f"oss://{self.bucket}/{self.vault_prefix}"

    def to_dict(self) -> Dict:
        return {
            "bucket": self.bucket,
            "endpoint": self.endpoint,
            "oss_uri": self.oss_uri,
            "local_path": str(self.local_vault_path),
        }


class OSSVaultSync:
    """
    Bidirectional Obsidian vault sync via Alibaba Cloud OSS.

    Sync modes:
      - push:  Local → OSS (upload changes)
      - pull:  OSS → Local (download changes)
      - sync:  Bidirectional (merge both ways)
      - watch: Monitor local changes and auto-push
    """

    SYNC_LOCK_FILE = ".clawshell_sync.lock"
    SYNC_STATE_FILE = ".clawshell_sync_state.json"

    def __init__(self, config: OSSVaultConfig = None):
        self.config = config or OSSVaultConfig()
        self._ossutil_available = self._check_ossutil()
        self._watch_running = False
        self._watch_thread = None

    def _check_ossutil(self) -> bool:
        """Check if ossutil CLI is available"""
        try:
            r = subprocess.run(["ossutil", "--version"], capture_output=True, text=True, timeout=5)
            return r.returncode == 0
        except:
            return False

    def _ensure_config(self):
        """Ensure ossutil is configured with credentials"""
        if not self._ossutil_available:
            return False

        # Configure ossutil if credentials provided
        if self.config.access_key_id and self.config.access_key_secret:
            cmd = [
                "ossutil", "config",
                "-e", self.config.endpoint,
                "-i", self.config.access_key_id,
                "-k", self.config.access_key_secret,
            ]
            try:
                subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            except:
                pass
        return True

    def _load_sync_state(self) -> Dict:
        """Load sync state (file hashes for change detection)"""
        state_file = self.config.local_vault_path / self.SYNC_STATE_FILE
        if state_file.exists():
            try:
                return json.loads(state_file.read_text())
            except:
                pass
        return {"files": {}, "last_sync": None}

    def _save_sync_state(self, state: Dict):
        state_file = self.config.local_vault_path / self.SYNC_STATE_FILE
        state["last_sync"] = datetime.now().isoformat()
        state_file.write_text(json.dumps(state, indent=2))

    def _hash_file(self, filepath: Path) -> str:
        """MD5 hash of file for change detection"""
        hasher = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    # ═══ Sync Operations ═══════════════════════════════════

    def push(self, dry_run: bool = False) -> Dict:
        """Push local vault changes to OSS"""
        if not self._ossutil_available:
            return {"status": "error", "reason": "ossutil not available"}

        self._ensure_config()
        local = str(self.config.local_vault_path) + "/"
        remote = self.config.oss_uri

        cmd = ["ossutil", "sync", local, remote, "--update", "--delete"]
        if dry_run:
            cmd.append("--dry-run")

        result = {"status": "ok", "files": 0, "skipped": 0, "errors": []}
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if r.returncode == 0:
                for line in r.stdout.split("\n"):
                    if "upload" in line.lower() and "success" in line.lower():
                        result["files"] += 1
                    elif "skip" in line.lower():
                        result["skipped"] += 1
                logger.info(f"Push complete: {result['files']} uploaded, {result['skipped']} skipped")
            else:
                result["status"] = "error"
                result["errors"].append(r.stderr[:500])
        except subprocess.TimeoutExpired:
            result["status"] = "timeout"
        except Exception as e:
            result["status"] = "error"
            result["errors"].append(str(e))

        # Update sync state
        self._update_state_hashes()
        return result

    def pull(self, dry_run: bool = False) -> Dict:
        """Pull OSS vault changes to local"""
        if not self._ossutil_available:
            return {"status": "error", "reason": "ossutil not available"}

        self._ensure_config()
        local = str(self.config.local_vault_path) + "/"
        remote = self.config.oss_uri

        cmd = ["ossutil", "sync", remote, local, "--update"]
        if dry_run:
            cmd.append("--dry-run")

        result = {"status": "ok", "files": 0, "errors": []}
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if r.returncode == 0:
                for line in r.stdout.split("\n"):
                    if "download" in line.lower() and "success" in line.lower():
                        result["files"] += 1
                logger.info(f"Pull complete: {result['files']} downloaded")
            else:
                result["status"] = "error"
                result["errors"].append(r.stderr[:500])
        except Exception as e:
            result["status"] = "error"
            result["errors"].append(str(e))

        return result

    def sync(self) -> Dict:
        """Bidirectional sync: pull first, then push"""
        pull_result = self.pull()
        push_result = self.push()
        return {
            "status": "ok",
            "pull": pull_result,
            "push": push_result,
        }

    def _update_state_hashes(self):
        """Update file hashes in sync state"""
        state = {"files": {}, "last_sync": datetime.now().isoformat()}
        vault = self.config.local_vault_path
        for f in vault.rglob("*.md"):
            if ".obsidian" in str(f) or ".trash" in str(f):
                continue
            rel = str(f.relative_to(vault))
            state["files"][rel] = self._hash_file(f)
        self._save_sync_state(state)

    # ═══ Watch Mode (auto-sync on changes) ════════════════

    def start_watch(self, interval: int = 30):
        """Start watching local vault for changes (auto-push)"""
        if self._watch_running:
            return

        self._watch_running = True
        self._watch_thread = threading.Thread(
            target=self._watch_loop, args=(interval,), daemon=True
        )
        self._watch_thread.start()
        logger.info(f"Vault watch started: {interval}s interval")

    def stop_watch(self):
        self._watch_running = False

    def _watch_loop(self, interval: int):
        """Watch loop — detect changes by comparing hashes"""
        import time
        old_state = self._load_sync_state()

        while self._watch_running:
            try:
                time.sleep(interval)
                new_state = {"files": {}}

                vault = self.config.local_vault_path
                for f in vault.rglob("*.md"):
                    if ".obsidian" in str(f) or ".trash" in str(f):
                        continue
                    rel = str(f.relative_to(vault))
                    h = self._hash_file(f)
                    new_state["files"][rel] = h

                # Compare
                changed = []
                for rel, h in new_state["files"].items():
                    if old_state["files"].get(rel) != h:
                        changed.append(rel)

                if changed:
                    logger.info(f"Detected {len(changed)} changes, auto-pushing...")
                    self.push()
                    old_state = new_state

            except Exception as e:
                logger.error(f"Watch error: {e}")

    # ═══ Vault CRUD ═══════════════════════════════════════

    def list_files(self, prefix: str = "") -> List[Dict]:
        """List vault files"""
        files = []
        vault = self.config.local_vault_path

        for f in vault.rglob("*.md"):
            if ".obsidian" in str(f) or ".trash" in str(f):
                continue
            rel = str(f.relative_to(vault))
            if prefix and not rel.startswith(prefix):
                continue
            files.append({
                "path": rel,
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })

        return sorted(files, key=lambda x: x["path"])

    def read_file(self, path: str) -> Optional[str]:
        """Read a vault file"""
        filepath = self.config.local_vault_path / path
        # Security: prevent path traversal
        filepath = filepath.resolve()
        if not str(filepath).startswith(str(self.config.local_vault_path.resolve())):
            return None
        if filepath.exists():
            return filepath.read_text(encoding="utf-8")
        return None

    def write_file(self, path: str, content: str) -> bool:
        """Write a vault file"""
        filepath = self.config.local_vault_path / path
        filepath = filepath.resolve()
        if not str(filepath).startswith(str(self.config.local_vault_path.resolve())):
            return False
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")
        return True

    def search(self, query: str, max_results: int = 20) -> List[Dict]:
        """Full-text search across vault files"""
        results = []
        vault = self.config.local_vault_path
        query_lower = query.lower()

        for f in vault.rglob("*.md"):
            if ".obsidian" in str(f) or ".trash" in str(f):
                continue
            try:
                content = f.read_text(encoding="utf-8")
                if query_lower in content.lower():
                    # Find context around match
                    idx = content.lower().find(query_lower)
                    start = max(0, idx - 60)
                    end = min(len(content), idx + len(query) + 60)
                    context = content[start:end].replace("\n", " ")

                    results.append({
                        "path": str(f.relative_to(vault)),
                        "context": f"...{context}...",
                        "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                    })
            except:
                pass

            if len(results) >= max_results:
                break

        return results

    def stats(self) -> Dict:
        """Vault statistics"""
        vault = self.config.local_vault_path
        md_files = list(vault.rglob("*.md"))
        # Filter out .obsidian and .trash
        md_files = [f for f in md_files if ".obsidian" not in str(f) and ".trash" not in str(f)]

        total_size = sum(f.stat().st_size for f in md_files)
        by_folder = {}
        for f in md_files:
            folder = str(f.parent.relative_to(vault)) if f.parent != vault else "/"
            by_folder[folder] = by_folder.get(folder, 0) + 1

        return {
            "total_files": len(md_files),
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "by_folder": by_folder,
            "oss_uri": self.config.oss_uri,
            "local_path": str(self.config.local_vault_path),
            "ossutil_available": self._ossutil_available,
        }


# ═══ CLI ══════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="ClawShell OSS Vault Sync")
    parser.add_argument("--push", action="store_true", help="Push local to OSS")
    parser.add_argument("--pull", action="store_true", help="Pull OSS to local")
    parser.add_argument("--sync", action="store_true", help="Bidirectional sync")
    parser.add_argument("--watch", action="store_true", help="Watch and auto-sync")
    parser.add_argument("--list", action="store_true", help="List vault files")
    parser.add_argument("--search", type=str, help="Search vault")
    parser.add_argument("--stats", action="store_true", help="Vault statistics")
    parser.add_argument("--bucket", type=str, default="clawshell-vault")
    parser.add_argument("--endpoint", type=str, default="oss-cn-hangzhou.aliyuncs.com")
    parser.add_argument("--local-path", type=str)
    args = parser.parse_args()

    config = OSSVaultConfig(
        bucket=args.bucket,
        endpoint=args.endpoint,
        local_vault_path=args.local_path,
    )
    sync = OSSVaultSync(config)

    if args.stats:
        print(json.dumps(sync.stats(), indent=2, default=str))
    elif args.list:
        for f in sync.list_files():
            print(f"  {f['path']:50} {f['size']:>8}  {f['modified'][:19]}")
    elif args.search:
        results = sync.search(args.search)
        for r in results:
            print(f"\n  📄 {r['path']}")
            print(f"  {r['context'][:120]}")
    elif args.push:
        print(json.dumps(sync.push(), indent=2))
    elif args.pull:
        print(json.dumps(sync.pull(), indent=2))
    elif args.sync:
        print(json.dumps(sync.sync(), indent=2))
    elif args.watch:
        sync.start_watch()
        try:
            import time
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            sync.stop_watch()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
