# 🧠 SOUL.md — Skills, Operations, Understanding, Learning

> The operational manifest for Hardwareless AI. This file defines how skills work.

---

## What is a SOUL Skill?

A **SOUL skill** is a self-contained capability module that extends Hardwareless AI's abilities. Skills are:

- **S**elf-contained — each skill is independent
- **O**perational — skills DO things (translate, compute, remember)
- **U**nderstood — skills have clear inputs/outputs
- **L**earnable — skills can be composed and chained

---

## Anatomy of a Skill

Every skill is a Python file in the `skills/` directory:

```python
# skills/hello.py
"""
Hello Skill — Greets the user in any language
"""
from core_engine.translation import get_weave

async def run(context, args):
    """Execute the skill."""
    target_lang = args.get("lang", "en")
    greeting = {
        "en": "Hello", "es": "Hola", "fr": "Bonjour",
        "de": "Hallo", "zh": "你好", "ja": "こんにちは"
    }
    return {
        "text": greeting.get(target_lang, "Hello"),
        "lang": target_lang
    }

# Metadata
meta = {
    "name": "hello",
    "description": "Greets in specified language",
    "args": {"lang": "target language code"},
    "triggers": ["hello", "hi", "greet"]
}
```

---

## Built-in Skills

| Skill | Description | Trigger |
|-------|-------------|---------|
| `translate` | Translate text between languages | `translate [text] to [lang]` |
| `remember` | Store a fact in memory | `remember [key] = [value]` |
| `recall` | Retrieve a stored fact | `recall [key]` |
| `encode` | Convert text to hypervector | `encode [text]` |
| `compute` | Run hypervector operations | `bundle [vec1] + [vec2]` |
| `status` | Show system status | `status`, `health` |

---

## Skill Registry

The skill registry maps trigger phrases to skill handlers:

```python
# core_engine/skills/registry.py
from typing import Dict, Callable, List
import asyncio
import importlib
import os

class SkillRegistry:
    """Manages loading and execution of skills."""
    
    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = skills_dir
        self._handlers: Dict[str, Callable] = {}
        self._metadata: Dict[str, dict] = {}
        self.load_all()
    
    def load_all(self):
        """Load all skills from skills directory."""
        if not os.path.exists(self.skills_dir):
            return
            
        for filename in os.listdir(self.skills_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                self.load_skill(filename[:-3])
    
    def load_skill(self, name: str):
        """Load a single skill."""
        try:
            module = importlib.import_module(f"{self.skills_dir}.{name}")
            if hasattr(module, "run"):
                self._handlers[name] = module.run
                if hasattr(module, "meta"):
                    meta = module.meta
                    for trigger in meta.get("triggers", []):
                        self._handlers[trigger] = module.run
                    self._metadata[name] = meta
        except Exception as e:
            print(f"Failed to load skill {name}: {e}")
    
    async def execute(self, trigger: str, context: dict, args: dict) -> dict:
        """Execute a skill by trigger."""
        handler = self._handlers.get(trigger)
        if not handler:
            return {"error": f"Unknown skill: {trigger}"}
        
        if asyncio.iscoroutinefunction(handler):
            return await handler(context, args)
        return handler(context, args)
    
    def list_skills(self) -> List[dict]:
        """List all available skills."""
        return [
            {"name": name, **meta}
            for name, meta in self._metadata.items()
        ]


_global_registry = None

def get_skills() -> SkillRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = SkillRegistry()
    return _global_registry
```

---

## Skill Execution Flow

```
User Input → Trigger Detection → Skill Lookup → Execute → Return Result
                  ↓
            [translate hello to ja]
                  ↓
            Handler: skills/translate.py
                  ↓
            Result: {"text": "こんにちは", "lang": "ja"}
```

---

## Creating a Custom Skill

1. Create `skills/myskill.py`
2. Define `async def run(context, args)` function
3. Add `meta` dict with triggers
4. Run `hardwareless reload-skills`

Example custom skill:

```python
# skills/math.py
"""Math skill — Simple arithmetic"""
from typing import Dict, Any

async def run(context: Dict, args: Dict) -> Dict[str, Any]:
    operation = args.get("op", "add")
    a = float(args.get("a", 0))
    b = float(args.get("b", 0))
    
    ops = {"add": a + b, "sub": a - b, "mul": a * b, "div": a / b if b else 0}
    
    return {"result": ops.get(operation, 0), "operation": operation}

meta = {
    "name": "math",
    "description": "Perform basic arithmetic",
    "args": {"op": "operation", "a": "first number", "b": "second number"},
    "triggers": ["calc", "math", "+", "-", "*", "/"]
}
```

---

## Persistence (CPU-less Memory)

Skills can use the HDC memory system:

```python
from core_engine.brain import get_mass, get_density

async def remember_skill(context, args):
    key = args["key"]
    value = args["value"]
    
    mass = get_mass()
    mass.memorize(f"skill:{key}", mass=1.0)
    
    return {"remembered": key, "value": value}

async def recall_skill(context, args):
    key = args["key"]
    
    mass = get_mass()
    vector = mass.get_weighted_vector(f"skill:{key}")
    
    return {"recalled": key, "vector": vector is not None}
```

---

## New Security Skills (v2)

### virus_guard_skill
Detects viruses using HDC hypervector similarity.

```python
# skills/virus_guard_skill.py
from core_engine.virus_guard import get_virus_detector

async def run(context, args):
    file_path = args["file_path"]
    detector = get_virus_detector()
    report = await detector.scan_file(file_path)
    return {"status": report.status.value, "virus": report.virus_name}
```

### scam_detector_skill
Detects phone, email, and website scams.

```python
# skills/scam_detector_skill.py
from core_engine.scam_fighter import get_scam_detector

async def run(context, args):
    detector = get_scam_detector()
    report = await detector.analyze_phone_number(args["phone"])
    return report
```

### attribution_skill
Identifies malicious download sources.

```python
# skills/attribution_skill.py
from core_engine.virus_guard import get_scammer_attribution

async def run(context, args):
    attribution = get_scammer_attribution()
    report = await attribution.check_software_attribution(
        args["software_hash"],
        args.get("download_source", "")
    )
    return {"risk_level": report.risk_level, "recommendations": report.recommendations}
```

### antivirus_scan_skill
Multi-engine antivirus scanning.

```python
# skills/antivirus_scan_skill.py
from core_engine.antivirus_integration import get_antivirus_integration

async def run(context, args):
    av = get_antivirus_integration()
    results = await av.scan_multi_engine(args["file_path"])
    return {"infected": any(r.is_infected for r in results), "engines": len(results)}
```

---

## Testing Skills

```bash
# List skills
hardwareless skills list

# Test a skill
hardwareless skills run translate --text "hello" --to es

# Reload skills
hardwareless skills reload
```

---

## Community Skills

Share skills on GitHub. Structure:
```
skills/
├── README.md          # Skill catalog
├── community/
│   ├── advanced_translate.py
│   ├── voice_synth.py
│   └── ...
```

---

*This document defines the SOUL of Hardwareless AI.*