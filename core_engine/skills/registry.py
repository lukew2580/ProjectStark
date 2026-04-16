"""
Hardwareless AI — Skill Registry
Manages loading and execution of skills
"""
import os
import importlib
import asyncio
from typing import Dict, Callable, List, Optional, Any
from dataclasses import dataclass


@dataclass
class SkillMeta:
    name: str
    description: str
    args: Dict[str, str]
    triggers: List[str]


class SkillRegistry:
    """
    Manages loading and execution of skills.
    
    Skills are in the `skills/` directory.
    Each skill is a Python file with:
    - run(context, args) -> dict
    - meta: dict with name, description, args, triggers
    """
    
    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = skills_dir
        self._handlers: Dict[str, Callable] = {}
        self._metadata: Dict[str, SkillMeta] = {}
        self._load_all()
    
    def _load_all(self):
        """Load all skills from skills directory."""
        if not os.path.exists(self.skills_dir):
            os.makedirs(self.skills_dir, exist_ok=True)
            self._create_default_skills()
            return
            
        for filename in os.listdir(self.skills_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                self._load_skill(filename[:-3])
    
    def _create_default_skills(self):
        """Create default built-in skills."""
        default_skills = {
            "translate": self._translate_skill,
            "remember": self._remember_skill,
            "recall": self._recall_skill,
            "status": self._status_skill,
            "encode": self._encode_skill,
        }
        
        for name, handler in default_skills.items():
            self._handlers[name] = handler
            self._metadata[name] = SkillMeta(
                name=name,
                description=f"Built-in {name} skill",
                args={},
                triggers=[name]
            )
    
    def _load_skill(self, name: str):
        """Load a single skill."""
        try:
            module = importlib.import_module(f"{self.skills_dir}.{name}")
            if hasattr(module, "run"):
                self._handlers[name] = module.run
                if hasattr(module, "meta"):
                    meta = module.meta
                    for trigger in meta.get("triggers", []):
                        self._handlers[trigger] = module.run
                    self._metadata[name] = SkillMeta(
                        name=meta.get("name", name),
                        description=meta.get("description", ""),
                        args=meta.get("args", {}),
                        triggers=meta.get("triggers", [])
                    )
        except Exception as e:
            print(f"Failed to load skill {name}: {e}")
    
    async def execute(
        self,
        trigger: str,
        context: dict,
        args: dict
    ) -> dict:
        """Execute a skill by trigger."""
        handler = self._handlers.get(trigger)
        if not handler:
            return {"error": f"Unknown skill: {trigger}"}
        
        try:
            if asyncio.iscoroutinefunction(handler):
                return await handler(context, args)
            return handler(context, args)
        except Exception as e:
            return {"error": str(e)}
    
    def find_skill(self, text: str) -> Optional[str]:
        """Find skill by trigger word in text."""
        text_lower = text.lower()
        for trigger, handler in self._handlers.items():
            if trigger.lower() in text_lower:
                return trigger
        return None
    
    def list_skills(self) -> List[dict]:
        """List all available skills."""
        return [
            {
                "name": name,
                "description": meta.description,
                "triggers": meta.triggers
            }
            for name, meta in self._metadata.items()
        ]
    
    def reload(self):
        """Reload all skills."""
        self._handlers.clear()
        self._metadata.clear()
        self._load_all()
    
    async def _translate_skill(self, context: dict, args: dict) -> dict:
        """Built-in translate skill."""
        from core_engine.translation import get_weave
        
        text = args.get("text", "")
        target = args.get("to", "en")
        
        weave = get_weave()
        result = await weave.think(text, target_lang=target)
        
        return {
            "original": text,
            "translated": result.target_text,
            "target_lang": target
        }
    
    async def _remember_skill(self, context: dict, args: dict) -> dict:
        """Built-in remember skill."""
        from core_engine.brain import get_mass
        
        key = args.get("key", "")
        value = args.get("value", "")
        
        mass = get_mass()
        mass.memorize(f"mem:{key}", mass=1.0)
        
        return {"remembered": key, "value": value}
    
    async def _recall_skill(self, context: dict, args: dict) -> dict:
        """Built-in recall skill."""
        from core_engine.brain import get_mass
        
        key = args.get("key", "")
        
        mass = get_mass()
        vector = mass.get_weighted_vector(f"mem:{key}")
        
        return {"recalled": key, "found": vector is not None}
    
    async def _status_skill(self, context: dict, args: dict) -> dict:
        """Built-in status skill."""
        from core_engine.translation import get_registry
        from core_engine.brain import get_mass
        
        registry = get_registry()
        mass = get_mass()
        
        return {
            "backends": registry.get_status(),
            "top_concepts": mass.top_concepts(5),
            "version": "0.3.0"
        }
    
    async def _encode_skill(self, context: dict, args: dict) -> dict:
        """Built-in encode skill."""
        from core_engine.translation import get_language_matrix
        
        text = args.get("text", "")
        lang = args.get("lang", "en")
        
        matrix = get_language_matrix()
        vector = matrix.encode_text(text, lang)
        
        return {
            "text": text,
            "lang": lang,
            "dimensions": vector.shape[0],
            "vector_hash": str(hash(vector.tobytes()[:16]))
        }


_global_registry: Optional[SkillRegistry] = None


def get_skills(skills_dir: str = "skills") -> SkillRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = SkillRegistry(skills_dir)
    return _global_registry