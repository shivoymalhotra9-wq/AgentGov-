#!/usr/bin/env python3
"""AgentGov Day 2 - token service, standalone version 1.

Two keys, two jobs:
  token_private.pem - mints tokens. Token service only. Never share,
      never push to GitHub. File permission 600.
  token_public.pem  - verifies tokens. Shim only, later. Public, safe
      to share inside the project, it cannot mint a token.

A token is a RS256 JWT, 5 minutes only:
  sub  = agent id, e.g. infra-drafter
  group = agent's group, e.g. infra-drafters
  capability = e.g. DRAFT_WRITE
  iss  = agentgov-token-service
  iat  = issued now, exp = now + 5 minutes

The language model never sees a token. The shim never mints one.

Usage, one step at a time, from inside the AgentGov folder:
  python3 token_service.py mint infra-drafter
      - creates keys on first run, prints a token
  python3 token_service.py verify <token>
      - prints the decoded token, or BLOCK / expired / invalid

This file does NOT change the shim yet. That is the next session.
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt

BASE = Path(__file__).parent
PRIVATE_KEY_FILE = BASE / "token_private.pem"
PUBLIC_KEY_FILE = BASE / "token_public.pem"


def load_or_create_keys():
    """Return (private_pem, public_pem). Create once, reuse after."""
    if PRIVATE_KEY_FILE.exists() and PUBLIC_KEY_FILE.exists():
        return PRIVATE_KEY_FILE.read_bytes(), PUBLIC_KEY_FILE.read_bytes()
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    PRIVATE_KEY_FILE.write_bytes(private_pem)
    PUBLIC_KEY_FILE.write_bytes(public_pem)
    try:
        PRIVATE_KEY_FILE.chmod(0o600)
    except Exception:
        pass
    print("Keys created: token_private.pem (600, private) + token_public.pem")
    return private_pem, public_pem


def mint(agent_id, group, capability, minutes=5):
    private_pem, _public_pem = load_or_create_keys()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": agent_id,
        "group": group,
        "capability": capability,
        "iss": "agentgov-token-service",
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, private_pem, algorithm="RS256")


def verify(token):
    _private_pem, public_pem = load_or_create_keys()
    return jwt.decode(
        token, public_pem, algorithms=["RS256"],
        issuer="agentgov-token-service",
    )


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 token_service.py mint <agent_id> | verify <token>")
        return 1
    if sys.argv[1] == "mint":
        # v1: drafter only, hard-coded group/capability from agents.yaml.
        # Later versions will read agents.yaml instead of hard-coding.
        agent_id = sys.argv[2] if len(sys.argv) > 2 else "infra-drafter"
        if agent_id != "infra-drafter":
            print("v1 mints only for infra-drafter, for now.")
            return 1
        token = mint(agent_id, "infra-drafters", "DRAFT_WRITE", minutes=5)
        print(token)
        return 0
    if sys.argv[1] == "verify":
        if len(sys.argv) < 3:
            print("Usage: python3 token_service.py verify <token>")
            return 1
        try:
            decoded = verify(sys.argv[2])
        except jwt.ExpiredSignatureError:
            print("BLOCK - token expired")
            return 1
        except Exception as e:
            print("BLOCK - invalid token: " + str(e))
            return 1
        print("OK - verified:")
        for k in ("sub", "group", "capability", "iss", "exp"):
            print("  " + k + ": " + str(decoded.get(k)))
        return 0
    print("Usage: python3 token_service.py mint <agent_id> | verify <token>")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
