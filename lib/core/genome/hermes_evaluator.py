     1|#!/usr/bin/env python3
     2|"""
     3|ClawShell Hermes Evaluator
     4|Hermes评估接口 - 用于外部评估OpenClaw的IQ
     5|版本: v1.1.0
     6|"""
     7|
     8|import json
     9|import time
    10|from typing import Dict, List, Optional
    11|from datetime import datetime
    12|from lib.core.genome.iq_challenge_questions import DeepChallengeIQTest as IQTestQuestions
    13|
    14|class HermesEvaluator:
    15|    """
    16|    Hermes评估器
    17|    
    18|    Hermes调用此接口对OpenClaw进行IQ评估
    19|    """
    20|    
    21|    def __init__(self):
    22|        self.questions = IQTestQuestions()
    23|        self.test_history: List[Dict] = []
    24|    
    25|    def get_test_suite(self, dimension: str = None) -> Dict:
    26|        """获取测试套件"""
    27|        if dimension:
    28|            tests = self.questions.get_tests_by_dimension(dimension)
    29|            return {
    30|                "dimension": dimension,
    31|                "tests": tests,
    32|                "count": len(tests)
    33|            }
    34|        else:
    35|            all_tests = self.questions.get_all_tests()
    36|            return {
    37|                "dimensions": list(all_tests.keys()),
    38|                "total_tests": sum(len(t) for t in all_tests.values()),
    39|                "tests": all_tests
    40|            }
    41|    
    42|    def submit_answer(self, test_id: str, answer: str, response_time: float) -> Dict:
    43|        """提交答案用于评估"""
    44|        # 找到对应测试
    45|        test_info = self._find_test(test_id)
    46|        if not test_info:
    47|            return {"error": "Test not found"}
    48|        
    49|        # 保存答案
    50|        submission = {
    51|            "test_id": test_id,
    52|            "answer": answer,
    53|            "response_time": response_time,
    54|            "dimension": test_info["dimension"],
    55|            "submitted_at": datetime.now().isoformat(),
    56|            "scored": False,
    57|            "score": None
    58|        }
    59|        
    60|        self.test_history.append(submission)
    61|        return {
    62|            "status": "submitted",
    63|            "test_id": test_id,
    64|            "pending_evaluation": True
    65|        }
    66|    
    67|    def _find_test(self, test_id: str) -> Optional[Dict]:
    68|        """查找测试"""
    69|        all_tests = self.questions.get_all_tests()
    70|        for dimension, tests in all_tests.items():
    71|            for test in tests:
    72|                if test["id"] == test_id:
    73|                    return {"dimension": dimension, "test": test}
    74|        return None
    75|    
    76|    def get_evaluation_prompt(self, test_id: str, answer: str) -> str:
    77|        """生成评估提示词（供Hermes使用）"""
    78|        test_info = self._find_test(test_id)
    79|        if not test_info:
    80|            return "Test not found"
    81|        
    82|        test = test_info["test"]
    83|        
    84|        prompt = f"""请评估以下答案：
    85|
    86|问题ID: {test_id}
    87|问题: {test['question']}
    88|
    89|答案: {answer}
    90|
    91|评分标准: {', '.join(test['criteria'])}
    92|满分: {test['max_score']}
    93|
    94|请给出：
    95|1. 得分 (0-{test['max_score']})
    96|2. 简要评语
    97|"""
    98|        return prompt
    99|    
   100|    def calculate_iq_score(self) -> Dict:
   101|        """计算IQ分数"""
   102|        if not self.test_history:
   103|            return {"error": "No tests completed"}
   104|        
   105|        # 按维度分组计算
   106|        dimension_scores = {}
   107|        dimension_counts = {}
   108|        
   109|        for submission in self.test_history:
   110|            dim = submission["dimension"]
   111|            if dim not in dimension_scores:
   112|                dimension_scores[dim] = 0
   113|                dimension_counts[dim] = 0
   114|            
   115|            # 这里需要Hermes评估后的分数
   116|            if submission["scored"]:
   117|                dimension_scores[dim] += submission["score"]
   118|                dimension_counts[dim] += 1
   119|        
   120|        # 计算各维度平均分
   121|        dimension_averages = {}
   122|        for dim in dimension_scores:
   123|            if dimension_counts[dim] > 0:
   124|                dimension_averages[dim] = dimension_scores[dim] / dimension_counts[dim]
   125|        
   126|        # 综合得分 (加权平均)
   127|        weights = {
   128|            "verbal": 0.15,
   129|            "reasoning": 0.20,
   130|            "memory": 0.20,
   131|            "speed": 0.15,
   132|            "knowledge": 0.15,
   133|            "adaption": 0.15
   134|        }
   135|        
   136|        overall_score = sum(
   137|            dimension_averages.get(dim, 0) * weights.get(dim, 0)
   138|            for dim in weights
   139|        )
   140|        
   141|        # IQ换算
   142|        iq_score = 70 + (overall_score * 0.6)
   143|        
   144|        return {
   145|            "iq_score": round(iq_score, 1),
   146|            "dimension_scores": dimension_averages,
   147|            "tests_completed": len(self.test_history),
   148|            "timestamp": datetime.now().isoformat()
   149|        }
   150|
   151|if __name__ == "__main__":
   152|    evaluator = HermesEvaluator()
   153|    
   154|    print("=== Hermes评估器测试 ===")
   155|    
   156|    # 获取测试套件
   157|    suite = evaluator.get_test_suite()
   158|    print(f"\n总测试数: {suite['total_tests']}")
   159|    print(f"维度: {suite['dimensions']}")
   160|    
   161|    # 获取言语理解测试
   162|    verbal_tests = evaluator.get_test_suite("verbal")
   163|    print(f"\n言语理解测试 ({verbal_tests['count']}题):")
   164|    for t in verbal_tests['tests']:
   165|        print(f"  [{t['id']}] {t['question'][:40]}...")
   166|