"""
Producer-consumer over `queue.PriorityQueue`.

N_PRODUCERS producers each enqueue ITEMS_PER_PRODUCER tuples
`(priority, payload)`. Consumers pop in priority order, hash the
payload, sum first 4 bytes into a shared tally. The final answer is
order-independent in the multi-set of payloads (which is fixed), so the
parallel and serial answers agree.
"""

from __future__ import annotations

import hashlib
import queue
import threading

import common

ITEMS_PER_PRODUCER = common.scaled(2_500, 250)
N_PRODUCERS = 4
N_CONSUMERS = 4

# Per-item consumer work: chained SHA-256 rounds so per-item CPU
# dominates over PriorityQueue heap-push/pop + lock overhead.
HASH_ROUNDS = 32

BENCH_SPEC = {
    "name": "priority_pipeline",
    "description": "4 producers + 4 consumers communicating via queue.PriorityQueue.",
    "num_threads": N_PRODUCERS + N_CONSUMERS,
    "sync": "queue",
    "work_units": N_PRODUCERS * ITEMS_PER_PRODUCER,
}


class Tally:
    def __init__(self) -> None:
        self.total = 0
        self.lock = threading.Lock()


def _hash_bytes_sum(item: int) -> int:
    h = hashlib.sha256(str(item).encode()).digest()
    for _ in range(HASH_ROUNDS - 1):
        h = hashlib.sha256(h).digest()
    return h[0] + h[1] + h[2] + h[3]


def main_parallel() -> int:
    # Use a *very high* priority sentinel so consumers see all real items first.
    SENTINEL_PRIORITY = 10**18
    SENTINEL_PAYLOAD = -1
    q: queue.PriorityQueue = queue.PriorityQueue(maxsize=128)
    tally = Tally()

    def producer(pid: int) -> None:
        base = pid * ITEMS_PER_PRODUCER + 1
        for i in range(ITEMS_PER_PRODUCER):
            item = base + i
            # Priority is just `item`'s low bits xor'd with pid for spread
            # final tally is invariant to order so any priority works.
            prio = ((item * 2654435761) & 0xFFFFFFFF) ^ pid
            q.put((prio, item))
        q.put((SENTINEL_PRIORITY, SENTINEL_PAYLOAD))

    def consumer(_cid: int) -> None:
        local = 0
        while True:
            _prio, payload = q.get()
            if payload == SENTINEL_PAYLOAD:
                break
            local += _hash_bytes_sum(payload)
        with tally.lock:
            tally.total += local

    threads: list[threading.Thread] = []
    assert N_PRODUCERS == N_CONSUMERS
    for pid in range(N_PRODUCERS):
        t = threading.Thread(target=producer, args=(pid,))
        threads.append(t)
        t.start()
    for cid in range(N_CONSUMERS):
        t = threading.Thread(target=consumer, args=(cid,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

    return tally.total % 10_000_019


def main_serial() -> int:
    """
    Same total work, no queue: hash items 1..N_PRODUCERS*ITEMS_PER_PRODUCER.
    """
    total = 0
    for item in range(1, N_PRODUCERS * ITEMS_PER_PRODUCER + 1):
        total += _hash_bytes_sum(item)
    return total % 10_000_019


if __name__ == "__main__":
    common.run_entry(main_parallel, main_serial)
