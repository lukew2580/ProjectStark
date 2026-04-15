"""
Hardwareless AI — Data Flow Pipeline
"""
from config.settings import DIMENSIONS
from core_engine.pipeline.node import DataFlowNode

class DataFlowPipeline:
    """
    Builder for chaining DataFlowNodes into a clean pipeline.
    Now correctly initializes Expert nodes with fuzzy semantic masks.
    """

    def __init__(self, node_count=None, dimensions=DIMENSIONS):
        self.dimensions = dimensions
        self.nodes = []
        
        # Default Expert Domain mapping for a 5-node swarm
        # Includes Linguistic Families (Romance, Germanic, Sinitic, etc.)
        expert_map = [
            ["LOGIC"],
            ["CODE"],
            ["ROMANCE", "GERMANIC"],         # West Linguistic expert
            ["SINITIC", "GLOBAL_SOUTH"],     # Global Linguistic expert
            ["CONTEXT", "GLOBAL_BRIDGE"]     # The Smoothness Bridge
        ]
        
        # If node_count is specific but doesn't match our map, we'll loop
        actual_count = node_count if node_count is not None else len(expert_map)
        
        for i in range(actual_count):
            domains = expert_map[i % len(expert_map)]
            node = DataFlowNode.create_expert(
                f"Expert-{i+1}", 
                domains=domains,
                dimensions=dimensions
            )
            self.nodes.append(node)

        # Chain them together
        for i in range(len(self.nodes) - 1):
            self.nodes[i].connect(self.nodes[i + 1])

        # === THE SENTINEL GATE ===
        # Final safety check before data delivery
        from core_engine.pipeline.node import AsimovSentinelNode
        self.sentinel = AsimovSentinelNode("SENTINEL-X")
        if self.nodes:
            self.nodes[-1].connect(self.sentinel)

    @property
    def head(self):
        """The entry point of the pipeline."""
        return self.nodes[0] if self.nodes else None

    async def process(self, input_vector):
        """Injects data into the stream and returns the final output."""
        if not self.nodes:
            return input_vector
        return await self.head.stream_vector(input_vector)

    def get_all_metrics(self):
        """Returns metrics from every node in the pipeline."""
        return [node.get_metrics() for node in self.nodes]

    def get_node_chain(self):
        """Returns a readable string of the pipeline path."""
        return " → ".join(f"{n.node_id}({n.domain})" for n in self.nodes)
