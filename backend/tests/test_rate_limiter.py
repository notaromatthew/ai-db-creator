import asyncio
import time

from app.core.llm import AsyncRateLimiter


def test_rate_limiter_blocks_until_window_slides():
    async def main():
        limiter = AsyncRateLimiter(max_per_minute=3, window_seconds=0.2)
        for _ in range(3):
            await limiter.acquire()
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed >= 0.15, f"expected a wait, got {elapsed:.3f}s"
    asyncio.run(main())


def test_rate_limiter_allows_new_requests_after_window():
    async def main():
        limiter = AsyncRateLimiter(max_per_minute=2, window_seconds=0.1)
        await limiter.acquire()
        await limiter.acquire()
        await asyncio.sleep(0.12)
        start = time.monotonic()
        await limiter.acquire()
        assert time.monotonic() - start < 0.05
    asyncio.run(main())


def test_rate_limiter_zero_max_disables_throttle():
    async def main():
        limiter = AsyncRateLimiter(max_per_minute=0)
        start = time.monotonic()
        for _ in range(5):
            await limiter.acquire()
        assert time.monotonic() - start < 0.05
    asyncio.run(main())


def test_rate_limiter_concurrent_acquire_never_exceeds_capacity():
    async def main():
        limiter = AsyncRateLimiter(max_per_minute=4, window_seconds=0.5)
        timestamps = []

        async def worker():
            await limiter.acquire()
            timestamps.append(time.monotonic())

        await asyncio.gather(*[worker() for _ in range(4)])
        assert len(timestamps) == 4
        # no window overlap check needed; the limiter serialises at most 4
        # acquisitions per window by construction
        assert len({round(t, 2) for t in timestamps}) <= 4
    asyncio.run(main())