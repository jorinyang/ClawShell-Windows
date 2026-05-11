#!/usr/bin/env python3
"""
跨环境启动脚本：从 WSL 启动 Windows 中的 browser-runtime 和 hermes_mcp_server
================================================================================

关键发现:
- browser-runtime 在 Windows 中运行，监听 127.0.0.1:4240 和 0.0.0.0:4240
- WSL 中无法通过 127.0.0.1 访问 Windows 服务，必须使用 Windows 主机 IP
- Windows 主机 IP 可通过 WSL 网关获取（通常是 172.x.x.1）
- browser-runtime 需要 Bearer token 认证（默认: dev-browser-token）

用法:
    python3 /mnt/c/Users/Aorus/.ClawShell/scripts/cross_env_launcher.py [command]

命令:
    start-br      启动 Windows 中的 browser-runtime
    start-mcp     启动 WSL 中的 hermes_mcp_server
    start-all     启动两者
    stop-all      停止所有进程
    status        检查状态
    health        健康检查
    test-api      测试 browser-runtime API
"""

import os
import sys
import json
import time
import signal
import socket
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# 配置
# ─────────────────────────────────────────────────────────────────────────────

# 获取 Windows 主机 IP（WSL 网关）
def get_windows_host_ip() -> str:
    """获取 Windows 主机 IP（WSL 网关）"""
    # 方法1: 通过 /etc/resolv.conf (注意：nameserver 可能是 WSL 虚拟网卡，不是 Windows IP)
    # 方法2: 通过 ip route 获取默认网关（这才是 Windows 主机 IP）
    try:
        result = subprocess.run(
            ["ip", "route", "show"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.split('\n'):
            if 'default' in line:
                parts = line.split()
                if 'via' in parts:
                    idx = parts.index('via')
                    if idx + 1 < len(parts):
                        return parts[idx + 1]
    except:
        pass
    
    # 方法3: 通过 /etc/resolv.conf fallback
    try:
        with open("/etc/resolv.conf", "r") as f:
            for line in f:
                if line.startswith("nameserver"):
                    return line.split()[1]
    except:
        pass
    
    # 方法4: 默认 fallback
    return "172.24.48.1"


WIN_IP = get_windows_host_ip()

CONFIG = {
    # Windows 路径（通过 cmd.exe /c 或 powershell.exe 访问）
    "win_browser_runtime": r"C:\Users\Aorus\.real\.bin\browser-runtime",
    "win_node": r"D:\Program Files\nodejs\node.exe",
    "win_npx": r"D:\Program Files\nodejs\npx.cmd",
    
    # WSL 路径（直接访问）
    "wsl_browser_runtime": "/mnt/c/Users/Aorus/.real/.bin/browser-runtime",
    "wsl_mcp_server": "/mnt/c/Users/Aorus/.real/users/user-bd1b229d4eff8f6a45c456149072cb3b/workspace/tmp/hermes_mcp_server.py",
    "wsl_venv_python": "/home/aorus/.hermes/hermes-agent/venv/bin/python3",
    
    # 网络
    "windows_host_ip": WIN_IP,
    "browser_runtime_port": 4240,
    "mcp_server_port": 47833,
    "browser_runtime_token": "dev-browser-token",
    
    # 日志
    "log_dir": "/tmp",
}

# PID 文件（用于追踪启动的进程）
PID_FILE = Path("/tmp/hermes_cross_env_pids.json")


# ─────────────────────────────────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────────────────────────────────

def check_port(port: int, host: str = "127.0.0.1") -> bool:
    """检查端口是否被监听"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        s.connect((host, port))
        s.close()
        return True
    except:
        return False


def run_windows_command(cmd: str, cwd: Optional[str] = None, background: bool = False) -> Tuple[int, str, str]:
    """
    在 Windows 环境中执行命令
    
    Args:
        cmd: 要执行的命令（Windows 格式）
        cwd: 工作目录（Windows 路径）
        background: 是否后台运行
    """
    # 使用 cmd.exe /c 执行 Windows 命令
    if cwd:
        full_cmd = f"cmd.exe /c cd /d {cwd} && {cmd}"
    else:
        full_cmd = f"cmd.exe /c {cmd}"
    
    try:
        result = subprocess.run(
            full_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            encoding='utf-8',
            errors='replace'
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)


def run_windows_powershell(script: str) -> Tuple[int, str, str]:
    """通过 PowerShell 执行命令"""
    # 将 PowerShell 脚本写入临时文件，然后执行
    ps_file = "/mnt/c/tmp/hermes_ps_script.ps1"
    os.makedirs("/mnt/c/tmp", exist_ok=True)
    with open(ps_file, "w", encoding="utf-8") as f:
        f.write(script)
    
    ps_cmd = f'powershell.exe -ExecutionPolicy Bypass -File "C:\\tmp\\hermes_ps_script.ps1"'
    
    try:
        result = subprocess.run(
            ps_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            encoding='utf-8',
            errors='replace'
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)


def kill_windows_process(pid: int) -> bool:
    """终止 Windows 进程"""
    ps_script = f"Stop-Process -Id {pid} -Force"
    rc, _, _ = run_windows_powershell(ps_script)
    return rc == 0


# ─────────────────────────────────────────────────────────────────────────────
# 核心功能
# ─────────────────────────────────────────────────────────────────────────────

class CrossEnvLauncher:
    """跨环境启动器"""
    
    def __init__(self):
        self.pids = self._load_pids()
    
    def _load_pids(self) -> Dict:
        """加载 PID 记录"""
        if PID_FILE.exists():
            try:
                return json.loads(PID_FILE.read_text())
            except:
                pass
        return {"browser_runtime": None, "mcp_server": None}
    
    def _save_pids(self):
        """保存 PID 记录"""
        PID_FILE.write_text(json.dumps(self.pids, indent=2))
    
    def start_browser_runtime(self) -> Dict:
        """
        启动 Windows 中的 browser-runtime
        
        策略:
        1. 检查 Windows 中 node 和 tsx 是否可用
        2. 使用 PowerShell Start-Process 后台启动
        3. 记录 Windows PID
        4. 等待端口就绪（通过 Windows IP 检查）
        """
        print("[CrossEnv] 启动 browser-runtime (Windows)...")
        
        # 检查端口（使用 Windows IP）
        win_ip = CONFIG["windows_host_ip"]
        port = CONFIG["browser_runtime_port"]
        
        if check_port(port, win_ip):
            print(f"  ✅ 端口 {win_ip}:{port} 已在监听，browser-runtime 可能已运行")
            return {"status": "already_running", "port": port, "host": win_ip}
        
        # 构建启动命令
        win_cwd = CONFIG["win_browser_runtime"]
        
        # 使用 PowerShell 后台启动并记录 PID
        ps_script = f"""
$p = Start-Process -FilePath "cmd.exe" -ArgumentList "/c cd /d `{win_cwd}` && npx tsx src/main.ts > C:\\tmp\\br_test.log 2>&1" -PassThru -WindowStyle Hidden
Write-Output $p.Id
"""
        
        rc, stdout, stderr = run_windows_powershell(ps_script)
        
        if rc != 0:
            print(f"  ❌ 启动失败: {stderr}")
            return {"status": "failed", "error": stderr}
        
        # 解析 PID
        win_pid = None
        try:
            lines = stdout.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.isdigit():
                    win_pid = int(line)
                    break
        except:
            pass
        
        print(f"  📝 Windows PID: {win_pid}")
        
        # 等待端口就绪（通过 Windows IP）
        print(f"  ⏳ 等待端口 {win_ip}:{port} 就绪...")
        for i in range(60):  # 最多等待60秒
            if check_port(port, win_ip):
                print(f"  ✅ browser-runtime 已启动")
                print(f"     访问地址: http://{win_ip}:{port}")
                print(f"     认证头: Authorization: Bearer {CONFIG['browser_runtime_token']}")
                
                # 保存 PID
                self.pids["browser_runtime"] = {
                    "win_pid": win_pid,
                    "type": "windows",
                    "port": port,
                    "host": win_ip,
                    "started_at": time.time()
                }
                self._save_pids()
                
                return {
                    "status": "started",
                    "win_pid": win_pid,
                    "port": port,
                    "host": win_ip
                }
            time.sleep(1)
        
        print(f"  ⚠️ 端口未就绪，但进程可能已启动")
        return {"status": "unknown", "win_pid": win_pid}
    
    def start_mcp_server(self) -> Dict:
        """
        启动 hermes_mcp_server
        
        策略:
        1. 在 WSL 中启动（因为 hermes_mcp_server.py 依赖 WSL 的 Python 环境）
        2. 监听 0.0.0.0:47833 以便 Windows 访问
        """
        print("[CrossEnv] 启动 hermes_mcp_server (WSL)...")
        
        # 检查端口
        if check_port(CONFIG["mcp_server_port"]):
            print(f"  ✅ 端口 {CONFIG['mcp_server_port']} 已在监听")
            return {"status": "already_running", "port": CONFIG["mcp_server_port"]}
        
        # 检查 Python 文件
        mcp_path = Path(CONFIG["wsl_mcp_server"])
        if not mcp_path.exists():
            print(f"  ❌ MCP Server 文件不存在: {mcp_path}")
            return {"status": "failed", "error": "File not found"}
        
        # 在 WSL 中后台启动
        python = CONFIG["wsl_venv_python"]
        log_file = f"{CONFIG['log_dir']}/hermes_mcp_server.log"
        
        try:
            # 使用 subprocess.Popen 后台启动
            process = subprocess.Popen(
                [python, str(mcp_path)],
                stdout=open(log_file, "w"),
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
            
            wsl_pid = process.pid
            print(f"  📝 WSL PID: {wsl_pid}")
            
            # 等待端口就绪
            print(f"  ⏳ 等待端口 {CONFIG['mcp_server_port']} 就绪...")
            for i in range(15):
                if check_port(CONFIG["mcp_server_port"]):
                    print(f"  ✅ MCP Server 已启动，端口 {CONFIG['mcp_server_port']} 监听中")
                    
                    self.pids["mcp_server"] = {
                        "wsl_pid": wsl_pid,
                        "type": "wsl",
                        "port": CONFIG["mcp_server_port"],
                        "started_at": time.time()
                    }
                    self._save_pids()
                    
                    return {
                        "status": "started",
                        "wsl_pid": wsl_pid,
                        "port": CONFIG["mcp_server_port"]
                    }
                time.sleep(1)
            
            print(f"  ⚠️ 端口未就绪")
            return {"status": "unknown", "wsl_pid": wsl_pid}
            
        except Exception as e:
            print(f"  ❌ 启动失败: {e}")
            return {"status": "failed", "error": str(e)}
    
    def stop_all(self) -> Dict:
        """停止所有进程"""
        results = {"stopped": [], "failed": []}
        
        # 停止 browser-runtime (Windows)
        if self.pids.get("browser_runtime"):
            br = self.pids["browser_runtime"]
            win_pid = br.get("win_pid")
            if win_pid:
                print(f"[CrossEnv] 停止 browser-runtime (Windows PID: {win_pid})...")
                if kill_windows_process(win_pid):
                    results["stopped"].append("browser_runtime")
                else:
                    results["failed"].append("browser_runtime")
        
        # 停止 MCP Server (WSL)
        if self.pids.get("mcp_server"):
            mcp = self.pids["mcp_server"]
            wsl_pid = mcp.get("wsl_pid")
            if wsl_pid:
                print(f"[CrossEnv] 停止 MCP Server (WSL PID: {wsl_pid})...")
                try:
                    os.kill(wsl_pid, signal.SIGTERM)
                    results["stopped"].append("mcp_server")
                except Exception as e:
                    results["failed"].append(f"mcp_server: {e}")
        
        # 清理 PID 文件
        self.pids = {"browser_runtime": None, "mcp_server": None}
        self._save_pids()
        
        return results
    
    def status(self) -> Dict:
        """检查所有服务状态"""
        win_ip = CONFIG["windows_host_ip"]
        return {
            "browser_runtime": {
                "port": CONFIG["browser_runtime_port"],
                "host": win_ip,
                "listening": check_port(CONFIG["browser_runtime_port"], win_ip),
                "pid_info": self.pids.get("browser_runtime")
            },
            "mcp_server": {
                "port": CONFIG["mcp_server_port"],
                "listening": check_port(CONFIG["mcp_server_port"]),
                "pid_info": self.pids.get("mcp_server")
            }
        }
    
    def health_check(self) -> Dict:
        """执行健康检查"""
        print("[CrossEnv] 执行健康检查...")
        
        status = self.status()
        win_ip = CONFIG["windows_host_ip"]
        token = CONFIG["browser_runtime_token"]
        
        # 测试 browser-runtime API
        br_health = None
        if status["browser_runtime"]["listening"]:
            try:
                result = subprocess.run(
                    ["curl", "-s", "-H", f"Authorization: Bearer {token}", f"http://{win_ip}:{CONFIG['browser_runtime_port']}/"],
                    capture_output=True, text=True, timeout=5
                )
                br_health = json.loads(result.stdout) if result.returncode == 0 else f"Error: {result.stderr}"
            except Exception as e:
                br_health = f"Exception: {e}"
        
        # 测试 MCP Server
        mcp_health = None
        if status["mcp_server"]["listening"]:
            try:
                result = subprocess.run(
                    ["curl", "-s", f"http://127.0.0.1:{CONFIG['mcp_server_port']}/health"],
                    capture_output=True, text=True, timeout=5
                )
                mcp_health = result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
            except Exception as e:
                mcp_health = f"Exception: {e}"
        
        return {
            "browser_runtime": {
                **status["browser_runtime"],
                "health_response": br_health
            },
            "mcp_server": {
                **status["mcp_server"],
                "health_response": mcp_health
            },
            "overall": "healthy" if all([
                status["browser_runtime"]["listening"],
                status["mcp_server"]["listening"]
            ]) else "degraded"
        }
    
    def test_api(self) -> Dict:
        """测试 browser-runtime API"""
        print("[CrossEnv] 测试 browser-runtime API...")
        
        win_ip = CONFIG["windows_host_ip"]
        token = CONFIG["browser_runtime_token"]
        
        endpoints = {
            "GET /": f"http://{win_ip}:{CONFIG['browser_runtime_port']}/",
            "GET /profiles": f"http://{win_ip}:{CONFIG['browser_runtime_port']}/profiles",
            "POST /start": f"http://{win_ip}:{CONFIG['browser_runtime_port']}/start",
        }
        
        results = {}
        for name, url in endpoints.items():
            try:
                if "POST" in name:
                    result = subprocess.run(
                        ["curl", "-s", "-X", "POST", "-H", f"Authorization: Bearer {token}", url],
                        capture_output=True, text=True, timeout=10
                    )
                else:
                    result = subprocess.run(
                        ["curl", "-s", "-H", f"Authorization: Bearer {token}", url],
                        capture_output=True, text=True, timeout=10
                    )
                
                if result.returncode == 0:
                    try:
                        data = json.loads(result.stdout)
                        results[name] = {"status": "ok", "data": data}
                    except:
                        results[name] = {"status": "ok", "raw": result.stdout[:200]}
                else:
                    results[name] = {"status": "error", "error": result.stderr[:200]}
            except Exception as e:
                results[name] = {"status": "exception", "error": str(e)}
        
        return results


# ─────────────────────────────────────────────────────────────────────────────
# 命令行入口
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="跨环境启动器：从 WSL 启动 Windows 中的服务"
    )
    parser.add_argument(
        "command",
        choices=["start-br", "start-mcp", "start-all", "stop-all", "status", "health", "test-api"],
        help="要执行的命令"
    )
    
    args = parser.parse_args()
    
    launcher = CrossEnvLauncher()
    
    if args.command == "start-br":
        result = launcher.start_browser_runtime()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "start-mcp":
        result = launcher.start_mcp_server()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "start-all":
        print("=" * 60)
        print("跨环境启动: browser-runtime + hermes_mcp_server")
        print("=" * 60)
        
        br_result = launcher.start_browser_runtime()
        print()
        mcp_result = launcher.start_mcp_server()
        print()
        
        print("=" * 60)
        print("启动结果:")
        print(json.dumps({
            "browser_runtime": br_result,
            "mcp_server": mcp_result
        }, indent=2, ensure_ascii=False))
        print("=" * 60)
    
    elif args.command == "stop-all":
        result = launcher.stop_all()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "status":
        result = launcher.status()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "health":
        result = launcher.health_check()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "test-api":
        result = launcher.test_api()
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
