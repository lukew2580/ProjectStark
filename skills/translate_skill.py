"""
Translate Skill — Translates text between languages
"""
from typing import Dict, Any

async def run(context: Dict, args: Dict) -> Dict[str, Any]:
    from core_engine.translation.registry import get_registry
    from core_engine.translation.offline_fallback import get_offline_fallback
    
    text = args.get("text", "")
    source = args.get("source", "auto")
    target = args.get("target", "en")
    
    if not text:
        return {"error": "text required"}
    
    # Try online translation first
    try:
        registry = get_registry()
        result = await registry.translate(text, source, target)
        return {
            "text": result.text,
            "source": result.source_lang,
            "target": result.target_lang,
            "backend": result.backend,
            "confidence": result.confidence
        }
    except Exception:
        # Fallback to offline
        fallback = get_offline_fallback()
        result = await fallback.translate(text, source, target)
        return {
            "text": result.text,
            "source": result.source_lang,
            "target": result.target_lang,
            "backend": result.backend,
            "confidence": result.confidence
        }

meta = {
    "name": "translate",
    "description": "Translates text between languages",
    "args": {"text": "text to translate", "source": "source lang", "target": "target lang"},
    "triggers": ["translate", "convert", "spanish", "french", "chinese"]
}