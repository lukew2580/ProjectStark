"""
Skills Marketplace — Skill discovery and management
"""
import os
import importlib.util
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class SkillMeta:
    name: str
    description: str
    args: Dict[str, str]
    triggers: List[str]


class SkillMarketplace:
    """
    Skill marketplace for discovering and loading skills.
    """
    
    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = skills_dir
        self.skills: Dict[str, Any] = {}
        self.skill_metadata: Dict[str, SkillMeta] = {}
        self._load_all_skills()
    
    def _load_all_skills(self):
        """Load all skills from skills directory."""
        if not os.path.exists(self.skills_dir):
            return
        
        for filename in os.listdir(self.skills_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                skill_name = filename[:-3]
                self._load_skill(skill_name)
    
    def _load_skill(self, skill_name: str):
        """Load a single skill."""
        filepath = os.path.join(self.skills_dir, f"{skill_name}.py")
        
        try:
            spec = importlib.util.spec_from_file_location(skill_name, filepath)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                if hasattr(module, "run") and hasattr(module, "meta"):
                    self.skills[skill_name] = module
                    self.skill_metadata[skill_name] = SkillMeta(
                        name=module.meta.get("name", skill_name),
                        description=module.meta.get("description", ""),
                        args=module.meta.get("args", {}),
                        triggers=module.meta.get("triggers", [])
                    )
        except Exception as e:
            print(f"Error loading skill {skill_name}: {e}")
    
    async def execute_skill(self, skill_name: str, context: Dict, args: Dict) -> Dict:
        """Execute a skill by name."""
        if skill_name not in self.skills:
            return {"error": f"Skill {skill_name} not found"}
        
        skill = self.skills[skill_name]
        return await skill.run(context, args)
    
    def find_skill_by_trigger(self, trigger: str) -> Optional[str]:
        """Find skill by trigger word."""
        for name, meta in self.skill_metadata.items():
            if trigger.lower() in [t.lower() for t in meta.triggers]:
                return name
        return None
    
    def list_skills(self) -> List[Dict]:
        """List all available skills."""
        return [
            {
                "name": meta.name,
                "description": meta.description,
                "args": meta.args,
                "triggers": meta.triggers
            }
            for meta in self.skill_metadata.values()
        ]
    
    def search_skills(self, query: str) -> List[Dict]:
        """Search skills by name or description."""
        query_lower = query.lower()
        results = []
        
        for name, meta in self.skill_metadata.items():
            if query_lower in meta.name.lower() or query_lower in meta.description.lower():
                results.append({
                    "name": meta.name,
                    "description": meta.description
                })
        
        return results


_global_marketplace: Optional[SkillMarketplace] = None


def get_skill_marketplace() -> SkillMarketplace:
    global _global_marketplace
    if _global_marketplace is None:
        _global_marketplace = SkillMarketplace()
    return _global_marketplace