     1|#!/usr/bin/env python3
     2|"""
     3|ClawShell News Aggregator
     4|新闻聚合器 - Phase 4
     5|版本: v1.1.0
     6|"""
     7|
     8|import json
     9|import urllib.request
    10|import urllib.parse
    11|from datetime import datetime
    12|from typing import Dict, List, Optional
    13|from collections import deque
    14|
    15|class NewsAggregator:
    16|    """新闻聚合器"""
    17|    
    18|    def __init__(self, max_history: int = 100):
    19|        self.max_history = max_history
    20|        self.news_history: deque = deque(maxlen=max_history)
    21|        self.categories = ["technology", "business", "science", "health"]
    22|    
    23|    def fetch_tech_news(self, limit: int = 10) -> List[Dict]:
    24|        """获取科技新闻 (使用NewsAPI或RSS)"""
    25|        # 这里使用一个免费的RSS源
    26|        rss_url = "https://feeds.feedburner.com/techcrunch"
    27|        
    28|        # 模拟新闻数据
    29|        mock_news = [
    30|            {
    31|                "title": "AI Breakthrough in Reasoning",
    32|                "source": "TechCrunch",
    33|                "published": datetime.now().isoformat(),
    34|                "url": "https://example.com/ai-reasoning",
    35|                "category": "technology"
    36|            },
    37|            {
    38|                "title": "New Programming Language Released",
    39|                "source": "Hacker News",
    40|                "published": datetime.now().isoformat(),
    41|                "url": "https://example.com/new-lang",
    42|                "category": "technology"
    43|            }
    44|        ]
    45|        
    46|        return mock_news[:limit]
    47|    
    48|    def add_news(self, news: Dict):
    49|        """添加新闻到历史"""
    50|        news["added_at"] = datetime.now().isoformat()
    51|        self.news_history.append(news)
    52|    
    53|    def get_recent_news(self, limit: int = 20) -> List[Dict]:
    54|        """获取最近新闻"""
    55|        return list(self.news_history)[-limit:]
    56|    
    57|    def search_news(self, keyword: str) -> List[Dict]:
    58|        """搜索新闻"""
    59|        keyword_lower = keyword.lower()
    60|        results = []
    61|        
    62|        for news in self.news_history:
    63|            title = news.get("title", "").lower()
    64|            if keyword_lower in title:
    65|                results.append(news)
    66|        
    67|        return results
    68|    
    69|    def get_stats(self) -> Dict:
    70|        """获取统计"""
    71|        return {
    72|            "total_news": len(self.news_history),
    73|            "max_history": self.max_history,
    74|            "categories": self.categories
    75|        }
    76|
    77|if __name__ == "__main__":
    78|    aggregator = NewsAggregator()
    79|    
    80|    print("=== 新闻聚合器测试 ===")
    81|    
    82|    # 获取新闻
    83|    news = aggregator.fetch_tech_news(limit=5)
    84|    print(f"\n获取到 {len(news)} 条新闻:")
    85|    for n in news:
    86|        print(f"  - {n['title']}")
    87|    
    88|    # 添加到历史
    89|    for n in news:
    90|        aggregator.add_news(n)
    91|    
    92|    print(f"\n历史新闻数: {aggregator.get_stats()}")
    93|    
    94|    # 搜索
    95|    results = aggregator.search_news("AI")
    96|    print(f"\n搜索 'AI' 结果: {len(results)}")
    97|