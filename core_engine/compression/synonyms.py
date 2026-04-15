"""
Hardwareless AI — Synonym Normalization
Collapse synonyms into a single canonical form so
"make", "build", "create", "construct" all map to ONE vector.
"""
SYNONYM_MAP = {
    # Action clusters
    "make": "create", "build": "create", "construct": "create", "generate": "create",
    "remove": "delete", "destroy": "delete", "erase": "delete", "purge": "delete",
    "modify": "update", "change": "update", "alter": "update", "edit": "update",
    "find": "search", "look": "search", "seek": "search", "locate": "search",
    "transmit": "send", "deliver": "send", "push": "send", "emit": "send",
    "get": "receive", "fetch": "receive", "pull": "receive", "obtain": "receive",
    "begin": "start", "launch": "start", "initiate": "start", "boot": "start",
    "halt": "stop", "end": "stop", "terminate": "stop", "kill": "stop",
    "execute": "run", "perform": "run", "invoke": "run",
    "examine": "analyze", "inspect": "analyze", "evaluate": "analyze", "check": "analyze",
    # Descriptor clusters
    "quick": "fast", "rapid": "fast", "speedy": "fast", "swift": "fast",
    "large": "big", "huge": "big", "massive": "big", "enormous": "big",
    "tiny": "small", "little": "small", "mini": "small", "compact": "small",
    "great": "good", "excellent": "good", "fine": "good", "nice": "good",
    "terrible": "bad", "awful": "bad", "poor": "bad", "broken": "bad",
    # Noun clusters
    "information": "data", "info": "data", "content": "data", "payload": "data",
    "server": "node", "host": "node", "machine": "node", "device": "node",
    "net": "network", "web": "network", "grid": "network", "mesh": "network",
    "msg": "message", "notification": "message", "alert": "message",
    "req": "request", "ask": "request", "prompt": "request",
    "res": "response", "reply": "response", "answer": "response",
}
