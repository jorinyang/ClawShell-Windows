     1|#!/usr/bin/env python3
     2|"""
     3|OpenClaw Skill Sync - 技能同步器
     4|负责轮询检测 Hermes 生成的技能并注册到 OpenClaw
     5|
     6|功能：
     7|1. 扫描 ~/.hermes/skills/generated/ 目录
     8|2. 检测新技能文件
     9|3. 解析 SKILL.md 文件
    10|4. 注册到 OpenClaw 技能系统
    11|5. 处理技能更新和冲突
    12|"""
    13|
    14|import os
    15|import sys
    16|import json
    17|import hashlib
    18|import shutil
    19|from datetime import datetime
    20|from pathlib import Path
    21|from typing import Optional, Dict, Any, List
    22|import logging
    23|
    24|# 配置日志
    25|logging.basicConfig(
    26|    level=logging.INFO,
    27|    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    28|    handlers=[
    29|        logging.FileHandler(Path("~/.real/logs/skill_sync.log").expanduser()),
    30|        logging.StreamHandler(sys.stdout)
    31|    ]
    32|)
    33|logger = logging.getLogger(__name__)
    34|
    35|
    36|class SkillSync:
    37|    """技能同步器"""
    38|    
    39|    def __init__(self):
    40|        self.hermes_skills_dir = Path("~/.hermes/skills/generated").expanduser()
    41|        self.openclaw_skills_dir = Path("~/.real/skills").expanduser()
    42|        self.sync_state_file = Path("~/.real/.skill_sync_state.json").expanduser()
    43|        self.conflicts_dir = Path("~/.real/skills/conflicts").expanduser()
    44|        
    45|        # 确保目录存在
    46|        self.hermes_skills_dir.mkdir(parents=True, exist_ok=True)
    47|        self.openclaw_skills_dir.mkdir(parents=True, exist_ok=True)
    48|        self.conflicts_dir.mkdir(parents=True, exist_ok=True)
    49|        
    50|        # 加载同步状态
    51|        self.sync_state = self._load_sync_state()
    52|    
    53|    def _load_sync_state(self) -> Dict[str, Any]:
    54|        """加载同步状态"""
    55|        if self.sync_state_file.exists():
    56|            try:
    57|                with open(self.sync_state_file, 'r', encoding='utf-8') as f:
    58|                    return json.load(f)
    59|            except Exception as e:
    60|                logger.error(f"加载同步状态失败: {e}")
    61|        return {"synced_skills": {}, "last_sync": None}
    62|    
    63|    def _save_sync_state(self):
    64|        """保存同步状态"""
    65|        try:
    66|            with open(self.sync_state_file, 'w', encoding='utf-8') as f:
    67|                json.dump(self.sync_state, f, ensure_ascii=False, indent=2)
    68|        except Exception as e:
    69|            logger.error(f"保存同步状态失败: {e}")
    70|    
    71|    def _calculate_file_hash(self, file_path: Path) -> str:
    72|        """计算文件哈希"""
    73|        try:
    74|            with open(file_path, 'rb') as f:
    75|                return hashlib.md5(f.read()).hexdigest()
    76|        except Exception as e:
    77|            logger.error(f"计算文件哈希失败 {file_path}: {e}")
    78|            return ""
    79|    
    80|    def _parse_skill_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
    81|        """解析 SKILL.md 文件"""
    82|        try:
    83|            with open(file_path, 'r', encoding='utf-8') as f:
    84|                content = f.read()
    85|            
    86|            # 提取元数据
    87|            skill_info = {
    88|                "name": "",
    89|                "description": "",
    90|                "version": "1.1.0",
    91|                "confidence": 0.0,
    92|                "pattern": {},
    93|                "content": content
    94|            }
    95|            
    96|            # 解析文件名作为技能名
    97|            skill_info["name"] = file_path.stem
    98|            
    99|            # 提取置信度（从文件内容或文件名）
   100|            if "confidence" in content.lower():
   101|                import re
   102|                match = re.search(r'confidence[:\s]+([\d.]+)', content, re.IGNORECASE)
   103|                if match:
   104|                    skill_info["confidence"] = float(match.group(1))
   105|            
   106|            # 提取描述（第一个段落）
   107|            lines = content.split('\n')
   108|            for line in lines:
   109|                line = line.strip()
   110|                if line and not line.startswith('#') and not line.startswith('-'):
   111|                    skill_info["description"] = line[:200]
   112|                    break
   113|            
   114|            return skill_info
   115|            
   116|        except Exception as e:
   117|            logger.error(f"解析技能文件失败 {file_path}: {e}")
   118|            return None
   119|    
   120|    def _detect_conflict(self, skill_name: str, new_skill: Dict[str, Any]) -> Optional[Path]:
   121|        """检测技能冲突"""
   122|        # 检查 OpenClaw 技能目录
   123|        existing_skill = self.openclaw_skills_dir / f"{skill_name}.md"
   124|        if existing_skill.exists():
   125|            return existing_skill
   126|        
   127|        # 检查 Hermes 技能目录（是否已存在不同版本）
   128|        hermes_existing = self.hermes_skills_dir / f"{skill_name}.md"
   129|        if hermes_existing.exists():
   130|            old_hash = self.sync_state["synced_skills"].get(skill_name, {}).get("hash", "")
   131|            new_hash = self._calculate_file_hash(hermes_existing)
   132|            if old_hash and old_hash != new_hash:
   133|                return hermes_existing
   134|        
   135|        return None
   136|    
   137|    def _handle_conflict(self, skill_name: str, new_file: Path, existing_file: Path) -> bool:
   138|        """处理技能冲突"""
   139|        try:
   140|            logger.warning(f"检测到技能冲突: {skill_name}")
   141|            
   142|            # 将冲突文件移动到冲突目录
   143|            conflict_file = self.conflicts_dir / f"{skill_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
   144|            shutil.copy2(existing_file, conflict_file)
   145|            
   146|            # 记录冲突
   147|            conflict_record = {
   148|                "skill_name": skill_name,
   149|                "new_file": str(new_file),
   150|                "existing_file": str(existing_file),
   151|                "conflict_file": str(conflict_file),
   152|                "timestamp": datetime.now().isoformat(),
   153|                "resolution": "merged"
   154|            }
   155|            
   156|            # 保存冲突记录
   157|            conflict_log = self.conflicts_dir / "conflicts.json"
   158|            conflicts = []
   159|            if conflict_log.exists():
   160|                with open(conflict_log, 'r', encoding='utf-8') as f:
   161|                    conflicts = json.load(f)
   162|            conflicts.append(conflict_record)
   163|            with open(conflict_log, 'w', encoding='utf-8') as f:
   164|                json.dump(conflicts, f, ensure_ascii=False, indent=2)
   165|            
   166|            logger.info(f"冲突已记录到: {conflict_log}")
   167|            return True
   168|            
   169|        except Exception as e:
   170|            logger.error(f"处理冲突失败: {e}")
   171|            return False
   172|    
   173|    def _register_skill(self, skill_info: Dict[str, Any], source_file: Path) -> bool:
   174|        """注册技能到 OpenClaw"""
   175|        try:
   176|            skill_name = skill_info["name"]
   177|            target_file = self.openclaw_skills_dir / f"{skill_name}.md"
   178|            
   179|            # 检测冲突
   180|            existing = self._detect_conflict(skill_name, skill_info)
   181|            if existing:
   182|                if not self._handle_conflict(skill_name, source_file, existing):
   183|                    return False
   184|            
   185|            # 复制技能文件
   186|            shutil.copy2(source_file, target_file)
   187|            
   188|            # 创建技能元数据
   189|            metadata = {
   190|                "name": skill_name,
   191|                "description": skill_info["description"],
   192|                "version": skill_info["version"],
   193|                "confidence": skill_info["confidence"],
   194|                "source": "hermes",
   195|                "source_file": str(source_file),
   196|                "registered_at": datetime.now().isoformat(),
   197|                "enabled": True,
   198|                "trigger_count": 0,
   199|                "success_count": 0
   200|            }
   201|            
   202|            # 保存元数据
   203|            metadata_file = self.openclaw_skills_dir / f"{skill_name}.json"
   204|            with open(metadata_file, 'w', encoding='utf-8') as f:
   205|                json.dump(metadata, f, ensure_ascii=False, indent=2)
   206|            
   207|            logger.info(f"技能已注册: {skill_name} (置信度: {skill_info['confidence']})")
   208|            return True
   209|            
   210|        except Exception as e:
   211|            logger.error(f"注册技能失败: {e}")
   212|            return False
   213|    
   214|    def sync(self) -> Dict[str, Any]:
   215|        """执行同步"""
   216|        logger.info("=== 开始技能同步 ===")
   217|        
   218|        result = {
   219|            "synced": 0,
   220|            "updated": 0,
   221|            "conflicts": 0,
   222|            "failed": 0,
   223|            "skills": []
   224|        }
   225|        
   226|        try:
   227|            # 扫描 Hermes 技能目录
   228|            skill_files = list(self.hermes_skills_dir.glob("*.md"))
   229|            logger.info(f"发现 {len(skill_files)} 个技能文件")
   230|            
   231|            for skill_file in skill_files:
   232|                try:
   233|                    skill_name = skill_file.stem
   234|                    file_hash = self._calculate_file_hash(skill_file)
   235|                    
   236|                    # 检查是否已同步
   237|                    if skill_name in self.sync_state["synced_skills"]:
   238|                        old_hash = self.sync_state["synced_skills"][skill_name].get("hash", "")
   239|                        if old_hash == file_hash:
   240|                            logger.debug(f"技能未变化，跳过: {skill_name}")
   241|                            continue
   242|                        else:
   243|                            logger.info(f"技能已更新: {skill_name}")
   244|                    
   245|                    # 解析技能文件
   246|                    skill_info = self._parse_skill_file(skill_file)
   247|                    if not skill_info:
   248|                        result["failed"] += 1
   249|                        continue
   250|                    
   251|                    # 注册技能
   252|                    if self._register_skill(skill_info, skill_file):
   253|                        if skill_name in self.sync_state["synced_skills"]:
   254|                            result["updated"] += 1
   255|                        else:
   256|                            result["synced"] += 1
   257|                        
   258|                        # 更新同步状态
   259|                        self.sync_state["synced_skills"][skill_name] = {
   260|                            "hash": file_hash,
   261|                            "synced_at": datetime.now().isoformat(),
   262|                            "confidence": skill_info["confidence"]
   263|                        }
   264|                        result["skills"].append(skill_name)
   265|                    else:
   266|                        result["failed"] += 1
   267|                        
   268|                except Exception as e:
   269|                    logger.error(f"处理技能文件失败 {skill_file}: {e}")
   270|                    result["failed"] += 1
   271|            
   272|            # 保存同步状态
   273|            self.sync_state["last_sync"] = datetime.now().isoformat()
   274|            self._save_sync_state()
   275|            
   276|            logger.info(f"=== 同步完成: 新增 {result['synced']}, 更新 {result['updated']}, 冲突 {result['conflicts']}, 失败 {result['failed']} ===")
   277|            return result
   278|            
   279|        except Exception as e:
   280|            logger.error(f"同步过程出错: {e}")
   281|            return result
   282|
   283|
   284|def main():
   285|    """主函数"""
   286|    sync = SkillSync()
   287|    result = sync.sync()
   288|    print(json.dumps(result, ensure_ascii=False, indent=2))
   289|    return result["failed"] == 0
   290|
   291|
   292|if __name__ == "__main__":
   293|    sys.exit(0 if main() else 1)
   294|