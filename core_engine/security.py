"""
Hardwareless AI — Security Layer
Virus protection, sandboxing, and input sanitization for HDC system
"""
import hashlib
import re
import ast
import asyncio
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ThreatLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Permission(Enum):
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    NETWORK = "network"
    EXECUTE = "execute"
    SHELL = "shell"
    IMPORT = "import"


@dataclass
class SecurityRule:
    """A security rule for threat detection."""
    name: str
    pattern: str
    threat_level: ThreatLevel
    description: str


@dataclass
class ThreatReport:
    """Report of a detected threat."""
    level: ThreatLevel
    threat_type: str
    description: str
    blocked: bool
    recommendations: List[str] = field(default_factory=list)


@dataclass
class SandboxedExecution:
    """Result of sandboxed execution."""
    result: Any
    blocked_permissions: List[str]
    execution_time: float
    memory_used: int


class SecurityLayer:
    """
    Security layer for Hardwareless AI.
    
    Provides:
    - Input sanitization for HDC encoding
    - Threat detection (virus, malware patterns)
    - Skill sandboxing
    - Permission management
    """
    
    def __init__(self):
        self._rules: List[SecurityRule] = []
        self._permissions: Dict[str, Set[Permission]] = {}
        self._quarantined: List[str] = []
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Set up default security rules."""
        self._rules = [
            SecurityRule(
                name="shell_injection",
                pattern=r"[;&|`$]",
                threat_level=ThreatLevel.HIGH,
                description="Shell command injection attempt"
            ),
            SecurityRule(
                name="path_traversal",
                pattern=r"\.\.[/\\]",
                threat_level=ThreatLevel.HIGH,
                description="Path traversal attempt"
            ),
            SecurityRule(
                name="sql_injection",
                pattern=r"(union|select|insert|delete|drop)\s+(from|table|into)",
                threat_level=ThreatLevel.HIGH,
                description="SQL injection pattern"
            ),
            SecurityRule(
                name="xss_pattern",
                pattern=r"<script|javascript:|onerror=|onclick=",
                threat_level=ThreatLevel.MEDIUM,
                description="Cross-site scripting pattern"
            ),
            SecurityRule(
                name="env_access",
                pattern=r"\$\{?[A-Z_]+\}?",
                threat_level=ThreatLevel.LOW,
                description="Environment variable access attempt"
            ),
            SecurityRule(
                name="dangerous_import",
                pattern=r"(import\s+os|import\s+subprocess|import\s+sys|__import__)",
                threat_level=ThreatLevel.HIGH,
                description="Dangerous module import"
            ),
            SecurityRule(
                name="eval_usage",
                pattern=r"(eval|exec|compile)\s*\(",
                threat_level=ThreatLevel.CRITICAL,
                description="Dangerous code execution"
            ),
            SecurityRule(
                name="file_write_attempt",
                pattern=r"(write|open|create)\s*\(.*['\"][/\\]",
                threat_level=ThreatLevel.HIGH,
                description="File write attempt"
            ),
        ]
    
    def scan_input(self, text: str) -> ThreatReport:
        """Scan input for threats before HDC encoding."""
        threats_found = []
        highest_level = ThreatLevel.SAFE
        
        for rule in self._rules:
            if re.search(rule.pattern, text, re.IGNORECASE):
                threats_found.append(rule)
                if rule.threat_level.value > highest_level.value:
                    highest_level = rule.threat_level
        
        if highest_level == ThreatLevel.CRITICAL:
            return ThreatReport(
                level=ThreatLevel.CRITICAL,
                threat_type="critical",
                description=f"Critical threats: {[r.name for r in threats_found]}",
                blocked=True,
                recommendations=["Block execution", "Log incident", "Notify admin"]
            )
        elif highest_level == ThreatLevel.HIGH:
            return ThreatReport(
                level=ThreatLevel.HIGH,
                threat_type="high",
                description=f"High threats: {[r.name for r in threats_found]}",
                blocked=True,
                recommendations=["Quarantine input", "Require review"]
            )
        elif highest_level == ThreatLevel.MEDIUM:
            return ThreatReport(
                level=ThreatLevel.MEDIUM,
                threat_type="medium",
                description=f"Medium threats: {[r.name for r in threats_found]}",
                blocked=False,
                recommendations=["Log warning", "Monitor closely"]
            )
        
        return ThreatReport(
            level=ThreatLevel.SAFE,
            threat_type="none",
            description="Input appears safe",
            blocked=False
        )
    
    def sanitize_input(self, text: str) -> str:
        """Sanitize input by removing dangerous patterns."""
        sanitized = text
        
        dangerous_patterns = [
            (r"[;&|`$]", ""),
            (r"\$\{[^}]+\}", ""),
            (r"eval\s*\(", ""),
            (r"exec\s*\(", ""),
            (r"<script[^>]*>", ""),
            (r"javascript:", ""),
            (r"on\w+\s*=", ""),
        ]
        
        for pattern, replacement in dangerous_patterns:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    def set_skill_permissions(self, skill_name: str, permissions: List[Permission]):
        """Set allowed permissions for a skill."""
        self._permissions[skill_name] = set(permissions)
    
    def check_permission(self, skill_name: str, permission: Permission) -> bool:
        """Check if skill has a specific permission."""
        if skill_name not in self._permissions:
            return False
        return permission in self._permissions[skill_name]
    
    def quarantine(self, item: str):
        """Quarantine a suspicious item."""
        if item not in self._quarantined:
            self._quarantined.append(item)
    
    def get_quarantine(self) -> List[str]:
        """Get list of quarantined items."""
        return self._quarantined.copy()
    
    def clear_quarantine(self):
        """Clear quarantine."""
        self._quarantined.clear()


class SkillSandbox:
    """
    Sandboxed environment for skill execution.
    Limits what skills can do to protect the system.
    """
    
    def __init__(self, security: SecurityLayer):
        self.security = security
        self._execution_count = 0
        self._max_executions = 1000
        self._timeout = 5.0
    
    async def execute_skill(
        self,
        skill_name: str,
        code: str,
        args: Dict[str, Any]
    ) -> SandboxedExecution:
        """Execute skill in sandbox."""
        self._execution_count += 1
        
        if self._execution_count > self._max_executions:
            return SandboxedExecution(
                result={"error": "Execution limit reached"},
                blocked_permissions=["execute"],
                execution_time=0,
                memory_used=0
            )
        
        blocked = []
        start_time = asyncio.get_event_loop().time()
        
        if not self.security.check_permission(skill_name, Permission.EXECUTE):
            blocked.append("execute")
        
        if not self.security.check_permission(skill_name, Permission.NETWORK):
            blocked.append("network")
        
        if not self.security.check_permission(skill_name, Permission.FILE_WRITE):
            blocked.append("file_write")
        
        threat_report = self.security.scan_input(code)
        if threat_report.blocked:
            return SandboxedExecution(
                result={"error": f"Threat detected: {threat_report.threat_type}"},
                blocked_permissions=blocked,
                execution_time=0,
                memory_used=0
            )
        
        safe_code = self.security.sanitize_input(code)
        
        result = {"sanitized_code": safe_code, "args": args}
        
        exec_time = asyncio.get_event_loop().time() - start_time
        
        return SandboxedExecution(
            result=result,
            blocked_permissions=blocked,
            execution_time=exec_time,
            memory_used=0
        )


_global_security: Optional[SecurityLayer] = None
_global_sandbox: Optional[SkillSandbox] = None


def get_security() -> SecurityLayer:
    global _global_security
    if _global_security is None:
        _global_security = SecurityLayer()
    return _global_security


def get_sandbox() -> SkillSandbox:
    global _global_sandbox
    if _global_sandbox is None:
        _global_sandbox = SkillSandbox(get_security())
    return _global_sandbox