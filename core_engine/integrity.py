"""
Integrity Protection System
Multi-ecosystem verification with fallbacks for fork protection.
"""
import importlib
import os
import json
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

from config.settings import DIMENSIONS


class IntegrityStatus(Enum):
    OK = "ok"
    DEGRADED = "degraded"
    FAILED = "failed"
    MISSING = "missing"


@dataclass
class IntegrityCheck:
    module: str
    function: str
    status: IntegrityStatus
    fallback_used: bool
    error: Optional[str] = None


@dataclass 
class EcosystemReport:
    ecosystem: str
    status: IntegrityStatus
    checks: List[Dict] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)


class IntegrityGuard:
    """Multi-ecosystem integrity guard with fallbacks."""
    
    def __init__(self):
        self.checks: List[IntegrityCheck] = []
        self._fallbacks: Dict[str, Callable] = {}
        self._ecosystem_checks: Dict[str, Callable] = {}
        self._register_fallbacks()
        self._register_ecosystem_checks()
    
    def _register_fallbacks(self):
        """Register bundled fallback implementations."""
        self._fallbacks = {
            "generate_random_vector": self._fallback_vector,
            "bind": self._fallback_bind,
            "bundle": self._fallback_bundle,
            "similarity": self._fallback_similarity,
            "get_virus_detector": self._fallback_detector,
            "get_weave": self._fallback_weave,
            "get_skills": self._fallback_skills,
            "get_mass": self._fallback_mass,
            "get_registry": self._fallback_registry,
            "get_language_matrix": self._fallback_matrix,
            "encrypt_payload": self._fallback_encrypt,
            "decrypt_payload": self._fallback_decrypt,
            "get_stream_handler": self._fallback_stream,
        }
    
    def _register_ecosystem_checks(self):
        """Register ecosystem verification functions."""
        self._ecosystem_checks = {
            "core_engine": self._check_core_engine,
            "config": self._check_config,
            "skills": self._check_skills,
            "gateway": self._check_gateway,
            "network": self._check_network,
            "h1v3_runtime": self._check_runtime,
        }
    
    def verify_and_get(self, module: str, func: str) -> Any:
        """Verify and get a function, using fallback if needed."""
        try:
            mod = importlib.import_module(module)
            result = getattr(mod, func)
            self.checks.append(IntegrityCheck(module=module, function=func, status=IntegrityStatus.OK, fallback_used=False))
            return result
        except (ImportError, AttributeError) as e:
            fallback = self._fallbacks.get(func)
            if fallback:
                self.checks.append(IntegrityCheck(module=module, function=func, status=IntegrityStatus.DEGRADED, fallback_used=True, error=str(e)))
                return fallback
            self.checks.append(IntegrityCheck(module=module, function=func, status=IntegrityStatus.FAILED, fallback_used=False, error=str(e)))
            raise RuntimeError(f"Critical function missing: {module}.{func}")
    
    def _check_core_engine(self) -> EcosystemReport:
        """Verify core_engine ecosystem."""
        issues = []
        checks = []
        
        critical = [
            ("core_engine.brain.vectors", "generate_random_vector"),
            ("core_engine.brain.operations", "bind"),
            ("core_engine.brain.operations", "bundle"),
            ("core_engine.brain.operations", "similarity"),
            ("core_engine.translation", "get_weave"),
            ("core_engine.brain.memory", "get_mass"),
            ("core_engine.skills.registry", "get_skills"),
            ("core_engine.translation.registry", "get_registry"),
            ("core_engine.secure_report", "get_secure_reporter"),
        ]
        
        for module, func in critical:
            try:
                self.verify_and_get(module, func)
                checks.append({"item": f"{module}.{func}", "status": "ok"})
            except RuntimeError as e:
                checks.append({"item": f"{module}.{func}", "status": "fallback", "issue": str(e)})
                issues.append(str(e))
        
        status = IntegrityStatus.FAILED if issues else IntegrityStatus.OK
        return EcosystemReport(ecosystem="core_engine", status=status, checks=checks, issues=issues)
    
    def _check_config(self) -> EcosystemReport:
        """Verify config ecosystem."""
        issues = []
        checks = []
        
        from config.settings import BASE_DIR, KNOWLEDGE_DIR, DIMENSIONS
        
        if not os.path.exists(BASE_DIR):
            issues.append("BASE_DIR missing")
        else:
            checks.append({"item": "BASE_DIR", "status": "ok"})
        
        if not os.path.exists(KNOWLEDGE_DIR):
            issues.append("KNOWLEDGE_DIR missing")
        else:
            checks.append({"item": "KNOWLEDGE_DIR", "status": "ok"})
            vocab_path = os.path.join(KNOWLEDGE_DIR, "global_lexicon.json")
            if os.path.exists(vocab_path):
                try:
                    with open(vocab_path) as f:
                        data = json.load(f)
                    checks.append({"item": "global_lexicon.json", "status": "ok", "entries": len(data) if isinstance(data, dict) else len(data)})
                except Exception as e:
                    issues.append(f"global_lexicon.json corrupted: {e}")
            else:
                issues.append("global_lexicon.json missing")
        
        if DIMENSIONS < 1000:
            issues.append(f"DIMENSIONS too small: {DIMENSIONS}")
        else:
            checks.append({"item": "DIMENSIONS", "status": "ok", "value": DIMENSIONS})
        
        status = IntegrityStatus.FAILED if issues else IntegrityStatus.OK
        return EcosystemReport(ecosystem="config", status=status, checks=checks, issues=issues)
    
    def _check_skills(self) -> EcosystemReport:
        """Verify skills ecosystem."""
        issues = []
        checks = []
        
        required_skills = ["translate_skill", "scam_detect", "virus_scan", "memory_recall"]
        
        for skill_name in required_skills:
            try:
                importlib.import_module(f"skills.{skill_name}")
                checks.append({"item": f"skills.{skill_name}", "status": "ok"})
            except ImportError:
                handler = self._fallbacks.get(f"{skill_name}_skill")
                if handler:
                    checks.append({"item": f"skills.{skill_name}", "status": "fallback"})
                else:
                    issues.append(f"skills.{skill_name} missing")
        
        status = IntegrityStatus.FAILED if issues else IntegrityStatus.OK
        return EcosystemReport(ecosystem="skills", status=status, checks=checks, issues=issues)
    
    def _check_gateway(self) -> EcosystemReport:
        """Verify gateway ecosystem."""
        issues = []
        checks = []
        
        routes = ["chat", "health", "evidence", "websocket", "models", "stats"]
        
        for route in routes:
            try:
                importlib.import_module(f"gateway.routes.{route}")
                checks.append({"item": f"gateway.routes.{route}", "status": "ok"})
            except ImportError:
                issues.append(f"gateway.routes.{route} missing")
        
        try:
            importlib.import_module("gateway.app")
            checks.append({"item": "gateway.app", "status": "ok"})
        except ImportError:
            issues.append("gateway.app missing")
        
        status = IntegrityStatus.FAILED if issues else IntegrityStatus.OK
        return EcosystemReport(ecosystem="gateway", status=status, checks=checks, issues=issues)
    
    def _check_network(self) -> EcosystemReport:
        """Verify network ecosystem."""
        issues = []
        checks = []
        
        network_modules = ["crypto", "protocol", "stream_server", "stream_client", "remote_node"]
        
        for mod in network_modules:
            try:
                importlib.import_module(f"network.{mod}")
                checks.append({"item": f"network.{mod}", "status": "ok"})
            except ImportError:
                issues.append(f"network.{mod} missing")
        
        status = IntegrityStatus.FAILED if issues else IntegrityStatus.OK
        return EcosystemReport(ecosystem="network", status=status, checks=checks, issues=issues)
    
    def _check_runtime(self) -> EcosystemReport:
        """Verify h1v3_runtime ecosystem."""
        issues = []
        checks = []
        
        runtime_modules = ["runtime", "vector", "packet"]
        
        for mod in runtime_modules:
            try:
                importlib.import_module(f"h1v3_runtime.{mod}")
                checks.append({"item": f"h1v3_runtime.{mod}", "status": "ok"})
            except ImportError:
                issues.append(f"h1v3_runtime.{mod} missing")
        
        status = IntegrityStatus.FAILED if issues else IntegrityStatus.OK
        return EcosystemReport(ecosystem="h1v3_runtime", status=status, checks=checks, issues=issues)
    
    def verify_all_ecosystems(self) -> Dict:
        """Verify all ecosystems."""
        results = {"ecosystems": [], "overall": IntegrityStatus.OK, "has_degraded": False}
        
        for eco_name, check_func in self._ecosystem_checks.items():
            report = check_func()
            results["ecosystems"].append({
                "ecosystem": report.ecosystem,
                "status": report.status.value,
                "issues": report.issues,
                "checks": report.checks
            })
            if report.status == IntegrityStatus.FAILED:
                results["overall"] = IntegrityStatus.FAILED
            elif report.status == IntegrityStatus.DEGRADED:
                results["has_degraded"] = True
                if results["overall"] != IntegrityStatus.FAILED:
                    results["overall"] = IntegrityStatus.DEGRADED
        
        return results
    
    def _fallback_vector(self, dimensions: int = DIMENSIONS, seed: int = 42) -> np.ndarray:
        np.random.seed(seed % (2**31))
        return np.random.choice([-1, 1], size=dimensions).astype(np.float32)
    
    def _fallback_bind(self, v1: np.ndarray, v2: np.ndarray) -> np.ndarray:
        return (v1 * v2).astype(np.float32)
    
    def _fallback_bundle(self, vectors: List[np.ndarray]) -> np.ndarray:
        if not vectors:
            return np.zeros(DIMENSIONS, dtype=np.float32)
        stacked = np.stack(vectors)
        return (np.sign(stacked.sum(axis=0)) * (np.abs(stacked.sum(axis=0)) > 0)).astype(np.float32)
    
    def _fallback_similarity(self, v1: np.ndarray, v2: np.ndarray, dimensions: int = DIMENSIONS) -> float:
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(v1, v2) / (norm1 * norm2))
    
    def _fallback_detector(self):
        return _FallbackVirusDetector()
    
    def _fallback_weave(self):
        return _FallbackWeave()
    
    def _fallback_skills(self):
        return _FallbackSkillRegistry()
    
    def _fallback_mass(self):
        return _FallbackMemory()
    
    def _fallback_registry(self):
        return _FallbackBackendRegistry()
    
    def _fallback_matrix(self):
        return _FallbackLanguageMatrix()
    
    def _fallback_encrypt(self, data: bytes, key: bytes) -> bytes:
        return data
    
    def _fallback_decrypt(self, data: bytes, key: bytes) -> bytes:
        return data
    
    def _fallback_stream(self):
        return _FallbackStreamHandler()


