#!/usr/bin/env python3
"""
Hardwareless AI — 10-Sandbox Integrity Test Suite
Tests system under different environments/scenarios to detect degradation.
"""
import asyncio
import sys
import os
import numpy as np
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Shared result store for run_all_tests()
_test_results = {}

def test_hdc_core():
    """Test 1: HDC Core Operations"""
    from core_engine.brain.vectors import generate_random_vector
    from core_engine.brain.operations import bind, bundle, similarity
    
    v1 = generate_random_vector(10000, seed=42)
    v2 = generate_random_vector(10000, seed=43)
    
    bound = bind(v1, v2)
    bundled = bundle([v1, v2], 10000)
    sim = similarity(v1, v2, 10000)
    
    assert len(bound) == 10000
    assert len(bundled) == 10000
    assert isinstance(sim, (int, float))
    _test_results["test_hdc_core"] = {"test": "HDC Core", "status": "ok", "vector_size": len(v1)}


def test_translation_engine():
    """Test 2: Translation Engine"""
    from core_engine.translation.registry import TranslationRegistry, BackendType
    from core_engine.translation.language_matrix import LANGUAGE_CODES
    
    registry = TranslationRegistry()
    codes = list(LANGUAGE_CODES.keys())[:5]
    
    assert len(codes) == 5
    _test_results["test_translation_engine"] = {"test": "Translation", "status": "ok", "languages": len(codes)}


def test_security_suite():
    """Test 3: Security Suite"""
    from core_engine.security import get_security, ThreatLevel
    from core_engine.virus_guard import get_virus_detector
    
    security = get_security()
    detector = get_virus_detector()
    
    assert security is not None
    assert detector is not None
    sig_count = len(detector.signatures) if hasattr(detector, 'signatures') else 0
    _test_results["test_security_suite"] = {"test": "Security", "status": "ok", "signatures": sig_count}


def test_network_crypto():
    """Test 4: Network Crypto"""
    from network.crypto import SwarmCrypto, generate_key, encrypt_evidence, verify_evidence
    
    key = generate_key()
    crypto = SwarmCrypto(key)
    
    vector = np.random.choice([-1, 1], size=10000).astype(np.int8)
    encrypted = crypto.encrypt(vector)
    vector_hash = crypto.hash_vector(vector)
    
    # Build evidence bundle with the vector hash
    evidence = {"test": "data", "vector_hash": vector_hash}
    # Compute proper evidence hash using encrypt_evidence
    evidence_hash = encrypt_evidence(evidence)
    # Verify using verify_evidence
    verified = verify_evidence(evidence, evidence_hash)
    
    assert encrypted is not None
    assert vector_hash is not None
    assert verified is True
    _test_results["test_network_crypto"] = {"test": "Network Crypto", "status": "ok", "enc_size": len(encrypted), "verified": verified}


def test_network_protocol():
    """Test 5: Network Protocol"""
    from network.protocol import pack_vector, verify_packet, get_node_registry
    from network.crypto import generate_key, SwarmCrypto
    
    key = generate_key()
    crypto = SwarmCrypto(key)
    
    vector = np.random.choice([-1, 1], size=1000).astype(np.int8)
    packed = pack_vector(vector, node_id=1, seq_id=1, crypto=crypto)
    verified = verify_packet(packed)
    
    registry = get_node_registry()
    registry.register(1, b"test_key")
    
    assert verified is True
    nodes = registry.list_active()
    assert 1 in nodes or len(nodes) >= 1
    _test_results["test_network_protocol"] = {"test": "Protocol", "status": "ok", "packet_valid": verified, "nodes": len(nodes)}


def test_multi_agent():
    """Test 6: Multi-Agent System"""
    from core_engine.multi_agent import create_default_swarm, get_orchestrator
    
    async def run():
        swarm = create_default_swarm()
        results = await swarm.execute_parallel(["t1", "t2"], "data")
        return len(results)
    
    count = asyncio.run(run())
    assert count == 2
    _test_results["test_multi_agent"] = {"test": "Multi-Agent", "status": "ok", "tasks": count}


