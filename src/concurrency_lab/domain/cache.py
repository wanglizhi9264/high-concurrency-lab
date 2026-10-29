"""Pure expiration rule; the service owns randomness and Redis owns publication."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CacheTtl:
    ttl_seconds: int

    def __post_init__(self) -> None:
        if type(self.ttl_seconds) is not int or not 1 <= self.ttl_seconds <= 60:
            raise ValueError("Cache TTL must be an integer from 1 to 60 seconds")

    @property
    def jitter_limit_ms(self) -> int:
        """Spread expiration over an additional 0..10% of the requested TTL."""
        return self.ttl_seconds * 100

    def expiration_ms(self, jitter_ms: int) -> int:
        if type(jitter_ms) is not int or not 0 <= jitter_ms <= self.jitter_limit_ms:
            raise ValueError("TTL jitter outside the declared integer window")
        return self.ttl_seconds * 1000 + jitter_ms
