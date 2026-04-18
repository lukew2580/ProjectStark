#!/usr/bin/env python3
"""
HDC Backend Benchmark — Compare legacy numpy vs torchhd

Usage:
    python benchmark_hdc_backends.py
    HDC_BACKEND=torchhd HDC_DEVICE=cuda python benchmark_hdc_backends.py
"""
import time
import numpy as np
from typing import Callable
import os
import sys

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def benchmark_func(fn: Callable, repeats: int = 100) -> tuple[float, float]:
    """Benchmark a function, returns (mean_ms, std_ms)."""
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        elapsed = (time.perf_counter() - start) * 1000  # ms
        times.append(elapsed)
    mean = np.mean(times)
    std = np.std(times)
    return mean, std


def main():
    DIM = 10000
    N_VECTORS = 100
    
    print("=" * 60)
    print("Hardwareless AI — HDC Backend Benchmark")
    print("=" * 60)
    print(f"Dimensions: {DIM}")
    print(f"Vectors in bundle: {N_VECTORS}")
    print()
    
    # Import backend system
    from core_engine.brain import (
        generate_random_vector,
        bind,
        bundle,
        permute,
        similarity,
        get_backend,
        switch_backend,
    )
    
    backend = get_backend()
    print(f"Active backend: {backend.name}")
    print(f"Description: {backend.description}")
    print(f"Capabilities: {backend.capabilities}")
    print()
    
    # Prepare test vectors
    print("Preparing test vectors...")
    v1 = generate_random_vector(DIM, seed=42)
    v2 = generate_random_vector(DIM, seed=43)
    vectors = [generate_random_vector(DIM, seed=i) for i in range(N_VECTORS)]
    print("Ready.")
    print()
    
    # Benchmark each operation
    ops = {
        "generate_random_vector": lambda: generate_random_vector(DIM, seed=1),
        "bind (pair)": lambda: bind(v1, v2),
        "bundle (100 vecs)": lambda: bundle(vectors, DIM),
        "permute (shift=5)": lambda: permute(v1, shifts=5),
        "similarity": lambda: similarity(v1, v2, DIM),
    }
    
    print(f"{'Operation':<25} {'Mean (ms)':>12} {'± Std':>10} {'Throughput':>12}")
    print("-" * 65)
    
    results = {}
    for name, fn in ops.items():
        mean, std = benchmark_func(fn, repeats=100)
        results[name] = (mean, std)
        
        # Calculate throughput
        if "generate" in name:
            throughput = f"{1000/mean:.0f} vec/s"
        elif "bundle" in name:
            throughput = f"{1000/mean:.1f} ops/s"
        else:
            throughput = f"{1000/mean:.0f} ops/s"
        
        print(f"{name:<25} {mean:>10.4f} ± {std:>8.4f}  {throughput:>12}")
    
    print()
    print("Benchmark complete.")
    
    # Try switching backends if torchhd available
    try:
        import torchhd
        print()
        print("torchhd detected. Try both backends:")
        print("  HDC_BACKEND=legacy python benchmark_hdc_backends.py")
        print("  HDC_BACKEND=torchhd HDC_DEVICE=cuda python benchmark_hdc_backends.py")
    except ImportError:
        print()
        print("torchhd not available. Install to compare:")
        print("  pip install torchhd torch")


if __name__ == "__main__":
    main()