class _FallbackVirusDetector:
    async def scan_data(self, data: bytes) -> Dict:
        return {"status": "degraded", "virus_name": "Unknown", "confidence": 0.0, "actions_taken": ["Using fallback"], "vector_similarity": 0.0}
    async def scan_file(self, file_path: str) -> Dict:
        return await self.scan_data(b"")


class _FallbackWeave:
    async def think(self, text: str, **kwargs) -> Dict:
        return {"target_text": text, "lang": "en", "similarity": 0.0}


class _FallbackSkillRegistry:
    async def execute(self, trigger: str, context: dict, args: dict) -> Dict:
        return {"error": "Using fallback - skill execution unavailable"}


class _FallbackMemory:
    def memorize(self, key: str, vector: Optional[np.ndarray] = None, mass: float = 1.0) -> None:
        pass
    def get_weighted_vector(self, key: str, dimensions: int = DIMENSIONS) -> np.ndarray:
        return np.zeros(dimensions, dtype=np.float32)
    def top_concepts(self, n: int) -> List[str]:
        return []


class _FallbackBackendRegistry:
    def get_status(self) -> Dict:
        return {"status": "degraded", "backends": []}


class _FallbackLanguageMatrix:
    def encode_text(self, text: str, lang: str = "en") -> np.ndarray:
        return np.zeros(DIMENSIONS, dtype=np.float32)


class _FallbackStreamHandler:
    async def send(self, data: Any) -> bool:
        return False


_guard: Optional[IntegrityGuard] = None


def get_integrity_guard() -> IntegrityGuard:
    global _guard
    if _guard is None:
        _guard = IntegrityGuard()
    return _guard


def verify_core_components() -> Dict:
    """Legacy function for backward compatibility."""
    return get_integrity_guard().verify_all_ecosystems()


def verify_ecosystem(name: str) -> EcosystemReport:
    """Verify a specific ecosystem."""
    guard = get_integrity_guard()
    check_func = guard._ecosystem_checks.get(name)
    if check_func:
        return check_func()
    return EcosystemReport(ecosystem=name, status=IntegrityStatus.FAILED, issues=[f"Unknown ecosystem: {name}"])