"""
Hardwareless AI — CLI Entry Point
One-liner: curl -fsSL https://hardwareless.ai/install.sh | bash
Or:       pip install hardwareless-ai
"""
import sys
import argparse
import asyncio
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        prog="hardwareless",
        description="🧠 Hardwareless AI - GPU/CPU-less hypervector intelligence"
    )
    parser.add_argument("command", nargs="?", help="run, serve, chat, translate, skills")
    parser.add_argument("--port", "-p", type=int, default=8000, help="Gateway port")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--lang", default="en", help="Default language")
    parser.add_argument("--text", help="Text to process")
    parser.add_argument("--translate-to", help="Target language for translation")
    parser.add_argument("--version", "-v", action="store_true", help="Show version")
    parser.add_argument("--skill", help="Skill name to execute")
    parser.add_argument("--args", help="Skill arguments as JSON")
    
    args = parser.parse_args()
    
    if args.version:
        print("hardwareless-ai v0.3.0")
        return
    
    if args.command == "run" or args.command == "serve":
        run_server(args)
    elif args.command == "chat":
        chat(args)
    elif args.command == "translate":
        translate(args)
    elif args.command == "init":
        init_project()
    elif args.command == "skills":
        list_skills(args)
    elif args.command == "skill":
        run_skill(args)
    elif args.skill:
        run_skill(args)
    else:
        print("Commands: run, serve, chat, translate, init")
        print("Run 'hardwareless run --port 8000' to start gateway")
        print("Or use the one-liner: curl -fsSL https://hardwareless.ai/install.sh | bash")


def run_server(args):
    """Start the FastAPI gateway."""
    try:
        import uvicorn
        from gateway.app import app
        print(f"🚀 Starting Hardwareless AI Gateway on {args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port)
    except ImportError as e:
        print(f"Error: {e}")
        print("Install dependencies: pip install hardwareless-ai[all]")
        sys.exit(1)


def chat(args):
    """Interactive chat mode."""
    from core_engine.translation import get_weave
    
    print("🧠 Hardwareless AI Chat (Ctrl+C to exit)")
    weave = get_weave()
    
    async def chat_loop():
        while True:
            try:
                user_input = input("\n> ")
                if not user_input.strip():
                    continue
                    
                result = await weave.think(
                    input_text=user_input,
                    target_lang=args.lang
                )
                print(f"\n🤖 {result.target_text}")
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
    
    asyncio.run(chat_loop())


def translate(args):
    """Quick translation from CLI."""
    if not args.text:
        print("Error: --text required for translate")
        sys.exit(1)
    
    from core_engine.translation import setup_translation_backends
    
    setup_translation_backends(enable_mtranserver=False, enable_libretranslate=False, enable_opus_mt=False)
    from core_engine.translation import get_weave
    
    async def run_translate():
        weave = get_weave()
        result = await weave.think(
            input_text=args.text,
            target_lang=args.translate_to or "en"
        )
        print(result.target_text)
    
    asyncio.run(run_translate())


def init_project():
    """Initialize a hardwareless project."""
    import os
    
    dirs = ["config/knowledge", "skills", "memory"]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
    
    print("✅ Initialized Hardwareless AI project")
    print("   Run 'hardwareless run' to start")


def list_skills(args):
    """List all available skills."""
    from core_engine.skills import get_skills
    
    registry = get_skills()
    skills = registry.list_skills()
    
    print("🧠 Available Skills:")
    for s in skills:
        print(f"  • {s['name']}: {s['description']}")
        print(f"    Triggers: {', '.join(s['triggers'])}")


async def run_skill_async(name: str, skill_args: dict):
    """Run a skill by name."""
    from core_engine.skills import get_skills
    
    registry = get_skills()
    result = await registry.execute(name, {}, skill_args)
    return result


def run_skill(args):
    """Execute a specific skill."""
    if not args.skill:
        print("Error: --skill required")
        sys.exit(1)
    
    import json
    skill_args = {}
    if args.args:
        try:
            skill_args = json.loads(args.args)
        except:
            print("Error: --args must be valid JSON")
            sys.exit(1)
    
    result = asyncio.run(run_skill_async(args.skill, skill_args))
    print(result)


if __name__ == "__main__":
    main()