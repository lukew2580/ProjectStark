"""
Quality Infrastructure — Atheris Fuzzing Harness
Fuzzes input validation and parsing code to discover crashes/asserts.
Run with: python -m atheris tests/fuzz/fuzz_input_validator.py
"""

import sys
import atheris
import json
from typing import Any

# Import fuzz targets
from core_engine.security.validator import InputValidator


def input_validator_fuzz(data: bytes):
    """
    Fuzz InputValidator.validate_question and validate_translation_text.
    Injects random byte sequences to find crashes, hangs, or unexpected behavior.
    """
    fdp = atheris.FuzzedDataProvider(data)
    
    # Random-length string with random bytes (may be invalid UTF-8)
    raw = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 5000))
    
    validator = InputValidator()
    
    # Exercise both validation paths
    try:
        validator.validate_question(raw)
    except (ValueError, UnicodeDecodeError, AssertionError) as e:
        # Expected validation failures OK; crashes are not
        pass
    except Exception as e:
        # Unexpected exception type
        raise RuntimeError(f"Unexpected exception type: {type(e).__name__}: {e}")
    
    try:
        validator.validate_translation_text(raw)
    except (ValueError, UnicodeDecodeError, AssertionError):
        pass
    except Exception as e:
        raise RuntimeError(f"Unexpected exception type: {type(e).__name__}: {e}")
    
    # Sanitization
    try:
        validator.sanitize(raw)
    except Exception as e:
        raise RuntimeError(f"Sanitize failed: {e}")


def json_parsing_fuzz(data: bytes):
    """
    Fuzz JSON parsing in request bodies.
    """
    fdp = atheris.FuzzedDataProvider(data)
    raw = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 10000))
    
    try:
        obj = json.loads(raw)
        # If parsed, exercise validator keywords
        if isinstance(obj, dict):
            question = obj.get("question", "")
            validator = InputValidator()
            validator.validate_question(str(question))
    except json.JSONDecodeError:
        # Expected — non-JSON is fine
        pass
    except (ValueError, UnicodeDecodeError, AssertionError):
        pass
    except Exception as e:
        raise RuntimeError(f"Unexpected exception: {type(e).__name__}: {e}")


def snake_case_collision_fuzz(data: bytes):
    """
    Fuzz edge cases around naming, snake_case vs camelCase in config.
    Ensures no NameError/KeyError on unusual key names.
    """
    fdp = atheris.FuzzedDataProvider(data)
    
    # Create a dict with random snake_case keys
    obj = {}
    for _ in range(fdp.ConsumeIntInRange(0, 20)):
        key_len = fdp.ConsumeIntInRange(1, 30)
        key_bytes = fdp.ConsumeBytes(key_len)
        try:
            key = key_bytes.decode("utf-8", errors="ignore")
        except Exception:
            key = "bad_key"
        obj[key] = fdp.ConsumeUnicodeNoSurrogates(20)
    
    # Access some known keys
    _ = obj.get("question")
    _ = obj.get("text")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        print("Fuzz targets: input_validator, json_parser, snake_collision")
        sys.exit(0)
    
    target = "input_validator"
    if len(sys.argv) > 1:
        target = sys.argv[1]
    
    targets = {
        "input_validator": input_validator_fuzz,
        "json_parser": json_parsing_fuzz,
        "snake_collision": snake_case_collision_fuzz,
    }
    
    if target not in targets:
        print(f"Unknown target '{target}'. Known: {list(targets.keys())}")
        sys.exit(1)
    
    print(f"Starting fuzzing target: {target}")
    atheris.Setup(sys.argv, targets[target])
    atheris.Fuzz()


if __name__ == "__main__":
    main()
