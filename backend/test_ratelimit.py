"""Self-check for retry-after parsing. Run: python test_ratelimit.py"""
from app.generate import RateLimited, _retry_after_seconds


class _Err:  # duck-types RateLimitError: just needs .response.headers.get
    def __init__(self, retry_after):
        self.response = type("R", (), {"headers": {"retry-after": retry_after}})()


assert _retry_after_seconds(_Err("30")) == 30.0
assert _retry_after_seconds(_Err("2.5")) == 2.5
assert _retry_after_seconds(_Err(None)) is None  # header absent
assert _retry_after_seconds(_Err("garbage")) is None  # unparseable -> None, never crash

# RateLimited carries the wait through.
assert RateLimited(30.0).retry_after == 30.0
assert RateLimited().retry_after is None

print("ok")
