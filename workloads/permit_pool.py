"""
Worker pool with `threading.Semaphore`-managed permits.

N workers each do bulk SHA-256 hashing of large byte buffers. Before
processing a task, the worker acquires one permit from a `Semaphore(N)`
sized to the worker count. After the task, it releases the permit. With
permits == worker count there's no contention.
"""

from __future__ import annotations

import hashlib
import threading

import common

CHUNKS_PER_THREAD = common.scaled(40, 8)
CHUNK_BYTES = common.scaled(64 * 1024, 8 * 1024)

BENCH_SPEC = {
    "name": "permit_pool",
    "description": "Worker pool with Semaphore-managed permits; bulk SHA-256 hashing per task.",
    "num_threads": common.NUM_THREADS,
    "sync": "semaphore",
    "work_units": common.NUM_THREADS * CHUNKS_PER_THREAD * CHUNK_BYTES,
}


def _make_chunks(tid: int) -> list[bytes]:
    """
    Deterministic per-thread chunks (seeded only on tid).
    """
    chunks: list[bytes] = []
    for c in range(CHUNKS_PER_THREAD):
        # Build a CHUNK_BYTES buffer from a deterministic seed pattern.
        seed = (tid * 0x9E3779B1 + c * 0x85EBCA77) & 0xFFFFFFFF
        # Quick PRNG: xorshift-style fill
        out = bytearray(CHUNK_BYTES)
        s = seed or 0xDEADBEEF
        for i in range(CHUNK_BYTES):
            s ^= (s << 13) & 0xFFFFFFFF
            s ^= s >> 17
            s ^= (s << 5) & 0xFFFFFFFF
            out[i] = s & 0xFF
        chunks.append(bytes(out))
    return chunks


def _hash_with_permit(tid: int, sem: threading.Semaphore) -> int:
    chunks = _make_chunks(tid)
    local = 0
    for chunk in chunks:
        sem.acquire()
        try:
            h = hashlib.sha256(chunk).digest()
            # Fold first 8 bytes
            for j in range(8):
                local = (local + h[j]) % 10_000_019
        finally:
            sem.release()
    return local


def main_parallel() -> int:
    sem = threading.Semaphore(common.SEMAPHORE_COUNT)
    results = [0] * common.NUM_THREADS

    def worker(tid: int, _item: int) -> int:
        results[tid] = _hash_with_permit(tid, sem)
        return results[tid]

    common.parallel_for(worker, list(range(common.NUM_THREADS)))
    return sum(results) % 10_000_019


def main_serial() -> int:
    """
    Serial baseline: same per-thread work, no semaphore needed.
    """
    sem = threading.Semaphore(1)
    total = 0
    for tid in range(common.NUM_THREADS):
        total = (total + _hash_with_permit(tid, sem)) % 10_000_019
    return total


if __name__ == "__main__":
    common.run_entry(main_parallel, main_serial)
