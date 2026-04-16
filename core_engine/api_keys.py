"""
Hardwareless AI — User API Key Management
Users supply their own keys, we just manage them securely
"""
import os
import json
import hashlib
from typing import Optional, Dict
from dataclasses import dataclass
from pathlib import Path


@dataclass
class UserAPIKeys:
    """User's personal API keys for external services."""
    openai_key: Optional[str] = None
    anthropic_key: Optional[str] = None
    google_key: Optional[str] = None
    deepseek_key: Optional[str] = None
    custom_keys: Dict[str, str] = None
    
    def __post_init__(self):
        if self.custom_keys is None:
            self.custom_keys = {}
    
    def has_key(self, provider: str) -> bool:
        key = getattr(self, f"{provider}_key", None)
        return key is not None and key.strip() != ""
    
    def get_key(self, provider: str) -> Optional[str]:
        if provider in self.custom_keys:
            return self.custom_keys[provider]
        return getattr(self, f"{provider}_key", None)
    
    def to_dict(self) -> dict:
        return {
            "has_openai": self.has_key("openai"),
            "has_anthropic": self.has_key("anthropic"),
            "has_google": self.has_key("google"),
            "has_deepseek": self.has_key("deepseek"),
            "custom_providers": list(self.custom_keys.keys())
        }


class APIKeyManager:
    """
    Manages user-supplied API keys.
    Keys are stored encrypted at rest, only stored for session.
    """
    
    def __init__(self, keys_dir: str = "memory/keys"):
        self.keys_dir = Path(keys_dir)
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        self._session_keys: Dict[str, UserAPIKeys] = {}
    
    def _get_key_path(self, user_id: str) -> Path:
        """Get encrypted key file path for user."""
        return self.keys_dir / f"{user_id}.enc"
    
    def _encrypt_key(self, key: str) -> str:
        """Simple XOR encryption - not production grade, but obfuscates."""
        secret = os.environ.get("HARDWARELESS_SECRET", "default-secret-change-me")
        key_bytes = key.encode()
        secret_bytes = secret.encode()
        encrypted = bytes(a ^ b for a, b in zip(key_bytes, secret_bytes * (len(key_bytes) // len(secret_bytes) + 1)))
        return encrypted.hex()
    
    def _decrypt_key(self, encrypted: str) -> str:
        """Decrypt XOR encrypted key."""
        secret = os.environ.get("HARDWARELESS_SECRET", "default-secret-change-me")
        encrypted_bytes = bytes.fromhex(encrypted)
        secret_bytes = secret.encode()
        decrypted = bytes(a ^ b for a, b in zip(encrypted_bytes, secret_bytes * (len(encrypted_bytes) // len(secret_bytes) + 1)))
        return decrypted.decode()
    
    def set_keys(self, user_id: str, keys: UserAPIKeys):
        """Store user's API keys for session."""
        self._session_keys[user_id] = keys
        
        key_file = self._get_key_path(user_id)
        key_data = {
            "openai_key": self._encrypt_key(keys.openai_key) if keys.openai_key else None,
            "anthropic_key": self._encrypt_key(keys.anthropic_key) if keys.anthropic_key else None,
            "google_key": self._encrypt_key(keys.google_key) if keys.google_key else None,
            "deepseek_key": self._encrypt_key(keys.deepseek_key) if keys.deepseek_key else None,
            "custom_keys": {k: self._encrypt_key(v) for k, v in (keys.custom_keys or {}).items()}
        }
        
        with open(key_file, "w") as f:
            json.dump(key_data, f)
    
    def get_keys(self, user_id: str) -> Optional[UserAPIKeys]:
        """Retrieve user's API keys from session or disk."""
        if user_id in self._session_keys:
            return self._session_keys[user_id]
        
        key_file = self._get_key_path(user_id)
        if not key_file.exists():
            return None
        
        try:
            with open(key_file, "r") as f:
                key_data = json.load(f)
            
            keys = UserAPIKeys(
                openai_key=self._decrypt_key(key_data["openai_key"]) if key_data.get("openai_key") else None,
                anthropic_key=self._decrypt_key(key_data["anthropic_key"]) if key_data.get("anthropic_key") else None,
                google_key=self._decrypt_key(key_data["google_key"]) if key_data.get("google_key") else None,
                deepseek_key=self._decrypt_key(key_data["deepseek_key"]) if key_data.get("deepseek_key") else None,
                custom_keys={k: self._decrypt_key(v) for k, v in (key_data.get("custom_keys") or {}).items()}
            )
            
            self._session_keys[user_id] = keys
            return keys
        except Exception:
            return None
    
    def check_key_status(self, user_id: str) -> dict:
        """Return which providers user has configured."""
        keys = self.get_keys(user_id)
        if keys is None:
            return {"configured": False}
        return {"configured": True, **keys.to_dict()}
    
    def clear_keys(self, user_id: str):
        """Remove user's API keys."""
        self._session_keys.pop(user_id, None)
        key_file = self._get_key_path(user_id)
        if key_file.exists():
            key_file.unlink()


_global_key_manager: Optional[APIKeyManager] = None


def get_key_manager() -> APIKeyManager:
    global _global_key_manager
    if _global_key_manager is None:
        _global_key_manager = APIKeyManager()
    return _global_key_manager