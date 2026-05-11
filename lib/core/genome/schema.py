     1|"""
     2|Genome Schema - ClawShell v0.1
     3|=============================
     4|
     5|基因组格式定义。
     6|每个Agent的知识以结构化文档形式存储。
     7|"""
     8|
     9|from dataclasses import dataclass, field
    10|from typing import Dict, List, Any, Optional
    11|from datetime import datetime
    12|from enum import Enum
    13|import yaml
    14|
    15|
    16|class AgentType(Enum):
    17|    """Agent类型"""
    18|    OPENCLAW = "openclaw"
    19|    HERMES = "hermes"
    20|    SHARED = "shared"
    21|
    22|
    23|@dataclass
    24|class KnowledgeEntry:
    25|    """知识条目"""
    26|    key: str
    27|    value: Any
    28|    category: str = "general"
    29|    source: str = None
    30|    confidence: float = 1.0
    31|    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    32|    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    33|    
    34|    def to_dict(self) -> Dict:
    35|        return {
    36|            "key": self.key,
    37|            "value": self.value,
    38|            "category": self.category,
    39|            "source": self.source,
    40|            "confidence": self.confidence,
    41|            "created_at": self.created_at,
    42|            "updated_at": self.updated_at,
    43|        }
    44|
    45|
    46|@dataclass
    47|class ErrorPattern:
    48|    """错误模式"""
    49|    error_type: str
    50|    description: str
    51|    solution: str
    52|    occurrences: int = 0
    53|    last_occurrence: str = None
    54|    tags: List[str] = field(default_factory=list)
    55|    
    56|    def to_dict(self) -> Dict:
    57|        return {
    58|            "error_type": self.error_type,
    59|            "description": self.description,
    60|            "solution": self.solution,
    61|            "occurrences": self.occurrences,
    62|            "last_occurrence": self.last_occurrence,
    63|            "tags": self.tags,
    64|        }
    65|
    66|
    67|@dataclass
    68|class SkillState:
    69|    """技能状态"""
    70|    skill_name: str
    71|    status: str = "active"  # active, disabled, evolving
    72|    version: str = "1.1.0"
    73|    config: Dict = field(default_factory=dict)
    74|    performance: float = 1.0  # 0-1
    75|    last_used: str = None
    76|    tags: List[str] = field(default_factory=list)
    77|    
    78|    def to_dict(self) -> Dict:
    79|        return {
    80|            "skill_name": self.skill_name,
    81|            "status": self.status,
    82|            "version": self.version,
    83|            "config": self.config,
    84|            "performance": self.performance,
    85|            "last_used": self.last_used,
    86|            "tags": self.tags,
    87|        }
    88|
    89|
    90|@dataclass
    91|class EvolutionRecord:
    92|    """进化记录"""
    93|    version: str
    94|    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    95|    changes: List[str] = field(default_factory=list)
    96|    improvements: List[str] = field(default_factory=list)
    97|    from_version: str = None
    98|    notes: str = None
    99|    
   100|    def to_dict(self) -> Dict:
   101|        return {
   102|            "version": self.version,
   103|            "timestamp": self.timestamp,
   104|            "changes": self.changes,
   105|            "improvements": self.improvements,
   106|            "from_version": self.from_version,
   107|            "notes": self.notes,
   108|        }
   109|
   110|
   111|@dataclass
   112|class Genome:
   113|    """
   114|    基因组
   115|    ======
   116|    
   117|    存储Agent的核心知识、状态和配置。
   118|    """
   119|    agent_type: AgentType
   120|    version: str = "0.1.0"
   121|    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
   122|    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
   123|    
   124|    # 核心知识
   125|    knowledge: List[KnowledgeEntry] = field(default_factory=list)
   126|    
   127|    # 用户偏好
   128|    preferences: Dict[str, Any] = field(default_factory=dict)
   129|    
   130|    # 错误模式库
   131|    error_patterns: List[ErrorPattern] = field(default_factory=list)
   132|    
   133|    # 技能状态
   134|    skills: List[SkillState] = field(default_factory=list)
   135|    
   136|    # 进化历史
   137|    evolution: List[EvolutionRecord] = field(default_factory=list)
   138|    
   139|    # 当前状态
   140|    current_task: str = None
   141|    context: str = None
   142|    pending_issues: List[str] = field(default_factory=list)
   143|    
   144|    # 元数据
   145|    metadata: Dict[str, Any] = field(default_factory=dict)
   146|    
   147|    def to_dict(self) -> Dict:
   148|        return {
   149|            "agent_type": self.agent_type.value if isinstance(self.agent_type, AgentType) else self.agent_type,
   150|            "version": self.version,
   151|            "created_at": self.created_at,
   152|            "updated_at": self.updated_at,
   153|            "knowledge": [k.to_dict() if hasattr(k, 'to_dict') else k for k in self.knowledge],
   154|            "preferences": self.preferences,
   155|            "error_patterns": [e.to_dict() if hasattr(e, 'to_dict') else e for e in self.error_patterns],
   156|            "skills": [s.to_dict() if hasattr(s, 'to_dict') else s for s in self.skills],
   157|            "evolution": [e.to_dict() if hasattr(e, 'to_dict') else e for e in self.evolution],
   158|            "current_task": self.current_task,
   159|            "context": self.context,
   160|            "pending_issues": self.pending_issues,
   161|            "metadata": self.metadata,
   162|        }
   163|    
   164|    def to_yaml(self) -> str:
   165|        """转换为YAML格式"""
   166|        return yaml.dump(self.to_dict(), allow_unicode=True, default_flow_style=False, sort_keys=False)
   167|    
   168|    @classmethod
   169|    def from_dict(cls, data: Dict) -> "Genome":
   170|        """从字典创建"""
   171|        agent_type = data.get("agent_type", "shared")
   172|        if isinstance(agent_type, str):
   173|            agent_type = AgentType(agent_type)
   174|        
   175|        return cls(
   176|            agent_type=agent_type,
   177|            version=data.get("version", "0.1.0"),
   178|            created_at=data.get("created_at", datetime.now().isoformat()),
   179|            updated_at=data.get("updated_at", datetime.now().isoformat()),
   180|            knowledge=[KnowledgeEntry(**k) if isinstance(k, dict) else k for k in data.get("knowledge", [])],
   181|            preferences=data.get("preferences", {}),
   182|            error_patterns=[ErrorPattern(**e) if isinstance(e, dict) else e for e in data.get("error_patterns", [])],
   183|            skills=[SkillState(**s) if isinstance(s, dict) else s for s in data.get("skills", [])],
   184|            evolution=[EvolutionRecord(**e) if isinstance(e, dict) else e for e in data.get("evolution", [])],
   185|            current_task=data.get("current_task"),
   186|            context=data.get("context"),
   187|            pending_issues=data.get("pending_issues", []),
   188|            metadata=data.get("metadata", {}),
   189|        )
   190|    
   191|    @classmethod
   192|    def from_yaml(cls, yaml_str: str) -> "Genome":
   193|        """从YAML创建"""
   194|        data = yaml.safe_load(yaml_str)
   195|        return cls.from_dict(data)
   196|    
   197|    def add_knowledge(self, key: str, value: Any, category: str = "general", source: str = None, confidence: float = 1.0):
   198|        """添加知识"""
   199|        entry = KnowledgeEntry(
   200|            key=key,
   201|            value=value,
   202|            category=category,
   203|            source=source,
   204|            confidence=confidence,
   205|        )
   206|        self.knowledge.append(entry)
   207|        self.updated_at = datetime.now().isoformat()
   208|    
   209|    def add_error_pattern(self, error_type: str, description: str, solution: str, tags: List[str] = None):
   210|        """添加错误模式"""
   211|        pattern = ErrorPattern(
   212|            error_type=error_type,
   213|            description=description,
   214|            solution=solution,
   215|            tags=tags or [],
   216|        )
   217|        self.error_patterns.append(pattern)
   218|        self.updated_at = datetime.now().isoformat()
   219|    
   220|    def record_evolution(self, version: str, changes: List[str], improvements: List[str] = None, notes: str = None):
   221|        """记录进化"""
   222|        record = EvolutionRecord(
   223|            version=version,
   224|            changes=changes,
   225|            improvements=improvements or [],
   226|            from_version=self.version,
   227|            notes=notes,
   228|        )
   229|        self.evolution.append(record)
   230|        self.version = version
   231|        self.updated_at = datetime.now().isoformat()
   232|    
   233|    def get_knowledge(self, key: str) -> Optional[Any]:
   234|        """获取知识"""
   235|        for entry in self.knowledge:
   236|            if entry.key == key:
   237|                return entry.value
   238|        return None
   239|    
   240|    def find_error_solution(self, error_type: str) -> Optional[str]:
   241|        """查找错误解决方案"""
   242|        for pattern in self.error_patterns:
   243|            if pattern.error_type == error_type:
   244|                return pattern.solution
   245|        return None
   246|
   247|
   248|@dataclass
   249|class HeritageRecord:
   250|    """
   251|    传承记录
   252|    =========
   253|    
   254|    记录一次传承事件。
   255|    """
   256|    from_version: str
   257|    to_version: str
   258|    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
   259|    heritage_type: str = "restart"  # restart, upgrade, migration
   260|    knowledge_transferred: int = 0
   261|    errors_transferred: int = 0
   262|    skills_transferred: int = 0
   263|    notes: str = None
   264|    
   265|    def to_dict(self) -> Dict:
   266|        return {
   267|            "from_version": self.from_version,
   268|            "to_version": self.to_version,
   269|            "timestamp": self.timestamp,
   270|            "heritage_type": self.heritage_type,
   271|            "knowledge_transferred": self.knowledge_transferred,
   272|            "errors_transferred": self.errors_transferred,
   273|            "skills_transferred": self.skills_transferred,
   274|            "notes": self.notes,
   275|        }
   276|