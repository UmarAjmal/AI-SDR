import pytest
import asyncio
from packages.common.distributed_lock import DistributedLock, LockAcquisitionError

@pytest.mark.asyncio
async def test_distributed_lock_acquire_and_release():
    lock_key = "test_lock_unique_1"

    async with DistributedLock(lock_key, ttl_seconds=5) as lock:
        assert lock.acquired is True
        # Attempting to acquire the same lock concurrently must fail
        lock2 = DistributedLock(lock_key, ttl_seconds=5, max_retries=0)
        acquired2 = await lock2.acquire()
        assert acquired2 is False

    # After exiting block, lock should be released and acquirable again
    lock3 = DistributedLock(lock_key, ttl_seconds=5)
    acquired3 = await lock3.acquire()
    assert acquired3 is True
    await lock3.release()

@pytest.mark.asyncio
async def test_distributed_lock_double_send_prevention():
    workspace_id = "ws-test-double-send"
    lead_id = "lead-12345"
    lock_key = f"send_lock:{workspace_id}:{lead_id}"

    send_count = 0

    async def simulate_outbound_send(delay: float):
        nonlocal send_count
        try:
            async with DistributedLock(lock_key, ttl_seconds=10, max_retries=0):
                # Simulate work
                await asyncio.sleep(delay)
                send_count += 1
                return "SENT"
        except LockAcquisitionError:
            return "LOCKED"

    # Run two concurrent send requests for the same lead
    results = await asyncio.gather(
        simulate_outbound_send(0.05),
        simulate_outbound_send(0.05)
    )

    # Exactly one must succeed and one must be locked out
    assert results.count("SENT") == 1
    assert results.count("LOCKED") == 1
    assert send_count == 1
