     1|#!/usr/bin/env python3
     2|"""
     3|Hermes Agent × ClawShell 集成模块
     4|====================================
     5|将 Hermes Agent 接入 ClawShell 生态，作为"前脑/进化引擎"
     6|
     7|功能:
     8|1. 向 ClawShell NodeRegistry 注册为 HERMES 节点
     9|2. 通过文件系统 EventBus 与悟空双向通信
    10|3. 消费悟空事件，生成洞察/技能/模式识别
    11|4. 发布 Hermes 洞察回 EventBus
    12|
    13|# 通信方式:
    14|- 文件系统 EventBus: ~/.real/eventbus/events/YYYY-MM-DD/
    15|- 事件格式: JSON，符合 ClawshellEvent/HermesEvent 规范
    16|"""
    17|
    18|import sys
    19|import json
    20|import time
    21|import uuid
    22|import threading
    23|from pathlib import Path
    24|from datetime import datetime
    25|from typing import Dict, List, Optional, Callable
    26|from dataclasses import dataclass, field
    27|
    28|# ClawShell 路径 (动态检测，支持WSL/Windows/macOS)
    29|CLAWSHELL_PATH = Path(os.environ.get("CLAWSHELL_ROOT", str(Path.home() / ".ClawShell")))
    30|sys.path.insert(0, str(CLAWSHELL_PATH))
    31|
    32|# 导入 ClawShell 组件
    33|try:
    34|    from lib.layer4.node_registry import NodeRegistry, NodeType, NodeStatus
    35|    from lib.core.eventbus.schema import Event, EventType, EventSource
    36|    from lib.core.eventbus.core import EventBus, get_eventbus
    37|    CLAWSHELL_AVAILABLE = True
    38|except ImportError as e:
    39|    print(f"[WARN] ClawShell 导入失败: {e}")
    40|    CLAWSHELL_AVAILABLE = False
    41|
    42|
    43|# ============ 配置 ============
    44|
    45|# 修正后的路径: 悟空实际 EventBus 路径
    46|EVENTBUS_DIR = Path.home() / ".real" / "eventbus"
    47|EVENTBUS_EVENTS_DIR = EVENTBUS_DIR / "events"
    48|EVENTBUS_CONDITIONS_DIR = EVENTBUS_DIR / "conditions"
    49|EVENTBUS_DEADLETTER_DIR = EVENTBUS_DIR / "dead_letter"
    50|
    51|# NodeRegistry 实际路径
    52|NODEREGISTRY_PATH = Path.home() / ".real" / ".node_registry.json"
    53|
    54|HERMES_NODE_ID = "hermes-agent-primary"
    55|HERMES_NODE_NAME = "Hermes Agent (前脑进化引擎)"
    56|POLL_INTERVAL = 1.0  # 事件轮询间隔(秒)
    57|
    58|
    59|# ============ Hermes 事件定义 ============
    60|
    61|@dataclass
    62|class HermesInsight:
    63|    """Hermes 洞察"""
    64|    insight_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    65|    source_event_id: str = ""
    66|    insight_type: str = "analysis"  # analysis/pattern/skill/review/prediction
    67|    priority: str = "P2"  # P0/P1/P2/P3
    68|    content: str = ""
    69|    recommendations: List[str] = field(default_factory=list)
    70|    confidence: float = 0.8
    71|    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    72|    
    73|    def to_dict(self) -> Dict:
    74|        return {
    75|            "insight_id": self.insight_id,
    76|            "source_event_id": self.source_event_id,
    77|            "insight_type": self.insight_type,
    78|            "priority": self.priority,
    79|            "content": self.content,
    80|            "recommendations": self.recommendations,
    81|            "confidence": self.confidence,
    82|            "timestamp": self.timestamp
    83|        }
    84|
    85|
    86|@dataclass 
    87|class HermesSkill:
    88|    """Hermes 生成的技能"""
    89|    skill_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    90|    name: str = ""
    91|    description: str = ""
    92|    trigger_words: List[str] = field(default_factory=list)
    93|    content: str = ""
    94|    source_event_id: str = ""
    95|    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    96|    
    97|    def to_dict(self) -> Dict:
    98|        return {
    99|            "skill_id": self.skill_id,
   100|            "name": self.name,
   101|            "description": self.description,
   102|            "trigger_words": self.trigger_words,
   103|            "content": self.content,
   104|            "source_event_id": self.source_event_id,
   105|            "timestamp": self.timestamp
   106|        }
   107|
   108|
   109|# ============ Hermes ClawShell 集成器 ============
   110|
   111|class HermesClawShellIntegration:
   112|    """
   113|    Hermes × ClawShell 集成器
   114|    =========================
   115|    
   116|    生态位: 前脑/进化引擎 (Layer 5)
   117|    
   118|    职责:
   119|    - 注册为 ClawShell HERMES 节点
   120|    - 订阅悟空事件 (clawshell.task.*, clawshell.error.*)
   121|    - 生成洞察 (insight.generated)
   122|    - 生成技能 (skill.created)
   123|    - 发布回 EventBus
   124|    """
   125|    
   126|    def __init__(self):
   127|        self.node_registry = NodeRegistry() if CLAWSHELL_AVAILABLE else None
   128|        self.eventbus = get_eventbus() if CLAWSHELL_AVAILABLE else None
   129|        self.node_id = None
   130|        self.running = False
   131|        self.poll_thread = None
   132|        self.processed_events = set()
   133|        
   134|        # 统计
   135|        self.stats = {
   136|            "events_received": 0,
   137|            "insights_generated": 0,
   138|            "skills_generated": 0,
   139|            "patterns_detected": 0
   140|        }
   141|        
   142|        # 回调注册
   143|        self.insight_callbacks: List[Callable] = []
   144|        self.skill_callbacks: List[Callable] = []
   145|    
   146|    def register_to_clawshell(self, capabilities: List[str] = None):
   147|        """
   148|        注册 Hermes 到 ClawShell 节点注册表
   149|        
   150|        节点类型: NodeType.HERMES
   151|        能力: 深度思考、洞察生成、模式识别、技能进化
   152|        """
   153|        if not self.node_registry:
   154|            print("[WARN] NodeRegistry 不可用，跳过注册")
   155|            return None
   156|        
   157|        capabilities = capabilities or [
   158|            "deep_thinking",
   159|            "insight_generation",
   160|            "pattern_recognition",
   161|            "skill_evolution",
   162|            "trend_analysis",
   163|            "review_engine",
   164|            "knowledge_coach"
   165|        ]
   166|        
   167|        self.node_id = self.node_registry.register(
   168|            name=HERMES_NODE_NAME,
   169|            node_type=NodeType.HERMES,
   170|            capabilities=capabilities,
   171|            metadata={
   172|                "role": "front_brain",
   173|                "layer": "L5",
   174|                "version": "1.1.0",
   175|                "integration_type": "eventbus"
   176|            }
   177|        )
   178|        
   179|        print(f"[✓] Hermes 已注册到 ClawShell: {self.node_id}")
   180|        print(f"    节点类型: HERMES")
   181|        print(f"    能力: {capabilities}")
   182|        return self.node_id
   183|    
   184|    def start(self):
   185|        """启动 Hermes 集成服务"""
   186|        if self.running:
   187|            print("[WARN] Hermes 集成已在运行")
   188|            return
   189|        
   190|        self.running = True
   191|        
   192|        # 注册节点
   193|        self.register_to_clawshell()
   194|        
   195|        # 启动事件轮询
   196|        self.poll_thread = threading.Thread(target=self._event_poll_loop, daemon=True)
   197|        self.poll_thread.start()
   198|        
   199|        print("[✓] Hermes × ClawShell 集成已启动")
   200|        print(f"    EventBus 路径: {EVENTBUS_DIR}")
   201|        print(f"    事件目录: {EVENTBUS_EVENTS_DIR}/YYYY-MM-DD/")
   202|        print(f"    NodeRegistry: {NODEREGISTRY_PATH}")
   203|        print(f"    轮询间隔: {POLL_INTERVAL}s")
   204|    
   205|    def stop(self):
   206|        """停止 Hermes 集成服务"""
   207|        self.running = False
   208|        if self.poll_thread:
   209|            self.poll_thread.join(timeout=5)
   210|        
   211|        # 更新节点状态为离线
   212|        if self.node_registry and self.node_id:
   213|            self.node_registry.update_status(self.node_id, NodeStatus.OFFLINE)
   214|        
   215|        print("[✓] Hermes × ClawShell 集成已停止")
   216|    
   217|    def _event_poll_loop(self):
   218|        """事件轮询循环"""
   219|        while self.running:
   220|            try:
   221|                self._poll_clawshell_events()
   222|                time.sleep(POLL_INTERVAL)
   223|            except Exception as e:
   224|                print(f"[ERROR] 轮询错误: {e}")
   225|                time.sleep(5)
   226|    
   227|    def _poll_clawshell_events(self):
   228|        """轮询 ClawShell 事件 - 修正为实际悟空 EventBus 路径"""
   229|        # 悟空实际 EventBus 路径: ~/.real/eventbus/events/YYYY-MM-DD/*.json
   230|        today_str = datetime.now().strftime("%Y-%m-%d")
   231|        today_events_dir = EVENTBUS_EVENTS_DIR / today_str
   232|        
   233|        if not today_events_dir.exists():
   234|            return
   235|        
   236|        # 查找今日所有事件文件
   237|        for event_file in sorted(today_events_dir.glob("*.json")):
   238|            if event_file.name in self.processed_events:
   239|                continue
   240|            
   241|            try:
   242|                with open(event_file, 'r', encoding='utf-8') as f:
   243|                    event_data = json.load(f)
   244|                
   245|                # 处理来自悟空系统的事件 (source 可能是多种标识)
   246|                source = event_data.get("source", "")
   247|                event_type = event_data.get("type", "")
   248|                # 过滤: 不处理 Hermes 自己发布的事件，处理 clawshell/悟空相关事件
   249|                if source == "hermes_agent":
   250|                    pass  # 跳过自己发布的事件
   251|                elif "clawshell." in event_type or "wukong." in event_type or source in [
   252|                    "clawshell", "wukong", "wukong-agent", "mcp_runtime", 
   253|                    "integration-test", "e2e-test", "test_boot", "smoke_test"
   254|                ]:
   255|                    self._handle_clawshell_event(event_data)
   256|                
   257|                self.processed_events.add(event_file.name)
   258|                
   259|            except Exception as e:
   260|                print(f"[ERROR] 处理事件失败: {e}")
   261|    
   262|    def _handle_clawshell_event(self, event_data: Dict):
   263|        """处理 ClawShell 事件"""
   264|        event_type = event_data.get("type", "")
   265|        event_id = event_data.get("id", "")
   266|        
   267|        print(f"[→] 收到事件: {event_type} ({event_id})")
   268|        self.stats["events_received"] += 1
   269|        
   270|        # 根据事件类型生成不同的 Hermes 响应
   271|        if "task.completed" in event_type:
   272|            self._generate_task_review(event_data)
   273|        elif "error.occurred" in event_type or "error.critical" in event_type:
   274|            self._generate_error_analysis(event_data)
   275|        elif "task.started" in event_type:
   276|            self._generate_task_prediction(event_data)
   277|        elif "system.health_check" in event_type:
   278|            self._generate_health_insight(event_data)
   279|        else:
   280|            # 默认分析
   281|            self._generate_general_insight(event_data)
   282|    
   283|    def _generate_task_review(self, event_data: Dict):
   284|        """生成任务复盘洞察"""
   285|        payload = event_data.get("payload", {})
   286|        task_id = payload.get("task_id", "unknown")
   287|        
   288|        insight = HermesInsight(
   289|            source_event_id=event_data.get("id", ""),
   290|            insight_type="review",
   291|            priority="P2",
   292|            content=f"任务 {task_id} 已完成，建议复盘执行过程中的优化点",
   293|            recommendations=[
   294|                "分析任务执行时间是否符合预期",
   295|                "检查是否有重复或可自动化的步骤",
   296|                "评估输出质量是否达到标准"
   297|            ],
   298|            confidence=0.85
   299|        )
   300|        
   301|        self.publish_insight(insight)
   302|    
   303|    def _generate_error_analysis(self, event_data: Dict):
   304|        """生成错误分析洞察"""
   305|        payload = event_data.get("payload", {})
   306|        error = payload.get("error", "unknown error")
   307|        
   308|        insight = HermesInsight(
   309|            source_event_id=event_data.get("id", ""),
   310|            insight_type="analysis",
   311|            priority="P1",  # 高优先级
   312|            content=f"检测到错误: {error}。建议立即分析根因并制定修复方案",
   313|            recommendations=[
   314|                "检查相关组件的日志输出",
   315|                "验证环境配置是否正确",
   316|                "评估是否需要回滚到稳定版本"
   317|            ],
   318|            confidence=0.9
   319|        )
   320|        
   321|        self.publish_insight(insight)
   322|    
   323|    def _generate_task_prediction(self, event_data: Dict):
   324|        """生成任务预测洞察"""
   325|        payload = event_data.get("payload", {})
   326|        task_type = payload.get("task_type", "unknown")
   327|        
   328|        insight = HermesInsight(
   329|            source_event_id=event_data.get("id", ""),
   330|            insight_type="prediction",
   331|            priority="P3",
   332|            content=f"任务类型 '{task_type}' 已开始，基于历史数据预测可能的风险点",
   333|            recommendations=[
   334|                "监控资源使用情况",
   335|                "准备备用执行方案",
   336|                "设置关键检查点"
   337|            ],
   338|            confidence=0.75
   339|        )
   340|        
   341|        self.publish_insight(insight)
   342|    
   343|    def _generate_health_insight(self, event_data: Dict):
   344|        """生成健康检查洞察"""
   345|        payload = event_data.get("payload", {})
   346|        
   347|        insight = HermesInsight(
   348|            source_event_id=event_data.get("id", ""),
   349|            insight_type="analysis",
   350|            priority="P2",
   351|            content="系统健康检查完成，生成优化建议",
   352|            recommendations=[
   353|                "定期清理过期日志文件",
   354|                "优化高频任务的执行策略",
   355|                "评估新技能的引入价值"
   356|            ],
   357|            confidence=0.8
   358|        )
   359|        
   360|        self.publish_insight(insight)
   361|    
   362|    def _generate_general_insight(self, event_data: Dict):
   363|        """生成通用洞察"""
   364|        event_type = event_data.get("type", "")
   365|        
   366|        insight = HermesInsight(
   367|            source_event_id=event_data.get("id", ""),
   368|            insight_type="analysis",
   369|            priority="P3",
   370|            content=f"收到事件 '{event_type}'，已记录供后续模式分析",
   371|            recommendations=["等待更多数据以识别模式"],
   372|            confidence=0.6
   373|        )
   374|        
   375|        self.publish_insight(insight)
   376|    
   377|    def publish_insight(self, insight: HermesInsight):
   378|        """
   379|        发布洞察到 EventBus - 修正为悟空实际 EventBus 路径
   380|        
   381|        写入: ~/.real/eventbus/events/YYYY-MM-DD/hermes_*.json
   382|        """
   383|        today_str = datetime.now().strftime("%Y-%m-%d")
   384|        today_events_dir = EVENTBUS_EVENTS_DIR / today_str
   385|        today_events_dir.mkdir(parents=True, exist_ok=True)
   386|        
   387|        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
   388|        filename = f"{timestamp}_hermes_{insight.insight_id}.json"
   389|        filepath = today_events_dir / filename
   390|        
   391|        event_data = {
   392|            "id": insight.insight_id,
   393|            "type": "hermes.insight.generated",
   394|            "source": "hermes_agent",
   395|            "timestamp": insight.timestamp,
   396|            "payload": insight.to_dict(),
   397|            "trace_id": insight.source_event_id,
   398|            "tags": ["insight", insight.insight_type, insight.priority]
   399|        }
   400|        
   401|        with open(filepath, 'w', encoding='utf-8') as f:
   402|            json.dump(event_data, f, ensure_ascii=False, indent=2)
   403|        
   404|        self.stats["insights_generated"] += 1
   405|        print(f"[←] 发布洞察: {insight.insight_type} ({insight.insight_id})")
   406|        
   407|        # 触发回调
   408|        for callback in self.insight_callbacks:
   409|            try:
   410|                callback(insight)
   411|            except Exception as e:
   412|                print(f"[ERROR] 洞察回调错误: {e}")
   413|    
   414|    def publish_skill(self, skill: HermesSkill):
   415|        """
   416|        发布技能到 EventBus - 修正为悟空实际 EventBus 路径
   417|        """
   418|        today_str = datetime.now().strftime("%Y-%m-%d")
   419|        today_events_dir = EVENTBUS_EVENTS_DIR / today_str
   420|        today_events_dir.mkdir(parents=True, exist_ok=True)
   421|        
   422|        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
   423|        filename = f"{timestamp}_hermes_skill_{skill.skill_id}.json"
   424|        filepath = today_events_dir / filename
   425|        
   426|        event_data = {
   427|            "id": skill.skill_id,
   428|            "type": "hermes.skill.created",
   429|            "source": "hermes_agent",
   430|            "timestamp": skill.timestamp,
   431|            "payload": skill.to_dict(),
   432|            "tags": ["skill", skill.name]
   433|        }
   434|        
   435|        with open(filepath, 'w', encoding='utf-8') as f:
   436|            json.dump(event_data, f, ensure_ascii=False, indent=2)
   437|        
   438|        self.stats["skills_generated"] += 1
   439|        print(f"[←] 发布技能: {skill.name} ({skill.skill_id})")
   440|        
   441|        # 触发回调
   442|        for callback in self.skill_callbacks:
   443|            try:
   444|                callback(skill)
   445|            except Exception as e:
   446|                print(f"[ERROR] 技能回调错误: {e}")
   447|    
   448|    def _archive_event(self, event_file: Path):
   449|        """归档已处理的事件文件"""
   450|        archive_dir = EVENTBUS_DIR / "archive"
   451|        archive_dir.mkdir(exist_ok=True)
   452|        
   453|        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
   454|        archived_name = f"{timestamp}_{event_file.name}"
   455|        
   456|        try:
   457|            event_file.rename(archive_dir / archived_name)
   458|        except Exception:
   459|            pass  # 如果移动失败，忽略
   460|    
   461|    def get_stats(self) -> Dict:
   462|        """获取统计信息"""
   463|        return {
   464|            **self.stats,
   465|            "node_id": self.node_id,
   466|            "running": self.running,
   467|            "processed_events": len(self.processed_events)
   468|        }
   469|    
   470|    def register_insight_callback(self, callback: Callable):
   471|        """注册洞察回调"""
   472|        self.insight_callbacks.append(callback)
   473|    
   474|    def register_skill_callback(self, callback: Callable):
   475|        """注册技能回调"""
   476|        self.skill_callbacks.append(callback)
   477|
   478|
   479|# ============ 快捷函数 ============
   480|
   481|def create_hermes_integration() -> HermesClawShellIntegration:
   482|    """创建并返回 Hermes ClawShell 集成器"""
   483|    return HermesClawShellIntegration()
   484|
   485|
   486|def publish_hermes_insight(content: str, insight_type: str = "analysis", 
   487|                          priority: str = "P2", recommendations: List[str] = None):
   488|    """快捷发布 Hermes 洞察"""
   489|    integration = HermesClawShellIntegration()
   490|    
   491|    insight = HermesInsight(
   492|        insight_type=insight_type,
   493|        priority=priority,
   494|        content=content,
   495|        recommendations=recommendations or []
   496|    )
   497|    
   498|    integration.publish_insight(insight)
   499|    return insight.insight_id
   500|
   501|
   502|def publish_hermes_skill(name: str, description: str, content: str, trigger_words: List[str] = None):
   503|    """快捷发布 Hermes 技能"""
   504|    integration = HermesClawShellIntegration()
   505|    
   506|    skill = HermesSkill(
   507|        name=name,
   508|        description=description,
   509|        content=content,
   510|        trigger_words=trigger_words or []
   511|    )
   512|    
   513|    integration.publish_skill(skill)
   514|    return skill.skill_id
   515|
   516|
   517|# ============ 主入口 ============
   518|
   519|if __name__ == "__main__":
   520|    print("=" * 60)
   521|    print("Hermes Agent × ClawShell 集成模块")
   522|    print("=" * 60)
   523|    
   524|    # 创建集成器
   525|    hermes = HermesClawShellIntegration()
   526|    
   527|    # 启动
   528|    hermes.start()
   529|    
   530|    # 保持运行
   531|    try:
   532|        while hermes.running:
   533|            time.sleep(10)
   534|            stats = hermes.get_stats()
   535|            print(f"\n[STATS] 事件: {stats['events_received']}, "
   536|                  f"洞察: {stats['insights_generated']}, "
   537|                  f"技能: {stats['skills_generated']}")
   538|    except KeyboardInterrupt:
   539|        print("\n[INFO] 用户中断")
   540|    finally:
   541|        hermes.stop()
   542|