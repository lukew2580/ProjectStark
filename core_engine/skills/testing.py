"""
Skill Testing Framework
"""
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class TestStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class SkillTestCase:
    name: str
    args: Dict[str, Any]
    expected: Any


@dataclass
class SkillTestResult:
    test_name: str
    status: TestStatus
    actual: Any
    expected: Any
    duration_ms: float
    error: Optional[str] = None


class SkillTestFramework:
    """
    Testing framework for skills.
    """
    
    def __init__(self):
        self.test_results: List[SkillTestResult] = []
    
    async def test_skill(
        self,
        skill_module,
        test_cases: List[SkillTestCase]
    ) -> List[SkillTestResult]:
        """Test a skill with multiple test cases."""
        results = []
        
        for test_case in test_cases:
            start_time = asyncio.get_event_loop().time()
            
            try:
                actual = await skill_module.run({}, test_case.args)
                status = TestStatus.PASSED if actual == test_case.expected else TestStatus.FAILED
                error = None
            except Exception as e:
                actual = None
                status = TestStatus.ERROR
                error = str(e)
            
            duration = (asyncio.get_event_loop().time() - start_time) * 1000
            
            result = SkillTestResult(
                test_name=test_case.name,
                status=status,
                actual=actual,
                expected=test_case.expected,
                duration_ms=duration,
                error=error
            )
            results.append(result)
        
        self.test_results.extend(results)
        return results
    
    def get_test_summary(self) -> Dict:
        """Get test summary."""
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in self.test_results if r.status == TestStatus.FAILED)
        errors = sum(1 for r in self.test_results if r.status == TestStatus.ERROR)
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "pass_rate": f"{(passed/total*100):.1f}%" if total > 0 else "0%"
        }


_global_test_framework: Optional[SkillTestFramework] = None


def get_skill_test_framework() -> SkillTestFramework:
    global _global_test_framework
    if _global_test_framework is None:
        _global_test_framework = SkillTestFramework()
    return _global_test_framework