     1|#!/usr/bin/env python3
     2|"""
     3|ClawShell Adaptive Controller
     4|自适应控制器 - Phase 3
     5|版本: v1.1.0
     6|功能: 实时监控+动态调节(神经反馈机制)
     7|"""
     8|
     9|import time
    10|import threading
    11|from typing import Dict, List, Optional, Callable, Any
    12|from dataclasses import dataclass, field
    13|from datetime import datetime
    14|from collections import deque
    15|
    16|@dataclass
    17|class MetricSnapshot:
    18|    """指标快照"""
    19|    timestamp: float
    20|    cpu_percent: float
    21|    memory_percent: float
    22|    response_time: float
    23|    error_rate: float
    24|    throughput: float
    25|
    26|@dataclass
    27|class FeedbackSignal:
    28|    """反馈信号"""
    29|    metric: str
    30|    current: float
    31|    target: float
    32|    deviation: float
    33|    adjustment: float
    34|    applied: bool = False
    35|
    36|class AdaptiveController:
    37|    """
    38|    自适应控制器(神经反馈机制)
    39|    
    40|    功能：
    41|    - 实时性能监控
    42|    - 偏差检测
    43|    - 自动调节
    44|    - 反馈闭环
    45|    """
    46|    
    47|    def __init__(
    48|        self,
    49|        target_response_time: float = 1.0,
    50|        target_error_rate: float = 0.01,
    51|        target_cpu: float = 70.0
    52|    ):
    53|        # 目标值
    54|        self.target_response_time = target_response_time
    55|        self.target_error_rate = target_error_rate
    56|        self.target_cpu = target_cpu
    57|        
    58|        # 当前状态
    59|        self.current_metrics: Dict[str, float] = {}
    60|        self.history: deque = deque(maxlen=100)
    61|        
    62|        # 调节器
    63|        self.adjustments: List[FeedbackSignal] = []
    64|        
    65|        # 回调函数
    66|        self.callbacks: Dict[str, Callable] = {}
    67|        
    68|        # 控制线程
    69|        self._monitoring = False
    70|        self._monitor_thread: Optional[threading.Thread] = None
    71|        
    72|    def set_callback(self, metric: str, callback: Callable[[float], None]):
    73|        """设置调节回调"""
    74|        self.callbacks[metric] = callback
    75|    
    76|    def record_metric(self, metric: str, value: float):
    77|        """记录指标"""
    78|        self.current_metrics[metric] = value
    79|        
    80|        # 记录历史
    81|        snapshot = MetricSnapshot(
    82|            timestamp=time.time(),
    83|            cpu_percent=self.current_metrics.get("cpu", 0),
    84|            memory_percent=self.current_metrics.get("memory", 0),
    85|            response_time=self.current_metrics.get("response_time", 0),
    86|            error_rate=self.current_metrics.get("error_rate", 0),
    87|            throughput=self.current_metrics.get("throughput", 0)
    88|        )
    89|        self.history.append(snapshot)
    90|        
    91|        # 检查偏差
    92|        self._check_deviation(metric, value)
    93|    
    94|    def _check_deviation(self, metric: str, value: float):
    95|        """检查偏差并调节"""
    96|        target = self._get_target(metric)
    97|        if target is None:
    98|            return
    99|        
   100|        deviation = value - target
   101|        deviation_percent = abs(deviation) / target if target > 0 else 0
   102|        
   103|        # 如果偏差超过10%，触发调节
   104|        if deviation_percent > 0.1:
   105|            adjustment = self._calculate_adjustment(metric, value, target, deviation)
   106|            
   107|            signal = FeedbackSignal(
   108|                metric=metric,
   109|                current=value,
   110|                target=target,
   111|                deviation=deviation,
   112|                adjustment=adjustment
   113|            )
   114|            
   115|            self.adjustments.append(signal)
   116|            
   117|            # 应用调节
   118|            self._apply_adjustment(signal)
   119|    
   120|    def _get_target(self, metric: str) -> Optional[float]:
   121|        """获取目标值"""
   122|        targets = {
   123|            "response_time": self.target_response_time,
   124|            "error_rate": self.target_error_rate,
   125|            "cpu": self.target_cpu
   126|        }
   127|        return targets.get(metric)
   128|    
   129|    def _calculate_adjustment(
   130|        self,
   131|        metric: str,
   132|        current: float,
   133|        target: float,
   134|        deviation: float
   135|    ) -> float:
   136|        """计算调节量"""
   137|        # PID控制器的简化版本
   138|        Kp = 0.5  # 比例系数
   139|        
   140|        # 根据指标类型调整
   141|        if metric == "response_time":
   142|            # 响应时间过高，降低负载
   143|            return -deviation * Kp
   144|        elif metric == "error_rate":
   145|            # 错误率过高，启用备用方案
   146|            return -deviation * Kp * 2
   147|        elif metric == "cpu":
   148|            # CPU过高，限流
   149|            return -deviation * Kp * 0.5
   150|        
   151|        return -deviation * Kp
   152|    
   153|    def _apply_adjustment(self, signal: FeedbackSignal):
   154|        """应用调节"""
   155|        if signal.metric in self.callbacks:
   156|            try:
   157|                self.callbacks[signal.metric](signal.adjustment)
   158|                signal.applied = True
   159|            except Exception as e:
   160|                print(f"Failed to apply adjustment: {e}")
   161|    
   162|    def start_monitoring(self, interval: float = 5.0):
   163|        """开始监控"""
   164|        self._monitoring = True
   165|        self._monitor_thread = threading.Thread(
   166|            target=self._monitor_loop,
   167|            args=(interval,),
   168|            daemon=True
   169|        )
   170|        self._monitor_thread.start()
   171|    
   172|    def stop_monitoring(self):
   173|        """停止监控"""
   174|        self._monitoring = False
   175|        if self._monitor_thread:
   176|            self._monitor_thread.join(timeout=1)
   177|    
   178|    def _monitor_loop(self, interval: float):
   179|        """监控循环"""
   180|        while self._monitoring:
   181|            # 检查历史数据
   182|            if len(self.history) >= 10:
   183|                recent = list(self.history)[-10:]
   184|                
   185|                # 计算平均指标
   186|                avg_response = sum(s.response_time for s in recent) / 10
   187|                avg_error = sum(s.error_rate for s in recent) / 10
   188|                
   189|                # 记录
   190|                self.record_metric("response_time", avg_response)
   191|                self.record_metric("error_rate", avg_error)
   192|            
   193|            time.sleep(interval)
   194|    
   195|    def get_status(self) -> Dict[str, Any]:
   196|        """获取状态"""
   197|        return {
   198|            "monitoring": self._monitoring,
   199|            "current_metrics": self.current_metrics,
   200|            "total_adjustments": len(self.adjustments),
   201|            "applied_adjustments": sum(1 for a in self.adjustments if a.applied),
   202|            "targets": {
   203|                "response_time": self.target_response_time,
   204|                "error_rate": self.target_error_rate,
   205|                "cpu": self.target_cpu
   206|            }
   207|        }
   208|
   209|if __name__ == "__main__":
   210|    controller = AdaptiveController()
   211|    
   212|    print("=== 自适应控制器测试 ===")
   213|    
   214|    # 模拟指标记录
   215|    controller.record_metric("response_time", 1.2)
   216|    controller.record_metric("response_time", 0.9)
   217|    controller.record_metric("error_rate", 0.02)
   218|    
   219|    # 设置回调
   220|    def on_high_cpu(adjustment):
   221|        print(f"CPU调节: {adjustment}")
   222|    
   223|    controller.set_callback("cpu", on_high_cpu)
   224|    
   225|    # 测试调节
   226|    controller.record_metric("cpu", 85.0)
   227|    
   228|    print(f"\n状态: {controller.get_status()}")
   229|    print(f"\n调节历史:")
   230|    for adj in controller.adjustments:
   231|        print(f"  {adj.metric}: {adj.current} -> {adj.target} (调整: {adj.adjustment:.2f})")
   232|