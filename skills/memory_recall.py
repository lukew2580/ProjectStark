"""
Memory Recall Skill — Retrieves information from memory
"""
from typing import Dict, Any

async def run(context: Dict, args: Dict) -> Dict[str, Any]:
    from core_engine.brain.memory import Memory
    from config.settings import DIMENSIONS
    
    query = args.get("query", "")
    top_n = args.get("top_n", 3)
    
    if not query:
        return {"error": "query required"}
    
    # Encode query as vector
    from core_engine.brain.vectors import generate_random_vector
    import hashlib
    seed = int.from_bytes(hashlib.sha256(query.encode()).digest()[:4], 'big') % (2**31)
    query_vector = generate_random_vector(DIMENSIONS, seed=seed)
    
    # Search memory
    memory = Memory(DIMENSIONS)
    results = memory.recall(query_vector, top_n=top_n)
    
    return {
        "query": query,
        "results": [{"concept": r[0], "score": r[1]} for r in results]
    }

meta = {
    "name": "memory_recall",
    "description": "Retrieves information from memory",
    "args": {"query": "search term", "top_n": "number of results"},
    "triggers": ["remember", "recall", "memory", "what is", "who was"]
}