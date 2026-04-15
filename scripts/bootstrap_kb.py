"""
Hardwareless AI — Polyglot Cognitive Bootstrap Engine
Parses the local repository (Python, Shell, Markdown) to generate a semantic map.
"""
import ast
import json
import re
import os
from pathlib import Path

# Directories to analyze for core intelligence
CORE_DIRS = ["core_engine", "network", "gateway", "scripts", ".antigravity"]
# Extensions to include
EXTENSIONS = {".py", ".sh", ".md"}

def extract_bash_signatures(content):
    """Simple regex to find function names and script purposes in .sh files."""
    functions = re.findall(r"^(\w+)\(\)", content, re.MULTILINE)
    return functions

def extract_markdown_concepts(content):
    """Extracts headers and key terms from markdown project maps."""
    headers = re.findall(r"^#+\s+(.+)$", content, re.MULTILINE)
    return headers

def main():
    repo_map = {
        "classes": set(),
        "functions": set(),
        "modules": set(),
        "roadmap_items": set()
    }
    
    root = Path(".")
    for dir_name in CORE_DIRS:
        target_dir = root / dir_name
        if not target_dir.exists():
            continue
            
        repo_map["modules"].add(dir_name)
        
        for file_path in target_dir.rglob("*"):
            if file_path.suffix not in EXTENSIONS or "__init__" in file_path.name:
                continue
                
            repo_map["modules"].add(file_path.stem)
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                if file_path.suffix == ".py":
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            repo_map["classes"].add(node.name)
                        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            repo_map["functions"].add(node.name)
                            
                elif file_path.suffix == ".sh":
                    repo_map["functions"].update(extract_bash_signatures(content))
                    
                elif file_path.suffix == ".md":
                    repo_map["roadmap_items"].update(extract_markdown_concepts(content))
            except:
                pass

    # Flatten and clean
    final_knowledge = sorted(list(
        repo_map["classes"] | repo_map["functions"] | repo_map["modules"] | repo_map["roadmap_items"]
    ))
    
    output_path = "knowledge_preheat.json"
    with open(output_path, "w") as f:
        json.dump(final_knowledge, f, indent=2)
        
    print(f"Polyglot Bootstrap complete. {len(final_knowledge)} concepts extracted to {output_path}")

if __name__ == "__main__":
    main()
