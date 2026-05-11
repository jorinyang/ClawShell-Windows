#!/usr/bin/env python3
"""
跨环境启动脚本：WSL Hermes → Windows browser-runtime + MCP Server
===============================================================

功能：
1. 在 Windows 环境中启动 browser-runtime（使用 Windows 的 Node.js）
2. 在 Windows 环境中启动 hermes_mcp_server.py（使用 Windows 的 Python）
3. 提供健康检查和自动重启
4. 支持 WSL 和 Windows 双向通信

使用方法：
    python3 wsl_windows_launcher.py [start|stop|status|restart]

位置: /mnt/c/Users/Aorus/.ClawShell/wsl_windows_launcher.py
"""

import sys
import os
import json
import time
import signal
import socket
import subprocess
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, List

# ─────────────────────────────────────────────────────────────────────────────
# 配置
# ─────────────────────────────────────────────────────────────────────────────

CONFIG = {
    # Windows 路径（通过 WSL 挂载访问）
    "windows_node": "D:\\Program Files\\nodejs\\node.exe",
    "windows_npm": "D:\\Program Files\\nodejs\\npm.cmd",
    "windows_python": "C:\\Users\\Aorus\\AppData\\Local\\Programs\\Python\\Python311\\python.exe",
    
    # 项目路径
    "browser_runtime_windows": "C:\\Users\\Aorus\\.real\\.bin\\browser-runtime",
    "browser_runtime_wsl": "/mnt/c/Users/Aorus/.real/.bin/browser-runtime",
    "mcp_server_windows": "C:\\Users\\Aorus\\.real\\users\\user-bd1b229d4eff8f6a45c456149072cb3b\\workspace\\tmp\\hermes_mcp_server.py",
    "mcp_server_wsl": "/mnt/c/Users/Aorus/.real/users/user-bd1b229d4eff8f6a45c456149072cb3b/workspace/tmp/hermes_mcp_server.py",
    
    # 端口
    "browser_runtime_port": 4240,
    "mcp_server_port": 47833,
    
    # 日志
    "log_dir_wsl": "/mnt/c/Users/Aorus/.real/logs",
    "pid_file_wsl": "/mnt/c/Users/Aorus/.real/.launcher.pid",
}

# ─────────────────────────────────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────────────────────────────────

def wsl_to_windows_path(wsl_path: str) -> str:
    """将 WSL 路径转换为 Windows 路径"""
    if wsl_path.startswith("/mnt/"):
        drive = wsl_path[5].upper()
        path_part = wsl_path[6:].replace('/', chr(92))  # chr(92) = backslash
        return f"{drive}:{path_part}"
    return wsl_path

def windows_to_wsl_path(win_path: str) -> str:
    """将 Windows 路径转换为 WSL 路径"""
    if len(win_path) >= 2 and win_path[1] == ":":
        drive = win_path[0].lower()
        path_part = win_path[2:].replace(chr(92), '/')
        return f"/mnt/{drive}/{path_part}"
    return win_path

