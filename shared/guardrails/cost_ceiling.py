"""Per-IP daily cost ceiling.

Rate limits cap REQUEST volume; this caps *units of work* (e.g., VLM pages
processed). A user can hit the request rate-limit comfortably without ever
threatening cost, but a single 100-page PDF would. The ceiling lives in
Redis as a per-(IP, YYYY-MM-DD) counter with a 26h TTL.

Contract:
- `cost_remaining(ip, max_units)` -> int : how many units this IP has left today.
- `consume_cost_units(ip, units, max_units)` -> bool :
    atomically deduct `units`; returns False if would exceed `max_units`.

This module is intentionally small and pure-Redis — same pattern translates
trivially to other stacks.
"""

from datetime import UTC, datetime

from redis import Redis


def _today_key(ip: str, namespace: str) -> str:
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    return f"{namespace}:cost:{ip}:{today}"


def cost_remaining(
    redis_client: Redis,
    ip: str,
    max_units: int,
    namespace: str = "docuai",
) -> int:
    """Return how many cost units this IP has left for today."""
    key = _today_key(ip, namespace)
    used = redis_client.get(key)
    used_int = int(used) if used else 0
    return max(0, max_units - used_int)


def consume_cost_units(
    redis_client: Redis,
    ip: str,
    units: int,
    max_units: int,
    namespace: str = "docuai",
    ttl_seconds: int = 26 * 3600,  # 26h covers the rollover safely
) -> bool:
    """Atomically reserve `units`. Returns True on success, False if it would
    exceed the daily ceiling. Uses a Redis pipeline for atomicity."""
    if units <= 0:
        return True

    key = _today_key(ip, namespace)

    # Atomic check-and-set via Lua script: only INCRBY if the resulting value
    # stays within max_units. Returns 1 (success) or 0 (rejected).
    lua = """
    local current = tonumber(redis.call('GET', KEYS[1]) or '0')
    local incr = tonumber(ARGV[1])
    local max_units = tonumber(ARGV[2])
    local ttl = tonumber(ARGV[3])
    if current + incr > max_units then
        return 0
    end
    redis.call('INCRBY', KEYS[1], incr)
    redis.call('EXPIRE', KEYS[1], ttl)
    return 1
    """

    result = redis_client.eval(
        lua,
        1,
        key,
        str(units),
        str(max_units),
        str(ttl_seconds),
    )
    return int(result) == 1
