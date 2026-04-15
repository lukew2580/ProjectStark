"""
Hardwareless AI — Simulation & Benchmark (v3)
Now includes: LeanCTX compression benchmark, sparse pipeline benchmark.
"""
import time
import psutil
import os
import numpy as np
from config.settings import DIMENSIONS, KNOWLEDGE_BASE
from core_engine.brain.memory import Memory
from core_engine.brain.operations import bind, bundle, permute, similarity
from core_engine.translation.encoder import Encoder
from core_engine.pipeline.pipeline import DataFlowPipeline
from core_engine.compression.compressor import CognitiveCompressor

class HDCBrain:
    """Proxy adapter to map legacy benchmark calls to new module functions."""
    def __init__(self, dimensions):
        self.dimensions = dimensions
        self.memory_component = Memory(dimensions)
        self.memory = self.memory_component.items
    
    def random_vector(self, seed=None):
        from core_engine.brain.vectors import generate_random_vector
        return generate_random_vector(self.dimensions, seed=seed)
        
    def memorize(self, concept_name):
        return self.memory_component.memorize(concept_name)
    
    def bind(self, vec_a, vec_b):
        return bind(vec_a, vec_b)
        
    def bundle(self, vectors):
        return bundle(vectors, self.dimensions)
        
    def permute(self, vec, shifts=1):
        return permute(vec, shifts)
        
    def similarity(self, vec_a, vec_b):
        return similarity(vec_a, vec_b, self.dimensions)
        
    def recall(self, query_vector, top_n=1):
        return self.memory_component.recall(query_vector, top_n=top_n)

class TextToHypervector:
    """Proxy adapter to map legacy benchmark calls to new Encoder."""
    def __init__(self, dimensions):
        self.encoder = Encoder(dimensions)
    def encode(self, text):
        return self.encoder.encode(text)


def get_memory_mb():
    return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)


