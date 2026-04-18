"""
Config Validation & Environment Profiles
Validates env vars, YAML/JSON config files, and profile overrides.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, TypedDict
from pathlib import Path
from dataclasses import dataclass, field

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

logger = logging.getLogger("hardwareless.config")


@dataclass
class ValidationError:
    field: str
    expected: str
    actual: str
    message: str


class ConfigValidator:
    """
    Schema-based config validator.
    Validates environment variables and config files on startup.
    """
    
    SCHEMA = {
        # Core HDC
        "HDC_BACKEND": {"type": "choice", "choices": ["legacy-numpy", "torchhd"], "default": "legacy-numpy"},
        "HDC_DEVICE": {"type": "choice", "choices": ["cpu", "cuda", "mps"], "default": "cpu"},
        "HDC_DIMENSIONS": {"type": "int", "min": 100, "max": 100000, "default": 10000},
        "DEFAULT_NODE_COUNT": {"type": "int", "min": 1, "max": 1000, "default": 17},
        
        # Security
        "SECURITY_HEADERS_ENABLED": {"type": "bool", "default": "1"},
        "INPUT_VALIDATION_ENABLED": {"type": "bool", "default": "1"},
        "ENABLE_REQUEST_SIGNING": {"type": "bool", "default": "0"},
        "REQUEST_SIGNING_SECRET": {"type": "str", "default": None, "sensitive": True},
        "CORS_ALLOW_ORIGINS": {"type": "str", "default": "http://localhost:3000,http://localhost:8000"},
        
        # Backend services
        "REDIS_URL": {"type": "str", "default": None},
        "DATABASE_URL": {"type": "str", "default": None},
        
        # Translation backends
        "ENABLE_MTB": {"type": "bool", "default": "0"},
        "ENABLE_LIBRETRANSLATE": {"type": "bool", "default": "0"},
        "ENABLE_OPUS_MT": {"type": "bool", "default": "0"},
        
        # Observability
        "ENABLE_GRAPHQL": {"type": "bool", "default": "0"},
        "PROMETHEUS_METRICS_PATH": {"type": "str", "default": "/metrics"},
        
        # Cache
        "CACHE_MAX_SIZE": {"type": "int", "min": 100, "max": 1000000, "default": 10000},
        "CACHE_DISK_PATH": {"type": "str", "default": "cache_disk"},
        
        # Dev / Debug
        "DEV_MODE": {"type": "bool", "default": "0"},
        "DEBUG": {"type": "bool", "default": "0"},
        "LOG_LEVEL": {"type": "choice", "choices": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], "default": "INFO"},
        
        # Threat intel
        "THREAT_FEED_URLS": {"type": "str", "default": None},
        "ANOMALY_WEBHOOK_URL": {"type": "str", "default": None},
    }
    
    SENSITIVE_FIELDS = {"REQUEST_SIGNING_SECRET", "DATABASE_URL", "REDIS_URL"}
    
    def __init__(self):
        self.errors: List[ValidationError] = []
        self.warnings: List[str] = []
    
    def validate_all(self, schema_override: Optional[Dict[str, Any]] = None) -> bool:
        """Validate all defined schema fields from environment."""
        schema = {**self.SCHEMA, **(schema_override or {})}
        
        all_ok = True
        for field_name, rules in schema.items():
            raw = os.getenv(field_name, rules["default"])
            if raw is None and rules.get("required", False):
                self.errors.append(ValidationError(
                    field=field_name,
                    expected="required",
                    actual="missing",
                    message="Required field missing from environment"
                ))
                all_ok = False
                continue
            
            if raw is None:
                continue
            
            # Type coercion
            try:
                if rules["type"] == "int":
                    val = int(raw)
                    if "min" in rules and val < rules["min"]:
                        self.errors.append(ValidationError(field_name, f">= {rules['min']}", str(val), f"Value below minimum"))
                        all_ok = False
                    if "max" in rules and val > rules["max"]:
                        self.errors.append(ValidationError(field_name, f"<= {rules['max']}", str(val), f"Value above maximum"))
                        all_ok = False
                elif rules["type"] == "bool":
                    val = raw.lower() in ("1", "true", "yes", "on")
                elif rules["type"] == "choice":
                    if raw not in rules["choices"]:
                        self.errors.append(ValidationError(field_name, str(rules["choices"]), raw, "Invalid choice"))
                        all_ok = False
                    val = raw
                else:  # str
                    val = raw
            except ValueError:
                self.errors.append(ValidationError(field_name, rules["type"], raw, "Type conversion failed"))
                all_ok = False
            
            # Sensitive logging redaction
            if field_name in self.SENSITIVE_FIELDS and val:
                logger.info(f"Config validated: {field_name}=***REDACTED***")
            else:
                logger.info(f"Config validated: {field_name}={val}")
        
        return all_ok
    
    def validate_config_file(self, path: str) -> List[ValidationError]:
        """Validate a JSON/YAML config file has the expected structure."""
        p = Path(path)
        if not p.exists():
            return [ValidationError("config_file", "exists", path, "File not found")]
        
        try:
            with open(p) as f:
                if p.suffix in (".yaml", ".yml") and HAS_YAML:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            errors = []
            # Could expand with deep schema validation using jsonschema
            # For now, basic type checks
            for key, val in data.items():
                if key in self.SCHEMA:
                    expected_type = self.SCHEMA[key]["type"]
                    if expected_type == "int" and not isinstance(val, int):
                        errors.append(ValidationError(key, "int", str(type(val)), "Wrong type"))
                    # more...
            return errors
        except Exception as e:
            return [ValidationError(path, "valid config", "", str(e))]
    
    def log_summary(self):
        if self.errors:
            logger.error(f"Config validation FAILED with {len(self.errors)} errors")
            for err in self.errors:
                logger.error(f"  • {err.field}: {err.message}")
        else:
            logger.info("Config validation OK")


# Profile overrides (dev/staging/prod)
@dataclass
class Profile:
    name: str
    env_overrides: Dict[str, str] = field(default_factory=dict)
    enabled_features: List[str] = field(default_factory=list)
    disabled_features: List[str] = field(default_factory=list)


_PROFILES = {
    "development": Profile(
        name="development",
        env_overrides={
            "DEV_MODE": "1",
            "DEBUG": "1",
            "LOG_LEVEL": "DEBUG",
            "CORS_ALLOW_ORIGINS": "*",
            "SECURITY_HEADERS_ENABLED": "0",
            "ENABLE_REQUEST_SIGNING": "0",
        },
        enabled_features=["dev_toolbar", "hot_reload", "debug_errors"],
    ),
    "staging": Profile(
        name="staging",
        env_overrides={
            "LOG_LEVEL": "INFO",
            "CORS_ALLOW_ORIGINS": "https://staging.hardwareless.ai",
            "SECURITY_HEADERS_ENABLED": "1",
            "ENABLE_REQUEST_SIGNING": "1",
        },
        enabled_features=["audit_logging", "threat_intel"],
    ),
    "production": Profile(
        name="production",
        env_overrides={
            "LOG_LEVEL": "WARNING",
            "DEV_MODE": "0",
            "DEBUG": "0",
            "SECURITY_HEADERS_ENABLED": "1",
            "ENABLE_REQUEST_SIGNING": "1",
            "CORS_ALLOW_ORIGINS": "https://hardwareless.ai",
        },
        enabled_features=["all"],
        disabled_features=["dev_toolbar", "hot_reload", "debug_endpoints"],
    ),
}


def apply_profile(profile_name: str) -> None:
    """Load a profile by name and set its env overrides."""
    profile = _PROFILES.get(profile_name)
    if not profile:
        logger.warning(f"Unknown profile '{profile_name}'. Available: {list(_PROFILES.keys())}")
        return
    
    logger.info(f"Applying profile: {profile.name}")
    for key, val in profile.env_overrides.items():
        os.environ.setdefault(key, val)  # setdefault so explicit env vars win


# Auto-selection via ENVIRONMENT var
def auto_apply_profile():
    profile = os.getenv("ENVIRONMENT", "development").lower()
    apply_profile(profile)


__all__ = [
    "ConfigValidator",
    "ValidationError",
    "Profile",
    "apply_profile",
    "auto_apply_profile",
    "_PROFILES",
]
