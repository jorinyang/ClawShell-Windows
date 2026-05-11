     1|#!/usr/bin/env python3
     2|"""
     3|ClawShell IQ Test Questions
     4|标准化IQ测试题库
     5|版本: v1.1.0
     6|"""
     7|
     8|from typing import Dict, List, Tuple
     9|
    10|class IQTestQuestions:
    11|    """IQ测试题库"""
    12|    
    13|    # 言语理解测试
    14|    VERBAL_TESTS = [
    15|        {
    16|            "id": "V1",
    17|            "question": "请解释'授人以鱼不如授人以渔'的含义，并举一个实际例子",
    18|            "max_score": 100,
    19|            "criteria": ["准确解释", "例子恰当", "应用场景"]
    20|        },
    21|        {
    22|            "id": "V2", 
    23|            "question": "如果有人说'时间就是金钱'，请从三个不同角度解读这句话",
    24|            "max_score": 100,
    25|            "criteria": ["经济学角度", "个人发展角度", "社会角度"]
    26|        },
    27|        {
    28|            "id": "V3",
    29|            "question": "请将'Rome was not built in a day'翻译成中文并解释其含义",
    30|            "max_score": 100,
    31|            "criteria": ["翻译准确", "解释完整", "实际应用"]
    32|        }
    33|    ]
    34|    
    35|    # 知觉推理测试
    36|    REASONING_TESTS = [
    37|        {
    38|            "id": "R1",
    39|            "question": """以下代码使用了什么设计模式？请分析其优缺点：
    40|class Singleton:
    41|    _instance = None
    42|    def __new__(cls):
    43|        if cls._instance is None:
    44|            cls._instance = super().__new__(cls)
    45|        return cls._instance""",
    46|            "max_score": 100,
    47|            "criteria": ["识别准确", "优点分析", "缺点分析"]
    48|        },
    49|        {
    50|            "id": "R2",
    51|            "question": "请分析这个系统的瓶颈在哪里：用户说系统慢，数据库CPU 100%，内存80%，应用服务器CPU 20%",
    52|            "max_score": 100,
    53|            "criteria": ["瓶颈定位", "原因分析", "解决方案"]
    54|        },
    55|        {
    56|            "id": "R3",
    57|            "question": "如果A > B, B > C, C > D, A和D是什么关系？请推理",
    58|            "max_score": 100,
    59|            "criteria": ["推理正确", "逻辑清晰", "结论明确"]
    60|        }
    61|    ]
    62|    
    63|    # 工作记忆测试
    64|    MEMORY_TESTS = [
    65|        {
    66|            "id": "M1",
    67|            "question": "请依次记住并复述：苹果、飞机、太阳、书本、河流（按原顺序）",
    68|            "max_score": 100,
    69|            "criteria": ["完全正确", "顺序正确", "回忆完整"]
    70|        },
    71|        {
    72|            "id": "M2",
    73|            "question": "请记住并倒序复述：7、3、9、1、5",
    74|            "max_score": 100,
    75|            "criteria": ["完全正确", "倒序正确"]
    76|        },
    77|        {
    78|            "id": "M3",
    79|            "question": "请在记住后5分钟复述：量子、混沌、涌现、涌现、涌现",
    80|            "max_score": 100,
    81|            "criteria": ["准确记忆", "无遗漏"]
    82|        }
    83|    ]
    84|    
    85|    # 处理速度测试
    86|    SPEED_TESTS = [
    87|        {
    88|            "id": "S1",
    89|            "question": "计算：256 + 128 = ?",
    90|            "max_score": 100,
    91|            "criteria": ["答案正确", "速度快"]
    92|        },
    93|        {
    94|            "id": "S2",
    95|            "question": "查找：数组 [5,2,8,1,9] 中最大的数",
    96|            "max_score": 100,
    97|            "criteria": ["答案正确", "速度快"]
    98|        },
    99|        {
   100|            "id": "S3",
   101|            "question": "判断：3721是质数吗？请快速判断",
   102|            "max_score": 100,
   103|            "criteria": ["判断正确", "速度<5秒"]
   104|        }
   105|    ]
   106|    
   107|    # 知识储备测试
   108|    KNOWLEDGE_TESTS = [
   109|        {
   110|            "id": "K1",
   111|            "question": "请解释什么是微服务架构，它与单体架构的核心区别是什么？",
   112|            "max_score": 100,
   113|            "criteria": ["定义准确", "区别清晰", "优缺点说明"]
   114|        },
   115|        {
   116|            "id": "K2",
   117|            "question": "请说明TCP协议的三次握手过程",
   118|            "max_score": 100,
   119|            "criteria": ["步骤完整", "描述准确", "理解正确"]
   120|        },
   121|        {
   122|            "id": "K3",
   123|            "question": "什么是机器学习中的'过拟合'？如何避免？",
   124|            "max_score": 100,
   125|            "criteria": ["概念正确", "避免方法可行"]
   126|        }
   127|    ]
   128|    
   129|    # 适应学习测试
   130|    ADAPTION_TESTS = [
   131|        {
   132|            "id": "A1",
   133|            "question": "面对一个从未见过的复杂问题，你会如何解决？请描述你的思考过程",
   134|            "max_score": 100,
   135|            "criteria": ["方法论", "系统性", "可操作性"]
   136|        },
   137|        {
   138|            "id": "A2",
   139|            "question": "如果你的方案被专家批评为'不可行'，你会如何应对？",
   140|            "max_score": 100,
   141|            "criteria": ["态度正确", "分析方法", "改进方案"]
   142|        },
   143|        {
   144|            "id": "A3",
   145|            "question": "请用你熟悉的领域的知识，解释一个完全陌生领域的概念",
   146|            "max_score": 100,
   147|            "criteria": ["类比恰当", "解释清晰", "创新性"]
   148|        }
   149|    ]
   150|    
   151|    @classmethod
   152|    def get_all_tests(cls) -> Dict[str, List]:
   153|        """获取所有测试"""
   154|        return {
   155|            "verbal": cls.VERBAL_TESTS,
   156|            "reasoning": cls.REASONING_TESTS,
   157|            "memory": cls.MEMORY_TESTS,
   158|            "speed": cls.SPEED_TESTS,
   159|            "knowledge": cls.KNOWLEDGE_TESTS,
   160|            "adaption": cls.ADAPTION_TESTS
   161|        }
   162|    
   163|    @classmethod
   164|    def get_tests_by_dimension(cls, dimension: str) -> List:
   165|        """按维度获取测试"""
   166|        tests = cls.get_all_tests()
   167|        return tests.get(dimension, [])
   168|
   169|if __name__ == "__main__":
   170|    print("=== IQ测试题库 ===")
   171|    questions = IQTestQuestions()
   172|    
   173|    for dim, tests in questions.get_all_tests().items():
   174|        print(f"\n{dim.upper()} ({len(tests)}题):")
   175|        for t in tests:
   176|            print(f"  [{t['id']}] {t['question'][:50]}...")
   177|