def run_windows_command(cmd: List[str], cwd: Optional[str] = None, 
                        background: bool = False, log_file: Optional[str] = None) -> subprocess.Popen:
    """
    在 Windows 环境中执行命令
    
    Args:
        cmd: Windows 命令（使用 Windows 路径）
        cwd: Windows 工作目录
        background: 是否后台运行
        log_file: 日志文件路径（WSL 路径）
    """
    # 使用 cmd.exe /c 执行 Windows 命令
    full_cmd = ["cmd.exe", "/c"]
    
    # 如果有工作目录，先 cd
    if cwd:
        full_cmd.append(f"cd /d {cwd} &&")
    
    full_cmd.extend(cmd)
    
    if background:
        # 后台运行，重定向输出到日志
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_file, 'w') as f:
                process = subprocess.Popen(
                    full_cmd,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    start_new_session=True
                )
            return process
        else:
            process = subprocess.Popen(
                full_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            return process
    else:
        return subprocess.Popen(full_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def check_port(port: int, host: str = "127.0.0.1") -> bool:
    """检查端口是否被监听"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            result = s.connect_ex((host, port))
            return result == 0
    except:
        return False

def save_pid(pid: int, service: str):
    """保存 PID 到文件"""
    pid_file = Path(CONFIG["pid_file_wsl"])
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    
    pids = {}
    if pid_file.exists():
        try:
            pids = json.loads(pid_file.read_text(encoding='utf-8'))
        except:
            pids = {}
    
    pids[service] = {
        "pid": pid,
        "timestamp": time.time(),
        "command": f"{service}_windows"
    }
    
    pid_file.write_text(json.dumps(pids, indent=2), encoding='utf-8')

def load_pids() -> Dict[str, Any]:
    """加载保存的 PID"""
    pid_file = Path(CONFIG["pid_file_wsl"])
    if pid_file.exists():
        try:
            return json.loads(pid_file.read_text(encoding='utf-8'))
        except:
            return {}
    return {}

def kill_windows_process(pid: int):
    """终止 Windows 进程"""
    try:
        subprocess.run(["cmd.exe", "/c", f"taskkill /PID {pid} /F /T"], 
                      capture_output=True, timeout=10)
        return True
    except Exception as e:
        print(f"[ERROR] 终止进程 {pid} 失败: {e}")
        return False

# ─────────────────────────────────────────────────────────────────────────────
# 服务管理
# ─────────────────────────────────────────────────────────────────────────────

class ServiceManager:
    """跨环境服务管理器"""
    
    def __init__(self):
        self.processes = {}
        self.log_dir = Path(CONFIG["log_dir_wsl"])
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def start_browser_runtime(self) -> Dict[str, Any]:
        """
        在 Windows 环境中启动 browser-runtime
        
        使用 Windows 的 Node.js 直接运行，避免 WSL/Windows 二进制兼容问题
        """
        print("[browser-runtime] 正在 Windows 环境中启动...")
        
        # 检查端口
        if check_port(CONFIG["browser_runtime_port"]):
            print(f"[browser-runtime] 端口 {CONFIG['browser_runtime_port']} 已被占用，可能已运行")
            return {"status": "already_running", "port": CONFIG["browser_runtime_port"]}
        
        # 构建启动命令
        # 使用 npm run start:node 或直接 node --import tsx
        log_file = str(self.log_dir / "browser-runtime.log")
        
        # 方法1: 使用 npm run start:node
        cmd = ["npm.cmd", "run", "start:node"]
        
        # 方法2: 直接使用 node + tsx（如果 npm 有问题）
        # cmd = [CONFIG["windows_node"], "--import", "tsx", "src/main.ts"]
        
        try:
            process = run_windows_command(
                cmd,
                cwd=CONFIG["browser_runtime_windows"],
                background=True,
                log_file=log_file
            )
            
            # 保存 PID
            save_pid(process.pid, "browser_runtime")
            self.processes["browser_runtime"] = process
            
            # 等待启动
            print(f"[browser-runtime] PID: {process.pid}，等待启动...")
            time.sleep(5)
            
            # 检查端口
            if check_port(CONFIG["browser_runtime_port"]):
                print(f"[browser-runtime] ✅ 启动成功，端口 {CONFIG['browser_runtime_port']} 已监听")
                return {
                    "status": "started",
                    "pid": process.pid,
                    "port": CONFIG["browser_runtime_port"],
                    "log": log_file
                }
            else:
                print(f"[browser-runtime] ⚠️ 端口未监听，检查日志...")
                # 读取日志最后几行
                try:
                    log_path = Path(log_file)
                    if log_path.exists():
                        log_content = log_path.read_text(encoding='utf-8', errors='ignore')
                        last_lines = '\n'.join(log_content.split('\n')[-20:])
                        print(f"[browser-runtime] 日志最后20行:\n{last_lines}")
                except Exception as e:
                    print(f"[browser-runtime] 读取日志失败: {e}")
                
                return {
                    "status": "maybe_started",
                    "pid": process.pid,
                    "port": CONFIG["browser_runtime_port"],
                    "log": log_file,
                    "warning": "端口未立即监听，可能正在启动中"
                }
                
        except Exception as e:
            print(f"[browser-runtime] ❌ 启动失败: {e}")
            return {"status": "failed", "error": str(e)}
    
    def start_mcp_server(self) -> Dict[str, Any]:
        """
        在 Windows 环境中启动 hermes_mcp_server.py
        
        使用 Windows 的 Python 运行，确保与悟空的 Windows 环境兼容
        """
        print("[mcp-server] 正在 Windows 环境中启动...")
        
        # 检查端口
        if check_port(CONFIG["mcp_server_port"]):
            print(f"[mcp-server] 端口 {CONFIG['mcp_server_port']} 已被占用，可能已运行")
            return {"status": "already_running", "port": CONFIG["mcp_server_port"]}
        
        log_file = str(self.log_dir / "hermes-mcp-server.log")
        
        # 构建启动命令
        # 使用 Windows Python 运行 MCP Server
        cmd = [
            CONFIG["windows_python"],
            CONFIG["mcp_server_windows"]
        ]
        
        try:
            process = run_windows_command(
                cmd,
                background=True,
                log_file=log_file
            )
            
            # 保存 PID
            save_pid(process.pid, "mcp_server")
            self.processes["mcp_server"] = process
            
            print(f"[mcp-server] PID: {process.pid}，等待启动...")
            time.sleep(3)
            
            # 检查端口
            if check_port(CONFIG["mcp_server_port"]):
                print(f"[mcp-server] ✅ 启动成功，端口 {CONFIG['mcp_server_port']} 已监听")
                return {
                    "status": "started",
                    "pid": process.pid,
                    "port": CONFIG["mcp_server_port"],
                    "log": log_file
                }
            else:
                return {
                    "status": "maybe_started",
                    "pid": process.pid,
                    "port": CONFIG["mcp_server_port"],
                    "log": log_file,
                    "warning": "端口未立即监听，可能正在启动中"
                }
                
        except Exception as e:
            print(f"[mcp-server] ❌ 启动失败: {e}")
            return {"status": "failed", "error": str(e)}
    
    def stop_all(self) -> Dict[str, Any]:
        """停止所有服务"""
        results = {}
        pids = load_pids()
        
        for service, info in pids.items():
            pid = info.get("pid")
            if pid:
                print(f"[{service}] 正在停止进程 {pid}...")
                if kill_windows_process(pid):
                    results[service] = {"status": "stopped", "pid": pid}
                else:
                    results[service] = {"status": "failed_to_stop", "pid": pid}
        
        # 清理 PID 文件
        pid_file = Path(CONFIG["pid_file_wsl"])
        if pid_file.exists():
            pid_file.unlink()
        
        return results
    
    def check_status(self) -> Dict[str, Any]:
        """检查所有服务状态"""
        return {
            "browser_runtime": {
                "port": CONFIG["browser_runtime_port"],
                "listening": check_port(CONFIG["browser_runtime_port"]),
                "pid_info": load_pids().get("browser_runtime", {})
            },
            "mcp_server": {
                "port": CONFIG["mcp_server_port"],
                "listening": check_port(CONFIG["mcp_server_port"]),
                "pid_info": load_pids().get("mcp_server", {})
            },
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def start_all(self) -> Dict[str, Any]:
        """启动所有服务"""
        print("=" * 60)
        print("跨环境启动: WSL Hermes → Windows Services")
        print("=" * 60)
        
        results = {
            "browser_runtime": self.start_browser_runtime(),
            "mcp_server": self.start_mcp_server(),
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 显示状态摘要
        print("\n" + "=" * 60)
        print("启动结果摘要")
        print("=" * 60)
        for service, result in results.items():
            if service == "timestamp":
                continue
            status = result.get("status", "unknown")
            icon = "✅" if status == "started" else "⚠️" if status == "already_running" else "❌"
            print(f"{icon} {service}: {status}")
            if "port" in result:
                print(f"   端口: {result['port']}")
            if "pid" in result:
                print(f"   PID: {result['pid']}")
            if "log" in result:
                wsl_log = windows_to_wsl_path(result['log']) if '\\' in str(result['log']) else result['log']
                print(f"   日志: {wsl_log}")
        
        return results

# ─────────────────────────────────────────────────────────────────────────────
# 命令行接口
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="跨环境启动脚本：WSL Hermes → Windows browser-runtime + MCP Server"
    )
    parser.add_argument(
        "command",
        choices=["start", "stop", "status", "restart", "logs"],
        help="要执行的命令"
    )
    parser.add_argument(
        "--service",
        choices=["browser_runtime", "mcp_server", "all"],
        default="all",
        help="指定服务（默认: all）"
    )
    
    args = parser.parse_args()
    
    manager = ServiceManager()
    
    if args.command == "start":
        if args.service == "all":
            result = manager.start_all()
        elif args.service == "browser_runtime":
            result = manager.start_browser_runtime()
        elif args.service == "mcp_server":
            result = manager.start_mcp_server()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "stop":
        result = manager.stop_all()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "status":
        result = manager.check_status()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "restart":
        print("正在停止所有服务...")
        manager.stop_all()
        time.sleep(2)
        print("正在启动所有服务...")
        result = manager.start_all()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "logs":
        log_dir = Path(CONFIG["log_dir_wsl"])
        print(f"日志目录: {log_dir}")
        if log_dir.exists():
            for log_file in log_dir.glob("*.log"):
                print(f"\n{'='*40}")
                print(f"日志文件: {log_file.name}")
                print(f"{'='*40}")
                try:
                    content = log_file.read_text(encoding='utf-8', errors='ignore')
                    lines = content.split('\n')
                    # 显示最后50行
                    for line in lines[-50:]:
                        print(line)
                except Exception as e:
                    print(f"读取失败: {e}")

if __name__ == "__main__":
    main()
