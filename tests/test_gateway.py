"""Hardwareless AI — Gateway Unit Tests"""
from gateway.app import app
from gateway.middleware.auth import get_api_key_manager, get_rate_limiter

def test_gateway_import():
    """Test gateway imports."""
    assert app is not None
    print("Gateway app: OK")

def test_api_key_manager():
    """Test API key management."""
    km = get_api_key_manager()
    keys = km.list_keys()
    assert len(keys) >= 1
    print("API Key Manager: OK")

def test_rate_limiter():
    """Test rate limiter."""
    rl = get_rate_limiter()
    assert rl.requests == 100
    assert rl.check("127.0.0.1") is True
    print("Rate Limiter: OK")

def test_gateway_routes():
    """Test gateway has routes."""
    assert len(app.routes) > 0
    print(f"Routes: {len(app.routes)}")