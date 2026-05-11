     1|#!/usr/bin/env python3
     2|"""
     3|Upgrade Manager - 升级机制脚本
     4|功能：
     5|1. 版本检查
     6|2. 自动升级
     7|3. 回滚机制
     8|4. 升级日志
     9|"""
    10|
    11|import os
    12|import sys
    13|import json
    14|import shutil
    15|import hashlib
    16|from pathlib import Path
    17|from datetime import datetime
    18|from typing import Dict, List, Optional
    19|
    20|# ==================== 配置 ====================
    21|
    22|SCRIPT_DIR = Path.home() / ".real/scripts"
    23|BACKUP_DIR = Path.home() / ".real/backups"
    24|UPGRADE_LOG = Path.home() / ".real/logs/upgrade.log"
    25|
    26|# ==================== 版本管理器 ====================
    27|
    28|class Version:
    29|    def __init__(self, version_str: str):
    30|        self.string = version_str
    31|        parts = version_str.lstrip('v').split('.')
    32|        self.major = int(parts[0]) if len(parts) > 0 else 0
    33|        self.minor = int(parts[1]) if len(parts) > 1 else 0
    34|        self.patch = int(parts[2]) if len(parts) > 2 else 0
    35|    
    36|    def __str__(self):
    37|        return self.string
    38|    
    39|    def __eq__(self, other):
    40|        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)
    41|    
    42|    def __lt__(self, other):
    43|        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
    44|    
    45|    def __le__(self, other):
    46|        return self == other or self < other
    47|    
    48|    def __gt__(self, other):
    49|        return (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch)
    50|    
    51|    def __ge__(self, other):
    52|        return self == other or self > other
    53|
    54|class UpgradeManager:
    55|    def __init__(self):
    56|        self.backup_dir = BACKUP_DIR
    57|        self.backup_dir.mkdir(parents=True, exist_ok=True)
    58|        self.scripts = self._scan_scripts()
    59|    
    60|    def _scan_scripts(self) -> Dict[str, str]:
    61|        """扫描脚本目录"""
    62|        scripts = {}
    63|        
    64|        if SCRIPT_DIR.exists():
    65|            for script_file in SCRIPT_DIR.glob("*.py"):
    66|                scripts[script_file.name] = str(script_file)
    67|        
    68|        return scripts
    69|    
    70|    def get_script_version(self, script_name: str) -> Optional[str]:
    71|        """获取脚本版本"""
    72|        script_path = SCRIPT_DIR / script_name
    73|        
    74|        if not script_path.exists():
    75|            return None
    76|        
    77|        with open(script_path, 'r') as f:
    78|            for line in f:
    79|                if line.startswith("__version__"):
    80|                    return line.split("=")[1].strip().strip('"').strip("'")
    81|        
    82|        return None
    83|    
    84|    def create_backup(self, script_name: str = None) -> Optional[str]:
    85|        """创建备份"""
    86|        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    87|        
    88|        if script_name:
    89|            script_path = SCRIPT_DIR / script_name
    90|            if not script_path.exists():
    91|                return None
    92|            
    93|            backup_name = f"{script_name}.{timestamp}.bak"
    94|            backup_path = self.backup_dir / backup_name
    95|            
    96|            shutil.copy2(script_path, backup_path)
    97|            
    98|            # 计算hash
    99|            with open(backup_path, 'rb') as f:
   100|                hash_value = hashlib.md5(f.read()).hexdigest()
   101|            
   102|            # 记录备份信息
   103|            self._log_upgrade("backup", {
   104|                "script": script_name,
   105|                "backup": str(backup_path),
   106|                "hash": hash_value
   107|            })
   108|            
   109|            return str(backup_path)
   110|        
   111|        else:
   112|            # 备份所有脚本
   113|            backup_name = f"all_scripts.{timestamp}.bak"
   114|            backup_path = self.backup_dir / backup_name
   115|            backup_path.mkdir(exist_ok=True)
   116|            
   117|            for script_path in SCRIPT_DIR.glob("*.py"):
   118|                shutil.copy2(script_path, backup_path / script_path.name)
   119|            
   120|            self._log_upgrade("backup_all", {"backup": str(backup_path)})
   121|            
   122|            return str(backup_path)
   123|    
   124|    def restore_backup(self, backup_path: str, script_name: str = None) -> bool:
   125|        """恢复备份"""
   126|        backup = Path(backup_path)
   127|        
   128|        if not backup.exists():
   129|            return False
   130|        
   131|        try:
   132|            if backup.is_file():
   133|                # 单文件恢复
   134|                target = SCRIPT_DIR / (script_name or backup.name.replace(f".{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak", ""))
   135|                shutil.copy2(backup, target)
   136|            elif backup.is_dir():
   137|                # 目录恢复
   138|                for script_path in backup.glob("*.py"):
   139|                    shutil.copy2(script_path, SCRIPT_DIR / script_path.name)
   140|            
   141|            self._log_upgrade("restore", {
   142|                "backup": str(backup),
   143|                "script": script_name
   144|            })
   145|            
   146|            return True
   147|        
   148|        except Exception as e:
   149|            self._log_upgrade("restore_error", {"error": str(e)})
   150|            return False
   151|    
   152|    def list_backups(self) -> List[Dict]:
   153|        """列出备份"""
   154|        backups = []
   155|        
   156|        for backup in sorted(self.backup_dir.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True):
   157|            backups.append({
   158|                "name": backup.name,
   159|                "path": str(backup),
   160|                "size": backup.stat().st_size,
   161|                "modified": datetime.fromtimestamp(backup.stat().st_mtime).isoformat(),
   162|                "type": "file" if backup.is_file() else "directory"
   163|            })
   164|        
   165|        return backups
   166|    
   167|    def check_upgrade(self) -> Dict:
   168|        """检查升级"""
   169|        # 这里简化处理，实际应连接远程仓库检查
   170|        return {
   171|            "current_version": "1.1.0",
   172|            "latest_version": "1.1.0",
   173|            "update_available": False,
   174|            "scripts": len(self.scripts)
   175|        }
   176|    
   177|    def _log_upgrade(self, action: str, details: Dict):
   178|        """记录升级日志"""
   179|        UPGRADE_LOG.parent.mkdir(parents=True, exist_ok=True)
   180|        
   181|        with open(UPGRADE_LOG, 'a') as f:
   182|            log_entry = {
   183|                "timestamp": datetime.now().isoformat(),
   184|                "action": action,
   185|                "details": details
   186|            }
   187|            f.write(json.dumps(log_entry) + "\n")
   188|
   189|# ==================== 主函数 ====================
   190|
   191|def main():
   192|    manager = UpgradeManager()
   193|    
   194|    if len(sys.argv) < 2:
   195|        print("Usage:")
   196|        print("  upgrade_manager.py check")
   197|        print("  upgrade_manager.py backup [script_name]")
   198|        print("  upgrade_manager.py restore <backup_path> [script_name]")
   199|        print("  upgrade_manager.py list")
   200|        print("  upgrade_manager.py version [script_name]")
   201|        sys.exit(1)
   202|    
   203|    command = sys.argv[1]
   204|    
   205|    if command == "check":
   206|        result = manager.check_upgrade()
   207|        print(json.dumps(result, indent=2, ensure_ascii=False))
   208|    
   209|    elif command == "backup":
   210|        script_name = sys.argv[2] if len(sys.argv) > 2 else None
   211|        backup_path = manager.create_backup(script_name)
   212|        
   213|        if backup_path:
   214|            print(f"备份成功: {backup_path}")
   215|        else:
   216|            print("备份失败")
   217|    
   218|    elif command == "restore":
   219|        backup_path = sys.argv[2] if len(sys.argv) > 2 else ""
   220|        script_name = sys.argv[3] if len(sys.argv) > 3 else None
   221|        
   222|        if manager.restore_backup(backup_path, script_name):
   223|            print("恢复成功")
   224|        else:
   225|            print("恢复失败")
   226|    
   227|    elif command == "list":
   228|        backups = manager.list_backups()
   229|        print(f"备份列表 ({len(backups)}个):")
   230|        for backup in backups[:10]:
   231|            print(f"  {backup['modified'][:19]} - {backup['name']} ({backup['size']} bytes)")
   232|    
   233|    elif command == "version":
   234|        script_name = sys.argv[2] if len(sys.argv) > 2 else None
   235|        if script_name:
   236|            version = manager.get_script_version(script_name)
   237|            print(f"{script_name}: {version or '未知版本'}")
   238|        else:
   239|            print("脚本版本:")
   240|            for name in sorted(manager.scripts.keys()):
   241|                version = manager.get_script_version(name)
   242|                print(f"  {name}: {version or '未知版本'}")
   243|    
   244|    else:
   245|        print(f"Unknown command: {command}")
   246|
   247|if __name__ == "__main__":
   248|    main()
   249|