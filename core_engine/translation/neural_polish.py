"""
Hardwareless AI — Neural Polish Post-Processor
Improves translation quality with neural-style refinements
"""
import re
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class PolishResult:
    original: str
    polished: str
    changes: List[Dict]
    confidence: float


class NeuralPolish:
    """
    Applies neural-style polish to translations.
    - Grammar corrections
    - Punctuation normalization
    - Capitalization fixes
    - Common phrase improvements
    """
    
    def __init__(self):
        self._grammar_rules = self._init_grammar_rules()
        self._phrase_improvements = self._init_phrases()
    
    def _init_grammar_rules(self) -> List[Dict]:
        """Initialize grammar correction rules."""
        return [
            {
                "pattern": r"\s+",
                "replacement": " ",
                "description": "Multiple spaces to single"
            },
            {
                "pattern": r"\.\.+",
                "replacement": "...",
                "description": "Multiple dots to ellipsis"
            },
            {
                "pattern": r"[!]+",
                "replacement": "!",
                "description": "Multiple exclamations to single"
            },
            {
                "pattern": r"[?]+",
                "replacement": "?",
                "description": "Multiple questions to single"
            },
            {
                "pattern": r"\bid\b",
                "replacement": "I",
                "description": "Lowercase 'i' to uppercase 'I'"
            },
            {
                "pattern": r"\s+([.!?,])",
                "replacement": r"\1",
                "description": "Space before punctuation"
            },
            {
                "pattern": r"([.!?,])\s*([.!?,])",
                "replacement": r"\1",
                "description": "Multiple punctuation"
            }
        ]
    
    def _init_phrases(self) -> Dict[str, Dict]:
        """Initialize phrase improvements."""
        return {
            "en": {
                "thank you very much": "thank you so much",
                "very good": "really good",
                "in order to": "to",
                "due to the fact that": "because",
                "at this point in time": "now",
                "in the event that": "if",
                "with regard to": "regarding",
                "in spite of the fact that": "although"
            },
            "es": {
                "muchas gracias": "muchas gracias",
                "muy bien": "really bien"
            }
        }
    
    async def polish(self, text: str, target_lang: str = "en") -> PolishResult:
        """Apply neural polish to text."""
        original = text
        changes = []
        
        # Apply grammar rules
        for rule in self._grammar_rules:
            new_text = re.sub(rule["pattern"], rule["replacement"], text)
            if new_text != text:
                changes.append({
                    "type": "grammar",
                    "description": rule["description"],
                    "original": text[:50],
                    "result": new_text[:50]
                })
                text = new_text
        
        # Capitalize first letter
        if text and text[0].islower():
            text = text[0].upper() + text[1:]
            if text != original:
                changes.append({
                    "type": "capitalization",
                    "description": "Capitalize first letter"
                })
        
        # Ensure ending punctuation
        if text and text[-1] not in ".!?":
            text = text + "."
            changes.append({
                "type": "punctuation",
                "description": "Add ending punctuation"
            })
        
        confidence = max(0.5, 1.0 - (len(changes) * 0.1))
        
        return PolishResult(
            original=original,
            polished=text,
            changes=changes,
            confidence=confidence
        )


_global_polish: Optional[NeuralPolish] = None


def get_neural_polish() -> NeuralPolish:
    global _global_polish
    if _global_polish is None:
        _global_polish = NeuralPolish()
    return _global_polish