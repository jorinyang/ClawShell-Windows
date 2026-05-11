     1|#!/usr/bin/env python3
     2|"""
     3|ClawShell Semantic Enhancer
     4|语义理解增强 - Phase 1 升级
     5|版本: v1.1.0
     6|功能: 歧义消解、多意图识别、情感分析
     7|"""
     8|
     9|import re
    10|from typing import Dict, List, Optional, Set, Tuple
    11|from dataclasses import dataclass, field
    12|from datetime import datetime
    13|
    14|@dataclass
    15|class Intent:
    16|    """意图"""
    17|    action: str
    18|    object: str
    19|    confidence: float
    20|    params: Dict = field(default_factory=dict)
    21|
    22|class SemanticEnhancer:
    23|    """
    24|    语义理解增强器
    25|    
    26|    功能：
    27|    - 歧义消解: 根据上下文消除歧义
    28|    - 多意图识别: 识别同一句话中的多个意图
    29|    - 情感分析: 判断情感倾向
    30|    """
    31|    
    32|    def __init__(self):
    33|        # 常用词的多义词消歧
    34|        self.disambiguation_rules = {
    35|            "打": {
    36|                "打电话": ["给", "电话"],
    37|                "打球": ["球", "运动"],
    38|                "打印": ["文件", "资料"],
    39|                "打扫": ["房间", "卫生"]
    40|            },
    41|            "取消": {
    42|                "取消订单": ["订单", "取消"],
    43|                "取消关注": ["关注", "粉丝"]
    44|            }
    45|        }
    46|        
    47|        # 意图模式
    48|        self.intent_patterns = {
    49|            "create": ["创建", "新建", "添加", "增加"],
    50|            "read": ["查看", "查询", "获取", "读取"],
    51|            "update": ["修改", "更新", "编辑", "调整"],
    52|            "delete": ["删除", "取消", "移除"],
    53|            "execute": ["执行", "运行", "启动", "触发"],
    54|            "schedule": ["安排", "预约", "定时", "计划"]
    55|        }
    56|        
    57|        # 情感词典
    58|        self.positive_words = {"好", "棒", "优秀", "完美", "赞", "不错", "成功", "完成"}
    59|        self.negative_words = {"差", "坏", "糟糕", "失败", "错误", "问题", "取消"}
    60|    
    61|    def disambiguate(self, word: str, context: str) -> List[str]:
    62|        """消歧: 根据上下文确定词义"""
    63|        candidates = []
    64|        
    65|        if word in self.disambiguation_rules:
    66|            for meaning, keywords in self.disambiguation_rules[word].items():
    67|                if any(kw in context for kw in keywords):
    68|                    candidates.append(meaning)
    69|        
    70|        return candidates if candidates else [word]
    71|    
    72|    def extract_intents(self, text: str) -> List[Intent]:
    73|        """提取意图"""
    74|        intents = []
    75|        
    76|        for action, keywords in self.intent_patterns.items():
    77|            for keyword in keywords:
    78|                if keyword in text:
    79|                    # 提取动作对象
    80|                    obj_match = re.search(f"{keyword}(.+?)(?:并|且|或|$)", text)
    81|                    obj = obj_match.group(1).strip() if obj_match else "unknown"
    82|                    
    83|                    intent = Intent(
    84|                        action=action,
    85|                        object=obj,
    86|                        confidence=0.8
    87|                    )
    88|                    intents.append(intent)
    89|                    break
    90|        
    91|        return intents
    92|    
    93|    def analyze_sentiment(self, text: str) -> Dict[str, float]:
    94|        """情感分析"""
    95|        positive_count = sum(1 for w in self.positive_words if w in text)
    96|        negative_count = sum(1 for w in self.negative_words if w in text)
    97|        
    98|        total = positive_count + negative_count
    99|        if total == 0:
   100|            return {"sentiment": "neutral", "score": 0.5}
   101|        
   102|        positive_ratio = positive_count / total
   103|        
   104|        return {
   105|            "sentiment": "positive" if positive_ratio > 0.6 else "negative" if positive_ratio < 0.4 else "neutral",
   106|            "score": positive_ratio,
   107|            "positive_count": positive_count,
   108|            "negative_count": negative_count
   109|        }
   110|    
   111|    def understand_metaphor(self, text: str) -> Optional[Dict]:
   112|        """隐喻理解"""
   113|        metaphors = {
   114|            "瓶颈": "限制因素",
   115|            "突破口": "解决方案",
   116|            "深水区": "复杂阶段"
   117|        }
   118|        
   119|        for metaphor, literal in metaphors.items():
   120|            if metaphor in text:
   121|                return {
   122|                    "metaphor": metaphor,
   123|                    "literal": literal,
   124|                    "confidence": 0.85
   125|                }
   126|        
   127|        return None
   128|    
   129|    def enhance_understanding(self, text: str, context: str = "") -> Dict:
   130|        """综合增强理解"""
   131|        return {
   132|            "original": text,
   133|            "context": context,
   134|            "disambiguated": [self.disambiguate(w, context or text) for w in text],
   135|            "intents": [
   136|                {"action": i.action, "object": i.object, "confidence": i.confidence}
   137|                for i in self.extract_intents(text)
   138|            ],
   139|            "sentiment": self.analyze_sentiment(text),
   140|            "metaphor": self.understand_metaphor(text)
   141|        }
   142|
   143|if __name__ == "__main__":
   144|    enhancer = SemanticEnhancer()
   145|    
   146|    # 测试
   147|    print("=== 语义增强测试 ===")
   148|    
   149|    # 歧义消解
   150|    print("\n1. 歧义消解:")
   151|    print(f"   '打'在'打电话给妈妈'中: {enhancer.disambiguate('打', '打电话给妈妈')}")
   152|    print(f"   '打'在'打篮球'中: {enhancer.disambiguate('打', '打篮球')}")
   153|    
   154|    # 意图识别
   155|    print("\n2. 多意图识别:")
   156|    intents = enhancer.extract_intents("创建文档并安排明天的会议")
   157|    for intent in intents:
   158|        print(f"   动作: {intent.action}, 对象: {intent.object}, 置信度: {intent.confidence}")
   159|    
   160|    # 情感分析
   161|    print("\n3. 情感分析:")
   162|    print(f"   '系统运行很好很完美': {enhancer.analyze_sentiment('系统运行很好很完美')}")
   163|    print(f"   '出现严重错误': {enhancer.analyze_sentiment('出现严重错误')}")
   164|    
   165|    # 隐喻理解
   166|    print("\n4. 隐喻理解:")
   167|    print(f"   '遇到技术深水区': {enhancer.understand_metaphor('遇到技术深水区')}")
   168|