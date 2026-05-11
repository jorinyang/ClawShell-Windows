"""
ClawShell Cloud — Skill Market v1.1
=====================================
Cloud-side skill repository. Edges publish skills, all edges
can discover and install them. Version-managed with tags.

Data stored in: data/skill_market/
"""

import json
import uuid
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class MarketSkill:
    skill_id: str = ""
    name: str = ""
    version: str = "1.1.0"
    description: str = ""
    content: str = ""
    author: str = ""           # node_id of publisher
    trigger_words: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    category: str = "general"
    dependencies: List[str] = field(default_factory=list)
    install_count: int = 0
    rating: float = 0.0
    published_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "MarketSkill":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class SkillMarket:
    """Cloud-side skill market — publish, discover, sync across edges."""

    def __init__(self, data_dir: Path = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data"
        self.data_dir = Path(data_dir)
        self.market_dir = self.data_dir / "skill_market"
        self.market_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.market_dir / "index.json"
        self._skills: Dict[str, MarketSkill] = {}
        self._lock = threading.Lock()
        self._load()

    def _save(self):
        with self._lock:
            data = {sid: s.to_dict() for sid, s in self._skills.items()}
            self.index_file.write_text(json.dumps({
                "skills": data,
                "updated_at": datetime.now().isoformat()
            }, indent=2, ensure_ascii=False))

    def _load(self):
        if self.index_file.exists():
            try:
                data = json.loads(self.index_file.read_text())
                with self._lock:
                    for sid, sd in data.get("skills", {}).items():
                        self._skills[sid] = MarketSkill.from_dict(sd)
            except:
                pass

    # ═══ Publish ═══════════════════════════════════════════

    def publish(self, name: str, content: str, author: str = "unknown",
                version: str = "1.1.0", description: str = "",
                trigger_words: List[str] = None, tags: List[str] = None,
                category: str = "general",
                dependencies: List[str] = None) -> MarketSkill:
        """Publish a skill to the market — discoverable by all edges"""
        now = datetime.now().isoformat()

        # Check if skill with same name exists → version bump
        with self._lock:
            for existing in self._skills.values():
                if existing.name == name and existing.author == author:
                    # Update existing
                    existing.content = content
                    existing.version = version
                    existing.description = description
                    existing.trigger_words = trigger_words or existing.trigger_words
                    existing.tags = tags or existing.tags
                    existing.updated_at = now
                    self._save()
                    # Save full content
                    (self.market_dir / f"{existing.skill_id}.md").write_text(content)
                    return existing

            # New skill
            skill = MarketSkill(
                skill_id=str(uuid.uuid4())[:8],
                name=name, version=version, description=description,
                content=content, author=author,
                trigger_words=trigger_words or [],
                tags=tags or [], category=category,
                dependencies=dependencies or [],
                published_at=now, updated_at=now,
            )
            self._skills[skill.skill_id] = skill
            self._save()
            # Save full content
            (self.market_dir / f"{skill.skill_id}.md").write_text(content)
            return skill

    # ═══ Discover ══════════════════════════════════════════

    def search(self, query: str = "", tags: List[str] = None,
               category: str = None, author: str = None,
               limit: int = 20) -> List[Dict]:
        """Search the skill market — all edges can discover"""
        with self._lock:
            results = []
            query_lower = query.lower()
            for skill in self._skills.values():
                # Filter
                if query_lower:
                    if query_lower not in skill.name.lower() and \
                       query_lower not in skill.description.lower() and \
                       not any(query_lower in t.lower() for t in skill.tags):
                        continue
                if tags and not any(t in skill.tags for t in tags):
                    continue
                if category and skill.category != category:
                    continue
                if author and skill.author != author:
                    continue

                results.append({
                    "skill_id": skill.skill_id,
                    "name": skill.name,
                    "version": skill.version,
                    "description": skill.description[:150],
                    "author": skill.author,
                    "tags": skill.tags,
                    "category": skill.category,
                    "install_count": skill.install_count,
                    "published_at": skill.published_at,
                })

            results.sort(key=lambda s: s["install_count"], reverse=True)
            return results[:limit]

    def get_skill(self, skill_id: str) -> Optional[MarketSkill]:
        """Get full skill content"""
        with self._lock:
            skill = self._skills.get(skill_id)
            if skill:
                skill.install_count += 1  # Track discovery
            return skill

    def list_by_author(self, author: str) -> List[MarketSkill]:
        """List skills published by a specific edge"""
        with self._lock:
            return [s for s in self._skills.values() if s.author == author]

    def stats(self) -> Dict:
        with self._lock:
            by_category = {}
            by_author = {}
            for s in self._skills.values():
                by_category[s.category] = by_category.get(s.category, 0) + 1
                by_author[s.author] = by_author.get(s.author, 0) + 1

            return {
                "total_skills": len(self._skills),
                "by_category": by_category,
                "by_author": by_author,
                "total_installs": sum(s.install_count for s in self._skills.values()),
            }