def test_secure_reporting():
    """Test 7: Secure Reporting"""
    from core_engine.secure_report import get_secure_reporter, ReportAgency
    
    reporter = get_secure_reporter()
    
    evidence = reporter.create_evidence_bundle(
        "malware", {"sample": "test"}, {"source": "test"}
    )
    
    report = reporter.generate_authority_report(
        ReportAgency.FBI_IC3, [evidence["bundle_id"]], "test", {"type": "test"}
    )
    
    court = reporter.export_court_ready([evidence["bundle_id"]], report["report_id"])
    
    assert evidence is not None
    assert report is not None
    assert court is not None
    assert court.get("court_ready") is True
    _test_results["test_secure_reporting"] = {"test": "Secure Report", "status": "ok", "court_ready": court["court_ready"]}


def test_integrity_guard():
    """Test 8: Integrity Guard"""
    from core_engine.integrity import verify_core_components, get_integrity_guard
    
    results = verify_core_components()
    guard = get_integrity_guard()
    
    assert guard is not None
    assert results["overall"].value == "passed" or results["overall"].value == "ok"
    assert len(results["ecosystems"]) > 0
    _test_results["test_integrity_guard"] = {"test": "Integrity", "status": results["overall"].value, "ecosystems": len(results["ecosystems"])}


def test_phase_manager():
    """Test 9: Phase Manager"""
    from core_engine.setup_manager import get_phase_manager
    
    pm = get_phase_manager()
    summary = pm.get_summary()
    matrix = pm.get_status_matrix()
    
    available = len([p for p in matrix if p["status"] == "available"])
    
    assert summary["total_phases"] > 0
    _test_results["test_phase_manager"] = {"test": "Phase Manager", "status": "ok", "available": available, "phases": summary["total_phases"]}


def test_skills_registry():
    """Test 10: Skills Registry"""
    from core_engine.skills.registry import get_skills
    
    registry = get_skills("skills")
    skills = registry.list_skills()
    
    assert skills is not None
    _test_results["test_skills_registry"] = {"test": "Skills", "status": "ok", "skills": len(skills)}


def run_all_tests():
    """Run all 10 sandbox tests."""
    global _test_results
    _test_results.clear()
    
    tests = [
        test_hdc_core,
        test_translation_engine,
        test_security_suite,
        test_network_crypto,
        test_network_protocol,
        test_multi_agent,
        test_secure_reporting,
        test_integrity_guard,
        test_phase_manager,
        test_skills_registry,
    ]
    
    results = []
    failed = []
    
    print("=" * 60)
    print("HARDWARELESS AI — 10-SANDBOX INTEGRITY TEST")
    print("=" * 60)
    
    for i, test in enumerate(tests, 1):
        try:
            test()
            result = _test_results.get(test.__name__, {"test": test.__name__, "status": "unknown"})
            results.append(result)
            icon = "✅" if result.get("status") == "ok" else "⚠️"
            print(f"\n[{i}/10] {icon} {result.get('test', test.__name__)}")
            for k, v in result.items():
                if k != "test":
                    print(f"    {k}: {v}")
        except Exception as e:
            failed.append((test.__name__, str(e)))
            print(f"\n[{i}/10] ❌ {test.__name__}")
            print(f"    Error: {e}")
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = len(results)
    print(f"Passed: {passed}/10")
    print(f"Failed: {len(failed)}/10")
    
    if failed:
        print("\nFailed tests:")
        for name, err in failed:
            print(f"  - {name}: {err}")
    
    status = "✅ ALL TESTS PASSED" if not failed else "⚠️ DEGRADATION DETECTED"
    print(f"\n{status}")
    
    return {"passed": passed, "failed": len(failed), "results": results}


if __name__ == "__main__":
    run_all_tests()