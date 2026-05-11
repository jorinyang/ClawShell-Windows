     1|"""
     2|ClawShell Cloud — Skill Market v1.1
     3|=====================================
     4|Cloud-side skill repository. Edges publish skills, all edges
     5|can discover and install them. Version-managed with tags.
     6|
     7|Data stored in: data/skill_market/
     8|"""
     9|
    10|import json
    11|import uuid
    12|import threading
    13|from pathlib import Path
    14|from datetime import datetime
    15|from typing import Dict, List, Optional
    16|from dataclasses import dataclass, field, asdict
    17|
    18|
    19|@dataclass
    20|class MarketSkill:
    21|    skill_id: str = ""
    22|    name: str = ""
    23|    version: str = "1.1.0"
    24|    description: str = ""
    25|    content: str = ""
    26|    author: str = ""           # node_id of publisher
    27|    trigger_words: List[str] = field(default_factory=list)
    28|    tags: List[str] = field(default_factory=list)
    29|    category: str = "general"
    30|    dependencies: List[str] = field(default_factory=list)
    31|    install_count: int = 0
    32|    rating: float = 0.0
    33|    published_at: str = ""
    34|    updated_at: str = ""
    35|
    36|    def to_dict(self) -> Dict:
    37|        return asdict(self)
    38|
    39|    @classmethod
    40|    def from_dict(cls, data: Dict) -> "MarketSkill":
    41|        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    42|
    43|
    44|class SkillMarket:
    45|    """Cloud-side skill market — publish, discover, sync across edges."""
    46|
    47|    def __init__(self, data_dir: Path = None):
    48|        if data_dir is None:
    49|            data_dir = Path(__file__).parent.parent.parent / "data"
    50|        self.data_dir = Path(data_dir)
    51|        self.market_dir = self.data_dir / "skill_market"
    52|        self.market_dir.mkdir(parents=True, exist_ok=True)
    53|        self.index_file = self.market_dir / "index.json"
    54|        self._skills: Dict[str, MarketSkill] = {}
    55|        self._lock = threading.Lock()
    56|        self._load()
    57|
    58|    def _save(self):
    59|        with self._lock:
    60|            data = {sid: s.to_dict() for sid, s in self._skills.items()}
    61|            self.index_file.write_text(json.dumps({
    62|                "skills": data,
    63|                "updated_at": datetime.now().isoformat()
    64|            }, indent=2, ensure_ascii=False))
    65|
    66|    def _load(self):
    67|        if self.index_file.exists():
    68|            try:
    69|                data = json.loads(self.index_file.read_text())
    70|                with self._lock:
    71|                    for sid, sd in data.get("skills", {}).items():
    72|                        self._skills[sid] = MarketSkill.from_dict(sd)
    73|            except:
    74|                pass
    75|
    76|    # ═══ Publish ═══════════════════════════════════════════
    77|
    78|    def publish(self, name: str, content: str, author: str = "unknown",
    79|                version: str = "1.1.0", description: str = "",
    80|                trigger_words: List[str] = None, tags: List[str] = None,
    81|                category: str = "general",
    82|                dependencies: List[str] = None) -> MarketSkill:
    83|        """Publish a skill to the market — discoverable by all edges"""
    84|        now = datetime.now().isoformat()
    85|
    86|        # Check if skill with same name exists → version bump
    87|        with self._lock:
    88|            for existing in self._skills.values():
    89|                if existing.name == name and existing.author == author:
    90|                    # Update existing
    91|                    existing.content = content
    92|                    existing.version = version
    93|                    existing.description = description
    94|                    existing.trigger_words = trigger_words or existing.trigger_words
    95|                    existing.tags = tags or existing.tags
    96|                    existing.updated_at = now
    97|                    self._save()
    98|                    # Save full content
    99|                    (self.market_dir / f"{existing.skill_id}.md").write_text(content)
   100|                    return existing
   101|
   102|            # New skill
   103|            skill = MarketSkill(
   104|                skill_id=str(uuid.uuid4())[:8],
   105|                name=name, version=version, description=description,
   106|                content=content, author=author,
   107|                trigger_words=trigger_words or [],
   108|                tags=tags or [], category=category,
   109|                dependencies=dependencies or [],
   110|                published_at=now, updated_at=now,
   111|            )
   112|            self._skills[skill.skill_id] = skill
   113|            self._save()
   114|            # Save full content
   115|            (self.market_dir / f"{skill.skill_id}.md").write_text(content)
   116|            return skill
   117|
   118|    # ═══ Discover ══════════════════════════════════════════
   119|
   120|    def search(self, query: str = "", tags: List[str] = None,
   121|               category: str = None, author: str = None,
   122|               limit: int = 20) -> List[Dict]:
   123|        """Search the skill market — all edges can discover"""
   124|        with self._lock:
   125|            results = []
   126|            query_lower = query.lower()
   127|            for skill in self._skills.values():
   128|                # Filter
   129|                if query_lower:
   130|                    if query_lower not in skill.name.lower() and \
   131|                       query_lower not in skill.description.lower() and \
   132|                       not any(query_lower in t.lower() for t in skill.tags):
   133|                        continue
   134|                if tags and not any(t in skill.tags for t in tags):
   135|                    continue
   136|                if category and skill.category != category:
   137|                    continue
   138|                if author and skill.author != author:
   139|                    continue
   140|
   141|                results.append({
   142|                    "skill_id": skill.skill_id,
   143|                    "name": skill.name,
   144|                    "version": skill.version,
   145|                    "description": skill.description[:150],
   146|                    "author": skill.author,
   147|                    "tags": skill.tags,
   148|                    "category": skill.category,
   149|                    "install_count": skill.install_count,
   150|                    "published_at": skill.published_at,
   151|                })
   152|
   153|            results.sort(key=lambda s: s["install_count"], reverse=True)
   154|            return results[:limit]
   155|
   156|    def get_skill(self, skill_id: str) -> Optional[MarketSkill]:
   157|        """Get full skill content"""
   158|        with self._lock:
   159|            skill = self._skills.get(skill_id)
   160|            if skill:
   161|                skill.install_count += 1  # Track discovery
   162|            return skill
   163|
   164|    def list_by_author(self, author: str) -> List[MarketSkill]:
   165|        """List skills published by a specific edge"""
   166|        with self._lock:
   167|            return [s for s in self._skills.values() if s.author == author]
   168|
   169|    def stats(self) -> Dict:
   170|        with self._lock:
   171|            by_category = {}
   172|            by_author = {}
   173|            for s in self._skills.values():
   174|                by_category[s.category] = by_category.get(s.category, 0) + 1
   175|                by_author[s.author] = by_author.get(s.author, 0) + 1
   176|
   177|            return {
   178|                "total_skills": len(self._skills),
   179|                "by_category": by_category,
   180|                "by_author": by_author,
   181|                "total_installs": sum(s.install_count for s in self._skills.values()),
   182|            }
   183|