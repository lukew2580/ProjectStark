#!/usr/bin/env python3
"""
Quick setup script for HDC backend options.
Installs optional dependencies based on chosen backend.
"""
import subprocess
import sys

def check_package(pkg: str) -> bool:
    try:
        __import__(pkg)
        return True
    except ImportError:
        return False

def main():
    print("Hardwareless AI — HDC Backend Setup")
    print("=" * 50)
    
    # Check torchhd
    print("\n[1/3] Checking torchhd (GPU-accelerated HDC)...")
    if check_package("torchhd"):
        import torchhd
        print(f"  ✓ torchhd {torchhd.__version__ if hasattr(torchhd, '__version__') else 'installed'}")
        
        # Check PyTorch + CUDA
        import torch
        print(f"  ✓ torch {torch.__version__}")
        if torch.cuda.is_available():
            print(f"  ✓ CUDA available: {torch.cuda.get_device_name(0)}")
        else:
            print("  ℹ CUDA not available (CPU mode)")
    else:
        print("  ✗ torchhd not installed")
        install = input("  Install torchhd? [y/N]: ").strip().lower()
        if install == 'y':
            print("  Installing torchhd...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "torchhd", "torch"])
            print("  ✓ Installation complete. Restart to use torchhd backend.")
        else:
            print("  Skipping. Use legacy backend.")
    
    # Check vLLM (optional LLM backend)
    print("\n[2/3] Checking vLLM (LLM inference engine)...")
    if check_package("vllm"):
        import vllm
        print(f"  ✓ vLLM installed")
    else:
        print("  ℹ vLLM not installed (optional). Install for production LLM serving:")
        print("    pip install vllm")
    
    # Check Haystack (optional orchestration)
    print("\n[3/3] Checking Haystack (AI orchestration)...")
    if check_package("haystack"):
        import haystack
        print(f"  ✓ Haystack installed")
    else:
        print("  ℹ Haystack not installed (optional). Install for RAG pipelines:")
        print("    pip install haystack-ai")
    
    print("\n" + "=" * 50)
    print("Backend Configuration")
    print("=" * 50)
    print("\nTo use torchhd backend, set environment variables:")
    print("  export HDC_BACKEND=torchhd")
    print("  export HDC_DEVICE=cuda  # or 'cpu'")
    print("  export HDC_TORCHHD_MODEL=MAP  # MAP, BSC, HRR, FHRR")
    print("\nOr run directly:")
    print("  HDC_BACKEND=torchhd python gateway/app.py")
    print("\nFor development, add to ~/.bashrc or ~/.zshrc:")
    print("  echo 'export HDC_BACKEND=torchhd' >> ~/.bashrc")
    print("  echo 'export HDC_DEVICE=cuda' >> ~/.bashrc")

if __name__ == "__main__":
    main()
