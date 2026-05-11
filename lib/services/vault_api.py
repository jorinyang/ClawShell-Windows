"""
ClawShell Cloud — Vault API (Obsidian + OSS)
=============================================
GET    /vault/status      — Vault statistics
GET    /vault/files       — List vault files
GET    /vault/search?q=   — Full-text search
POST   /vault/note        — Create a note
PUT    /vault/note/{path} — Update a note
POST   /vault/sync/push   — Push to OSS
POST   /vault/sync/pull   — Pull from OSS
"""
from fastapi import APIRouter, HTTPException, Header, Query
from typing import Optional
from pathlib import Path

from core.config import settings
from core.auth import verify_edge_auth

router = APIRouter()

# Lazy import OSS vault (only available on Cloud side)
_vault = None


def _get_vault():
    global _vault
    if _vault is None:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / ".ClawShell"))
        from lib.services.oss_vault import OSSVaultConfig, OSSVaultSync
        
        config = OSSVaultConfig(
            bucket=settings.OSS_BUCKET if hasattr(settings, 'OSS_BUCKET') else "clawshell-vault",
            endpoint=settings.OSS_ENDPOINT if hasattr(settings, 'OSS_ENDPOINT') else "oss-cn-hangzhou.aliyuncs.com",
            local_vault_path=str(settings.DATA_DIR / "vault"),
        )
        _vault = OSSVaultSync(config)
    return _vault


@router.get("/vault/status")
async def vault_status(x_edge_token: str = Header(None)):
    """Get vault statistics"""
    verify_edge_auth(x_edge_token)
    vault = _get_vault()
    return vault.stats()


@router.get("/vault/files")
async def list_files(prefix: str = "", x_edge_token: str = Header(None)):
    """List vault files"""
    verify_edge_auth(x_edge_token)
    vault = _get_vault()
    files = vault.list_files(prefix)
    return {"files": files, "count": len(files)}


@router.get("/vault/search")
async def search_vault(q: str = Query(...), limit: int = 20, x_edge_token: str = Header(None)):
    """Full-text search across vault"""
    verify_edge_auth(x_edge_token)
    vault = _get_vault()
    results = vault.search(q, max_results=limit)
    return {"query": q, "results": results, "count": len(results)}


@router.post("/vault/note")
async def create_note(payload: dict, x_edge_token: str = Header(None)):
    """Create a new vault note"""
    verify_edge_auth(x_edge_token)
    vault = _get_vault()
    
    path = payload.get("path", "")
    content = payload.get("content", "")
    
    if not path:
        import uuid
        path = f"notes/{uuid.uuid4().hex[:8]}.md"
    
    success = vault.write_file(path, content)
    return {"status": "created" if success else "error", "path": path}


@router.put("/vault/note/{path:path}")
async def update_note(path: str, payload: dict, x_edge_token: str = Header(None)):
    """Update a vault note"""
    verify_edge_auth(x_edge_token)
    vault = _get_vault()
    
    content = payload.get("content", "")
    success = vault.write_file(path, content)
    return {"status": "updated" if success else "error", "path": path}


@router.post("/vault/sync/push")
async def push_vault(x_edge_token: str = Header(None)):
    """Push vault to OSS"""
    verify_edge_auth(x_edge_token)
    vault = _get_vault()
    return vault.push()


@router.post("/vault/sync/pull")
async def pull_vault(x_edge_token: str = Header(None)):
    """Pull vault from OSS"""
    verify_edge_auth(x_edge_token)
    vault = _get_vault()
    return vault.pull()
