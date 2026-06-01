"""
Producer-consumer with a bounded `queue.Queue`.

N_PRODUCERS producers each enqueue ITEMS_PER_PRODUCER integers.
N_CONSUMERS consumers take items, do a small SHA-256 round, sum the
first 4 bytes of the digest. Each producer sends a `None` sentinel
when done. Producer/consumer counts match so each consumer sees
exactly one sentinel and exits. Race-free: queue.Queue is thread-safe
(it's built on Condition + Lock internally).

Final checksum is deterministic in the *set* of items produced
(1..N_PRODUCERS*ITEMS_PER_PRODUCER). Consumer interleaving does not
change the sum.
"""

from __future__ import annotations

import hashlib
import queue
import threading

import common

ITEMS_PER_PRODUCER = common.scaled(2_500, 250)
N_PRODUCERS = 4
N_CONSUMERS = 4

# Per-item consumer work: chained SHA-256 rounds. Set high enough that
# per-item CPU dominates queue.put / queue.get overhead, otherwise the
# parallel version is purely queue-contention bound and serial wins.
HASH_ROUNDS = 32

BENCH_SPEC = {
    "name": "producer_consumer",
    "description": "4 producers + 4 consumers communicating via a bounded queue.Queue.",
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
    q: queue.Queue = queue.Queue(maxsize=128)
    tally = Tally()
    SENTINEL = None

    def producer(pid: int) -> None:
        base = pid * ITEMS_PER_PRODUCER + 1
        for i in range(ITEMS_PER_PRODUCER):
            q.put(base + i)
        q.put(SENTINEL)

    def consumer(_cid: int) -> None:
        local = 0
        while True:
            item = q.get()
            if item is SENTINEL:
                break
            local += _hash_bytes_sum(item)
        with tally.lock:
            tally.total += local

    threads = []
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
    Same total work as the parallel version: hash items
    1..N_PRODUCERS*ITEMS_PER_PRODUCER, fold first 4 bytes.
    """
    total = 0
    for item in range(1, N_PRODUCERS * ITEMS_PER_PRODUCER + 1):
        total += _hash_bytes_sum(item)
    return total % 10_000_019


if __name__ == "__main__":
    common.run_entry(main_parallel, main_serial)
