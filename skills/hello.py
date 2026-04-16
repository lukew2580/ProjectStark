"""
Hello Skill — Simple greeting
"""
from typing import Dict, Any

async def run(context: Dict, args: Dict) -> Dict[str, Any]:
    lang = args.get("lang", "en")
    greetings = {
        "en": "Hello",
        "es": "Hola", 
        "fr": "Bonjour",
        "de": "Hallo",
        "zh": "你好",
        "ja": "こんにちは",
        "ko": "안녕하세요",
        "ru": "Привет",
        "ar": "مرحبا",
        "hi": "नमस्ते"
    }
    return {"text": greetings.get(lang, "Hello"), "lang": lang}

meta = {
    "name": "hello",
    "description": "Greets in specified language",
    "args": {"lang": "language code"},
    "triggers": ["hello", "hi", "greet", "hey"]
}