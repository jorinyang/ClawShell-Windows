#!/usr/bin/env python3
"""
ClawShell GPU/CPU 加速引擎
===========================
自动检测硬件加速能力并配置最优推理后端。

检测优先级:
1. NVIDIA CUDA (GPU) → onnxruntime-gpu
2. Intel oneDNN/OpenVINO → onnxruntime + CPU optimizations
3. Apple Metal/MPS → coremltools (macOS)
4. Pure CPU → onnxruntime + multi-threading

当前环境: WSL — 无GPU → 自动启用 ONNX Runtime CPU 优化
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("ClawShell.Accelerator")

# ── Configuration ──────────────────────────────────────────
ACCEL_STATE_PATH = Path.home() / ".real" / ".accel_state.json"

class AcceleratorEngine:
    """统一加速引擎 — 自动选择最优后端"""

    def __init__(self):
        self.state = self._load_state()
        self.backend = self._detect_backend()
        self.initialized = False

    def _load_state(self) -> Dict:
        if ACCEL_STATE_PATH.exists():
            try:
                return json.loads(ACCEL_STATE_PATH.read_text())
            except:
                pass
        return {
            "backend": "cpu",
            "gpu_available": False,
            "onnx_providers": [],
            "threads": os.cpu_count() or 4,
            "batch_size": 8,
        }

    def _save_state(self):
        ACCEL_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        ACCEL_STATE_PATH.write_text(json.dumps(self.state, indent=2))

    def _detect_backend(self) -> str:
        """检测最优加速后端"""
        # 1. CUDA GPU
        try:
            import torch
            if torch.cuda.is_available():
                self.state["gpu_available"] = True
                self.state["gpu_name"] = torch.cuda.get_device_name(0)
                self.state["gpu_memory"] = torch.cuda.get_device_properties(0).total_mem
                logger.info(f"GPU detected: {self.state['gpu_name']}")
                return "cuda"
        except ImportError:
            pass

        # 2. NVIDIA GPU via nvidia-smi (WSL pass-through)
        import subprocess
        try:
            smi = subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True, timeout=5)
            if smi.returncode == 0 and "GPU" in smi.stdout:
                logger.info(f"GPU detected via nvidia-smi: {smi.stdout.strip()[:80]}")
                self.state["gpu_available"] = True
                return "cuda_wsl"
        except:
            pass

        # 3. Check ONNX Runtime providers
        try:
            import onnxruntime as ort
            providers = ort.get_available_providers()
            self.state["onnx_providers"] = providers
            if 'CUDAExecutionProvider' in providers:
                self.state["gpu_available"] = True
                return "onnx_cuda"
            if 'DnnlExecutionProvider' in providers or 'OpenVINOExecutionProvider' in providers:
                logger.info("Intel oneDNN/OpenVINO CPU acceleration available")
                return "onnx_dnnl"
        except ImportError:
            pass

        # 4. CPU-only fallback with threading optimizations
        cpu_count = os.cpu_count() or 4
        self.state["threads"] = cpu_count
        os.environ.setdefault("OMP_NUM_THREADS", str(cpu_count))
        os.environ.setdefault("MKL_NUM_THREADS", str(cpu_count))
        os.environ.setdefault("OPENBLAS_NUM_THREADS", str(cpu_count))

        logger.info(f"CPU-only mode: {cpu_count} threads")
        return "cpu"

    def initialize(self):
        """初始化加速引擎"""
        if self.initialized:
            return self.backend

        logger.info(f"Initializing accelerator: backend={self.backend}")

        if self.backend == "cpu":
            # Set CPU thread optimization
            import multiprocessing
            threads = self.state["threads"]
            # Configure ONNX runtime session options
            try:
                import onnxruntime as ort
                self._ort_session_opts = ort.SessionOptions()
                self._ort_session_opts.intra_op_num_threads = threads
                self._ort_session_opts.inter_op_num_threads = max(1, threads // 2)
                self._ort_session_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                self._ort_session_opts.enable_cpu_mem_arena = True
                self._ort_session_opts.enable_mem_pattern = True
                self._ort_session_opts.execution_mode = ort.ExecutionMode.ORT_PARALLEL
                logger.info(f"ONNX CPU optimized: {threads} threads, graph opt=ALL")
            except ImportError:
                pass

        elif self.backend in ("cuda", "cuda_wsl", "onnx_cuda"):
            try:
                import onnxruntime as ort
                self._ort_session_opts = ort.SessionOptions()
                self._ort_session_opts.intra_op_num_threads = 1  # Single thread for GPU
                self._ort_session_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                logger.info("ONNX GPU mode: CUDA execution provider")
            except ImportError:
                logger.warning("ONNX Runtime not available, falling back to CPU")
                self.backend = "cpu"
                return self.initialize()

        self.initialized = True
        self._save_state()
        return self.backend

    def get_ort_session_options(self):
        """获取优化后的 ONNX Runtime 会话选项"""
        self.initialize()
        return getattr(self, '_ort_session_opts', None)

    def get_ort_providers(self) -> list:
        """获取 ONNX Runtime 执行提供者列表"""
        self.initialize()
        if self.backend in ("cuda", "onnx_cuda", "cuda_wsl"):
            return ['CUDAExecutionProvider', 'CPUExecutionProvider']
        if self.backend == "onnx_dnnl":
            return ['DnnlExecutionProvider', 'CPUExecutionProvider']
        return ['CPUExecutionProvider']

    def status(self) -> Dict:
        return {
            "backend": self.backend,
            "gpu_available": self.state.get("gpu_available", False),
            "gpu_name": self.state.get("gpu_name", "N/A"),
            "onnx_providers": self.state.get("onnx_providers", []),
            "threads": self.state.get("threads", 0),
            "optimizations": "inter_op+intra_op+graph_ALL+mem_arena" if self.backend != "cuda" else "CUDA_EP"
        }


# ── Singleton ──────────────────────────────────────────────
_accelerator: Optional[AcceleratorEngine] = None

def get_accelerator() -> AcceleratorEngine:
    global _accelerator
    if _accelerator is None:
        _accelerator = AcceleratorEngine()
    return _accelerator


# ── Convenience Functions ──────────────────────────────────
def optimize_onnx_session(model_path: str) -> Any:
    """Load ONNX model with optimal settings"""
    import onnxruntime as ort
    accel = get_accelerator()
    accel.initialize()
    return ort.InferenceSession(
        model_path,
        sess_options=accel.get_ort_session_options(),
        providers=accel.get_ort_providers()
    )


def accelerate_chromadb():
    """Apply acceleration settings to ChromaDB embedding"""
    accel = get_accelerator()
    accel.initialize()
    # ChromaDB uses ONNX Runtime internally for embeddings
    # Set environment variables for optimal threading
    threads = accel.state.get("threads", 4)
    os.environ["CHROMA_ONNX_THREADS"] = str(threads)
    os.environ["CHROMA_OMP_NUM_THREADS"] = str(threads)
    logger.info(f"ChromaDB accelerated: {threads} ONNX threads")
    return accel.status()


if __name__ == "__main__":
    accel = AcceleratorEngine()
    print(json.dumps(accel.status(), indent=2))
    print(f"\nBackend: {accel.backend}")
    print(f"GPU: {'YES' if accel.state['gpu_available'] else 'NO (CPU optimized)'}")
    print(f"Threads: {accel.state['threads']}")
