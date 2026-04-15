"""
Hardwareless AI — Swarm Key Generator
Run this once to generate YOUR swarm's identity.
"""
import os
import binascii
from network.crypto import generate_key

def main():
    key = generate_key()
    key_hex = binascii.hexlify(key).decode()
    
    print("=" * 60)
    print("  HARDWARELESS AI — SWARM KEY GENERATOR")
    print("=" * 60)
    print(f"\nYour New Swarm Key (Keep this secret!):\n")
    print(f"  {key_hex}\n")
    
    key_file = ".swarm.key"
    with open(key_file, "w") as f:
        f.write(key_hex)
        
    print(f"Key saved to {key_file}")
    print("\nTo use this key across your swarm, set the SWARM_KEY")
    print("environment variable or ensure this file exists on all nodes.")
    print("=" * 60)

if __name__ == "__main__":
    main()
