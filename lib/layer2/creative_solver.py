     1|#!/usr/bin/env python3
     2|"""
     3|ClawShell Creative Problem Solver
     4|创造性问题解决器 - Phase 3
     5|版本: v1.1.0
     6|功能: 发散思维(多解生成) + 收敛思维(方案优选)
     7|"""
     8|
     9|import json
    10|import random
    11|from typing import Dict, List, Optional, Any
    12|from dataclasses import dataclass, field
    13|from datetime import datetime
    14|
    15|@dataclass
    16|class Solution:
    17|    """解决方案"""
    18|    id: str
    19|    description: str
    20|    score: float = 0.0
    21|    confidence: float = 0.0
    22|    novelty: float = 0.0,  # 创新度
    23|    feasibility: float = 0.0,  # 可行性
    24|    strategy: str = "general",  # 策略
    25|    category: str = "general"
    26|    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    27|
    28|class CreativeSolver:
    29|    """
    30|    创造性问题解决器
    31|    
    32|    功能：
    33|    - 发散思维: 生成多个可能的解决方案
    34|    - 收敛思维: 从多解中选择最优
    35|    - 远迁移: 跨领域应用知识
    36|    """
    37|    
    38|    def __init__(self):
    39|        self.solutions: List[Solution] = []
    40|        self.domain_knowledge: Dict[str, List[str]] = {}
    41|        
    42|        # 启发式策略
    43|        self.divergence_strategies = [
    44|            "analogy",      # 类比
    45|            "reversal",     # 逆转
    46|            "combination",  # 组合
    47|            "abstract",     # 抽象
    48|            "concrete"      # 具体化
    49|        ]
    50|    
    51|    def add_domain_knowledge(self, domain: str, patterns: List[str]):
    52|        """添加领域知识"""
    53|        if domain not in self.domain_knowledge:
    54|            self.domain_knowledge[domain] = []
    55|        self.domain_knowledge[domain].extend(patterns)
    56|    
    57|    def generate_divergent(self, problem: str, num_solutions: int = 5) -> List[Solution]:
    58|        """发散思维: 生成多个解决方案"""
    59|        solutions = []
    60|        
    61|        for i in range(num_solutions):
    62|            strategy = random.choice(self.divergence_strategies)
    63|            
    64|            solution = Solution(
    65|                id=f"sol_{len(self.solutions) + i + 1}",
    66|                description=self._apply_strategy(problem, strategy),
    67|                strategy=strategy,
    68|                novelty=random.uniform(0.6, 0.95),
    69|                feasibility=random.uniform(0.5, 0.9)
    70|            )
    71|            solution.score = (solution.novelty + solution.feasibility) / 2
    72|            solutions.append(solution)
    73|        
    74|        self.solutions.extend(solutions)
    75|        return solutions
    76|    
    77|    def _apply_strategy(self, problem: str, strategy: str) -> str:
    78|        """应用策略生成解决方案"""
    79|        strategies = {
    80|            "analogy": f"类比方案: {problem} 类似场景...",
    81|            "reversal": f"逆转方案: 反向思考 {problem}...",
    82|            "combination": f"组合方案: 结合多个元素 {problem}...",
    83|            "abstract": f"抽象方案: 提取 {problem} 的核心本质...",
    84|            "concrete": f"具体方案: 将 {problem} 细化为具体步骤..."
    85|        }
    86|        return strategies.get(strategy, f"方案: {problem}")
    87|    
    88|    def converge(self, solutions: List[Solution], top_k: int = 3) -> List[Solution]:
    89|        """收敛思维: 选择最优方案"""
    90|        # 按评分排序
    91|        sorted_solutions = sorted(solutions, key=lambda s: s.score, reverse=True)
    92|        return sorted_solutions[:top_k]
    93|    
    94|    def far_transfer(self, source_domain: str, target_domain: str, solution: Solution) -> Solution:
    95|        """远迁移: 将一个领域的解决方案应用到另一个领域"""
    96|        if source_domain in self.domain_knowledge and target_domain in self.domain_knowledge:
    97|            # 获取目标领域的知识
    98|            target_knowledge = self.domain_knowledge[target_domain]
    99|            
   100|            # 修改解决方案以适应新领域
   101|            transferred = Solution(
   102|                id=f"{solution.id}_transferred",
   103|                description=f"[{target_domain}] {solution.description}",
   104|                novelty=solution.novelty * 0.8,  # 迁移会降低创新度
   105|                feasibility=solution.feasibility * 0.9,
   106|                category=target_domain
   107|            )
   108|            transferred.score = (transferred.novelty + transferred.feasibility) / 2
   109|            return transferred
   110|        
   111|        return solution
   112|    
   113|    def solve(self, problem: str, domain: str = "general") -> Dict[str, Any]:
   114|        """完整解决流程"""
   115|        # 1. 发散生成
   116|        divergent_solutions = self.generate_divergent(problem, num_solutions=7)
   117|        
   118|        # 2. 收敛选择
   119|        best_solutions = self.converge(divergent_solutions, top_k=3)
   120|        
   121|        # 3. 如果有领域知识，尝试远迁移
   122|        if domain != "general" and domain in self.domain_knowledge:
   123|            transferred = []
   124|            for sol in best_solutions[:2]:
   125|                transfer = self.far_transfer("general", domain, sol)
   126|                transferred.append(transfer)
   127|            best_solutions.extend(transferred)
   128|        
   129|        return {
   130|            "problem": problem,
   131|            "all_solutions": [
   132|                {"id": s.id, "description": s.description, "score": s.score}
   133|                for s in divergent_solutions
   134|            ],
   135|            "best_solutions": [
   136|                {"id": s.id, "description": s.description, "score": s.score}
   137|                for s in best_solutions
   138|            ],
   139|            "stats": {
   140|                "total_generated": len(divergent_solutions),
   141|                "top_score": best_solutions[0].score if best_solutions else 0
   142|            }
   143|        }
   144|
   145|if __name__ == "__main__":
   146|    solver = CreativeSolver()
   147|    
   148|    # 添加领域知识
   149|    solver.add_domain_knowledge("software", ["模式", "架构", "重构"])
   150|    solver.add_domain_knowledge("business", ["流程", "优化", "增长"])
   151|    
   152|    print("=== 创造性问题解决测试 ===")
   153|    
   154|    # 测试
   155|    result = solver.solve("如何提高系统性能", domain="software")
   156|    
   157|    print(f"\n问题: {result['problem']}")
   158|    print(f"\n生成方案数: {result['stats']['total_generated']}")
   159|    print(f"\n最优方案:")
   160|    for sol in result['best_solutions']:
   161|        print(f"  [{sol['score']:.2f}] {sol['description']}")
   162|