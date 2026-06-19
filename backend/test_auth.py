"""Self-check for the API-key auth decision. Run: python test_auth.py"""
from app.auth import _ok

# Disabled when no key configured.
assert _ok("", None) is True
assert _ok("", "anything") is True
# Enabled: exact match passes, everything else fails.
assert _ok("secret", "secret") is True
assert _ok("secret", "wrong") is False
assert _ok("secret", "") is False
assert _ok("secret", None) is False

print("ok")
