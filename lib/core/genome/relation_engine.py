     1|#!/usr/bin/env python3
     2|"""
     3|ClawShell Relation Engine
     4|关系推理引擎 - Phase 1 升级
     5|版本: v1.1.0
     6|功能: 抽象关系理解、归纳推理、演绎推理
     7|"""
     8|
     9|import json
    10|import re
    11|from typing import Dict, List, Optional, Set, Tuple
    12|from dataclasses import dataclass, field
    13|from datetime import datetime
    14|
    15|RELATION_TYPES = [
    16|    "opposite",      # 相反关系: A→非A
    17|    "similar",       # 相似关系: A≈B
    18|    "part_whole",    # 部分-整体: A∈B
    19|    "cause_effect",   # 因果关系: A导致B
    20|    "condition",      # 条件关系: A则B
    21|    "temporal",      # 时间关系: A先于B
    22|    "spatial",       # 空间关系: A位于B
    23|    "reference",     # 引用关系: A引用B
    24|]
    25|
    26|@dataclass
    27|class Relation:
    28|    """关系"""
    29|    id: str
    30|    relation_type: str
    31|    source: str
    32|    target: str
    33|    confidence: float = 1.0
    34|    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    35|
    36|class RelationEngine:
    37|    """
    38|    关系推理引擎
    39|    
    40|    功能：
    41|    - 关系识别: 从文本中识别关系
    42|    - 关系推理: 基于已知关系推断新关系
    43|    - 关系验证: 验证关系的一致性
    44|    """
    45|    
    46|    def __init__(self):
    47|        self.relations: Dict[str, List[Relation]] = {}
    48|        self.relation_graph: Dict[str, Set[str]] = {}
    49|        
    50|    def add_relation(self, relation_type: str, source: str, target: str, confidence: float = 1.0):
    51|        """添加关系"""
    52|        rel_id = f"{source}|{relation_type}|{target}"
    53|        relation = Relation(
    54|            id=rel_id,
    55|            relation_type=relation_type,
    56|            source=source,
    57|            target=target,
    58|            confidence=confidence
    59|        )
    60|        
    61|        if relation_type not in self.relations:
    62|            self.relations[relation_type] = []
    63|        self.relations[relation_type].append(relation)
    64|        
    65|        # 更新关系图
    66|        if source not in self.relation_graph:
    67|            self.relation_graph[source] = set()
    68|        self.relation_graph[source].add(target)
    69|        
    70|        return relation
    71|    
    72|    def find_opposite(self, entity: str) -> List[str]:
    73|        """找相反关系"""
    74|        opposites = []
    75|        for rel in self.relations.get("opposite", []):
    76|            if rel.source == entity:
    77|                opposites.append(rel.target)
    78|            elif rel.target == entity:
    79|                opposites.append(rel.source)
    80|        return opposites
    81|    
    82|    def find_similar(self, entity: str) -> List[str]:
    83|        """找相似关系"""
    84|        similar = []
    85|        for rel in self.relations.get("similar", []):
    86|            if rel.source == entity:
    87|                similar.append(rel.target)
    88|            elif rel.target == entity:
    89|                similar.append(rel.source)
    90|        return similar
    91|    
    92|    def find_causes(self, entity: str) -> List[str]:
    93|        """找原因"""
    94|        causes = []
    95|        for rel in self.relations.get("cause_effect", []):
    96|            if rel.target == entity:
    97|                causes.append(rel.source)
    98|        return causes
    99|    
   100|    def find_effects(self, entity: str) -> List[str]:
   101|        """找结果"""
   102|        effects = []
   103|        for rel in self.relations.get("cause_effect", []):
   104|            if rel.source == entity:
   105|                effects.append(rel.target)
   106|        return effects
   107|    
   108|    def transitive_inference(self, entity: str, relation_type: str) -> Set[str]:
   109|        """传递推理: A→B, B→C => A→C"""
   110|        result = set()
   111|        visited = set()
   112|        queue = [entity]
   113|        
   114|        while queue:
   115|            current = queue.pop(0)
   116|            if current in visited:
   117|                continue
   118|            visited.add(current)
   119|            
   120|            for rel in self.relations.get(relation_type, []):
   121|                if rel.source == current and rel.target not in visited:
   122|                    result.add(rel.target)
   123|                    queue.append(rel.target)
   124|        
   125|        return result
   126|    
   127|    def deduce_from_opposites(self, entity: str) -> Dict[str, any]:
   128|        """演绎推理: opposite(opposite(A)) = A"""
   129|        return {
   130|            "entity": entity,
   131|            "opposites": self.find_opposite(entity),
   132|            "double_negation": entity if self.find_opposite(entity) else None
   133|        }
   134|    
   135|    def deduce_from_causes(self, entity: str) -> Dict[str, List[str]]:
   136|        """演绎推理: 原因链"""
   137|        chain = []
   138|        current = entity
   139|        
   140|        while True:
   141|            causes = self.find_causes(current)
   142|            if not causes:
   143|                break
   144|            chain.append(causes[0])
   145|            current = causes[0]
   146|        
   147|        return {
   148|            "entity": entity,
   149|            "root_causes": chain,
   150|            "effects": self.find_effects(entity)
   151|        }
   152|    
   153|    def export_graph(self) -> Dict:
   154|        """导出关系图"""
   155|        return {
   156|            "nodes": list(self.relation_graph.keys()),
   157|            "edges": [
   158|                {"source": k, "target": v}
   159|                for k, vs in self.relation_graph.items()
   160|                for v in vs
   161|            ],
   162|            "relation_counts": {
   163|                rel_type: len(rels)
   164|                for rel_type, rels in self.relations.items()
   165|            }
   166|        }
   167|    
   168|    def import_from_json(self, data: Dict):
   169|        """从JSON导入"""
   170|        self.relations = {}
   171|        self.relation_graph = {}
   172|        
   173|        for rel_type, rels in data.get("relations", {}).items():
   174|            for rel_data in rels:
   175|                self.add_relation(
   176|                    rel_type,
   177|                    rel_data["source"],
   178|                    rel_data["target"],
   179|                    rel_data.get("confidence", 1.0)
   180|                )
   181|
   182|if __name__ == "__main__":
   183|    engine = RelationEngine()
   184|    
   185|    # 测试关系添加
   186|    engine.add_relation("opposite", "hot", "cold", 0.95)
   187|    engine.add_relation("opposite", "cold", "hot", 0.95)
   188|    engine.add_relation("similar", "hot", "warm", 0.8)
   189|    engine.add_relation("cause_effect", "fire", "smoke", 0.9)
   190|    engine.add_relation("cause_effect", "smoke", "alarm", 0.85)
   191|    
   192|    # 测试推理
   193|    print("=== 关系推理引擎测试 ===")
   194|    print(f"hot的反义: {engine.find_opposite('hot')}")
   195|    print(f"hot的相似: {engine.find_similar('hot')}")
   196|    print(f"alarm的原因: {engine.find_causes('alarm')}")
   197|    print(f"fire的传递结果: {engine.transitive_inference('fire', 'cause_effect')}")
   198|    
   199|    # 导出图
   200|    graph = engine.export_graph()
   201|    print(f"\n关系图: {json.dumps(graph, indent=2, ensure_ascii=False)}")
   202|