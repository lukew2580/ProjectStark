"""
Hardwareless AI — Data Flow Node
"""
import numpy as np
import time
from config.settings import DIMENSIONS

class DataFlowNode:
    """
    A node in the Hardwareless AI data stream.
    Receives a flowing hypervector, applies a lightweight transformation
    (its piece of 'intelligence'), and pipes the result downstream.
    The AI processing happens IN TRANSIT — no central hardware.

    Sparse mode (LeanCTX-inspired): only processes dimensions where the
    transformation actually flips the sign (-1). Dimensions where the
    transform is +1 are identity ops and get SKIPPED entirely.
    """

    def __init__(self, node_id, dimensions=DIMENSIONS, transformation=None, sparse=False):
        self.node_id = node_id
        self.dimensions = dimensions
        self.downstream = None
        self.sparse = sparse
        self.domain = "Generic"

        if transformation is not None:
            self.transformation = transformation
        else:
            rng = np.random.default_rng()
            self.transformation = np.where(
                rng.integers(0, 2, size=dimensions, dtype=np.uint8),
                np.int8(1), np.int8(-1)
            )

        self._active_mask = (self.transformation == -1)
        self._active_count = int(self._active_mask.sum())

        self.ops_count = 0
        self.bytes_processed = 0
        self.dims_skipped = 0
        self.total_time_ns = 0

    @classmethod
    def create_expert(cls, node_id, domains, dimensions=DIMENSIONS, sparse=True):
        """Creates a node specialized in fuzzy semantic domains (seed-based)."""
        from core_engine.swarm.specialization import get_fuzzy_transformation
        transformation = get_fuzzy_transformation(dimensions, domains)
        node = cls(node_id, dimensions=dimensions, transformation=transformation, sparse=sparse)
        node.domain = ", ".join(domains)
        return node

    def connect(self, downstream_node):
        """Pipes this node's output to the next in the stream."""
        self.downstream = downstream_node
        return downstream_node

    async def stream_vector(self, incoming):
        """
        Process the data stream in transit using High-Dimensional Algebra.
        The node 'Binds' its expert identity into the flowing hypervector.
        """
        t0 = time.perf_counter_ns()
        from core_engine.brain import bind  # Uses backend-aware bind

        if self.sparse:
            # Sparse Binding: only XOR-bind where the transformation is active
            processed = incoming.copy()
            processed[self._active_mask] = -processed[self._active_mask]
            skipped = self.dimensions - self._active_count
        else:
            # Full Bipolar Binding
            processed = bind(incoming, self.transformation)
            skipped = 0

        elapsed = time.perf_counter_ns() - t0
        self.ops_count += 1
        self.bytes_processed += incoming.nbytes
        self.dims_skipped += skipped
        self.total_time_ns += elapsed

        if self.downstream:
            # Check if downstream is async (it should be now)
            import asyncio
            if asyncio.iscoroutinefunction(self.downstream.stream_vector):
                return await self.downstream.stream_vector(processed)
            else:
                return self.downstream.stream_vector(processed)
        return processed

    def get_metrics(self):
        """Returns performance metrics for this node."""
        avg_ns = self.total_time_ns / max(self.ops_count, 1)
        total_dims = self.dimensions * max(self.ops_count, 1)
        return {
            "node_id": self.node_id,
            "domain": self.domain,
            "ops": self.ops_count,
            "bytes_processed": self.bytes_processed,
            "active_dims": self._active_count,
            "skip_ratio": f"{self.dims_skipped / max(total_dims, 1):.1%}",
            "avg_latency_us": round(avg_ns / 1000, 2),
        }

class AsimovSentinelNode(DataFlowNode):
    """
    A high-dimensional safety gate.
    Monitors the stream for 'SkyNet' patterns and neutralizes unauthorized commands.
    """
    def __init__(self, node_id, dimensions=DIMENSIONS, restricted_vectors=None, threshold=0.7):
        super().__init__(node_id, dimensions=dimensions)
        self.restricted_vectors = restricted_vectors or []
        self.threshold = threshold
        self.domain = "ASIMOV_SENTINEL"
        self.incidents_prevented = 0

    async def stream_vector(self, incoming):
        """Monitors and filters the data stream for destructive patterns."""
        from core_engine.brain.operations import similarity
        
        is_safe = True
        for r_vec in self.restricted_vectors:
            score = similarity(incoming, r_vec, self.dimensions)
            if score > self.threshold:
                is_safe = False
                break
        
        if not is_safe:
            self.incidents_prevented += 1
            # Neutralize: replace with a Zero/Identity vector
            # This 'kills' the destructive command in transit
            processed = np.zeros(self.dimensions, dtype=np.int8)
        else:
            processed = incoming

        if self.downstream:
            return await self.downstream.stream_vector(processed)
        return processed

    def get_metrics(self):
        metrics = super().get_metrics()
        metrics["safety_incidents_prevented"] = self.incidents_prevented
        return metrics