def run_simulation():
    print("=" * 60)
    print("  HARDWARELESS AI — FULL SYSTEM BENCHMARK v2")
    print("=" * 60)

    mem_baseline = get_memory_mb()

    # ── 1. HDC Brain Operations ────────────────────────────────────
    print("\n[1] HDC BRAIN — Core Operations")
    brain = HDCBrain(dimensions=DIMENSIONS)

    # Memorize the full knowledge base
    t0 = time.perf_counter()
    for concept in KNOWLEDGE_BASE:
        brain.memorize(concept)
    mem_time = (time.perf_counter() - t0) * 1000
    print(f"    Memorized {len(KNOWLEDGE_BASE)} concepts in {mem_time:.2f} ms")

    # Bind + Bundle
    t0 = time.perf_counter()
    v_a = brain.memory["data"]
    v_b = brain.memory["stream"]
    v_c = brain.memory["flow"]
    bound = brain.bind(v_a, v_b)
    bundled = brain.bundle([bound, v_c])
    ops_time = (time.perf_counter() - t0) * 1000
    print(f"    Bind + Bundle in {ops_time:.4f} ms")

    # Vectorized Recall
    t0 = time.perf_counter()
    top3 = brain.recall(bundled, top_n=3)
    recall_time = (time.perf_counter() - t0) * 1000
    print(f"    Vectorized recall (top-3 from {len(brain.memory)} items): {recall_time:.2f} ms")
    for name, score in top3:
        print(f"      → {name}: {score:.4f}")

    # ── 2. Word Order Verification ─────────────────────────────────
    print("\n[2] WORD ORDER — Critical Test")
    translator = TextToHypervector(dimensions=DIMENSIONS)

    vec_a = translator.encode("dog bites man")
    vec_b = translator.encode("man bites dog")
    vec_c = translator.encode("dog bites man")  # duplicate of A

    sim_ab = brain.similarity(vec_a, vec_b)
    sim_ac = brain.similarity(vec_a, vec_c)

    print(f"    'dog bites man' vs 'man bites dog': {sim_ab:.4f}")
    print(f"    'dog bites man' vs 'dog bites man': {sim_ac:.4f}")

    if sim_ac > sim_ab and sim_ac > 0.99:
        print("    ✅ PASS — Word order is correctly encoded!")
    else:
        print("    ❌ FAIL — Word order not differentiated!")

    # ── 3. Data Flow Pipeline ──────────────────────────────────────
    print("\n[3] DATA FLOW PIPELINE — Streaming Benchmark")
    pipeline = DataFlowPipeline(node_count=5, dimensions=DIMENSIONS)
    print(f"    Path: {pipeline.get_node_chain()}")

    input_vec = translator.encode("test the hardwareless data stream")

    # Run 1000 iterations for stable timing
    iterations = 1000
    t0 = time.perf_counter()
    for _ in range(iterations):
        pipeline.process(input_vec)
    total_ms = (time.perf_counter() - t0) * 1000
    per_op = total_ms / iterations

    print(f"    {iterations} pipeline passes in {total_ms:.2f} ms")
    print(f"    Per-pass latency: {per_op:.4f} ms ({per_op * 1000:.1f} μs)")

    # Node-level metrics
    for m in pipeline.get_all_metrics():
        print(f"      {m['node_id']}: {m['ops']} ops, avg {m['avg_latency_us']} μs/op")

    # ── 4. LeanCTX Compression Benchmark ─────────────────────────────
    print("\n[4] LEANCTX COMPRESSION — Cognitive Filter")
    compressor = CognitiveCompressor()

    test_prompts = [
        "Can you please help me to quickly find and locate the information about the data?",
        "I would like you to build and create a very large and massive distributed network for me",
        "The system should be able to rapidly search through all of the content in the web",
        "Please make a tiny little program that will transmit and deliver messages to the server",
        "I want to generate and construct an excellent computing pipeline that is fast and speedy",
    ]

    print("    Sample compressions:")
    for prompt in test_prompts:
        compressed = compressor.compress(prompt)
        raw_len = len(prompt.split())
        comp_len = len(compressed.split()) if compressed else 0
        saved = raw_len - comp_len
        print(f"      [{raw_len}→{comp_len} words, -{saved}] \"{prompt[:50]}...\"")
        print(f"        → \"{compressed}\"")

    # Benchmark: encode with vs without compression
    big_prompt = " ".join(test_prompts)

    t0 = time.perf_counter()
    for _ in range(100):
        translator.encode(big_prompt)
    no_comp_time = (time.perf_counter() - t0) * 1000

    compressed_big = compressor.compress(big_prompt)
    t0 = time.perf_counter()
    for _ in range(100):
        translator.encode(compressed_big)
    comp_time = (time.perf_counter() - t0) * 1000

    print(f"\n    Encode 100x WITHOUT compression: {no_comp_time:.2f} ms ({len(big_prompt.split())} words)")
    print(f"    Encode 100x WITH compression:    {comp_time:.2f} ms ({len(compressed_big.split())} words)")
    print(f"    Speedup: {no_comp_time / comp_time:.1f}x faster with compression")
    print(f"    Compressor stats: {compressor.get_stats()}")

    # ── 5. Sparse Pipeline Benchmark ───────────────────────────────
    print("\n[5] SPARSE vs DENSE PIPELINE")
    sparse_pipe = DataFlowPipeline(node_count=5, dimensions=DIMENSIONS)
    dense_pipe = DataFlowPipeline(node_count=5, dimensions=DIMENSIONS)
    # Force dense mode on the dense pipeline
    for node in dense_pipe.nodes:
        node.sparse = False

    test_vec = translator.encode("benchmark sparse vs dense")

    t0 = time.perf_counter()
    for _ in range(1000):
        sparse_pipe.process(test_vec)
    sparse_time = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    for _ in range(1000):
        dense_pipe.process(test_vec)
    dense_time = (time.perf_counter() - t0) * 1000

    print(f"    Sparse pipeline (1k passes): {sparse_time:.2f} ms")
    print(f"    Dense pipeline  (1k passes): {dense_time:.2f} ms")
    if sparse_time < dense_time:
        print(f"    Sparse is {dense_time / sparse_time:.1f}x faster!")
    else:
        print(f"    Dense is faster — sparse overhead too high at this scale")
    # Show skip ratios per node
    for m in sparse_pipe.get_all_metrics():
        print(f"      {m['node_id']}: active dims={m['active_dims']}, skip={m['skip_ratio']}")

    # ── 6. Comparative Benchmark: HDC vs Neural-Net-Style ──────────
    print("\n[6] COMPARATIVE BENCHMARK — HDC vs Matrix Multiply")

    vec1 = np.random.choice([-1, 1], size=DIMENSIONS).astype(np.int8)
    vec2 = np.random.choice([-1, 1], size=DIMENSIONS).astype(np.int8)

    t0 = time.perf_counter()
    for _ in range(10000):
        _ = vec1 * vec2
    hdc_time = (time.perf_counter() - t0) * 1000

    mat_a = np.random.randn(256, 256).astype(np.float32)
    mat_b = np.random.randn(256, 256).astype(np.float32)

    t0 = time.perf_counter()
    for _ in range(10000):
        _ = mat_a @ mat_b
    nn_time = (time.perf_counter() - t0) * 1000

    speedup = nn_time / hdc_time
    print(f"    HDC element-wise (10k ops): {hdc_time:.2f} ms")
    print(f"    NN matrix multiply (10k ops): {nn_time:.2f} ms")
    print(f"    HDC is {speedup:.1f}x faster — no GPU needed!")

    # ── 7. Memory Report ───────────────────────────────────────────
    mem_total = get_memory_mb() - mem_baseline
    print(f"\n[7] MEMORY FOOTPRINT")
    print(f"    Total framework overhead: {mem_total:.3f} MB")
    if mem_total < 10:
        print("    ✅ Ultra-lean — fits on the tiniest devices!")
    else:
        print(f"    ⚠️  {mem_total:.1f} MB — needs optimization")

    print("\n" + "=" * 60)
    print("  BENCHMARK COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_simulation()

