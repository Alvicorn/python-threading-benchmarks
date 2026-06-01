"""
Hand-rolled bounded buffer using `threading.Condition`.

A `BoundedBuffer` of capacity `CAPACITY` is implemented with one
`Condition` and a backing `collections.deque`. Producers block on
"not_full" (cv.wait_for(lambda: len(buf) < cap)); consumers block on
"not_empty". Each successful put/get notifies the cv.

N_PRODUCERS producers each push ITEMS_PER_PRODUCER integers; N_CONSUMERS
consumers pull, do a small SHA-256 round, sum first 4 bytes into a
shared tally protected by a Lock.
"""

from __future__ import annotations

import collections
import hashlib
import threading

import common

ITEMS_PER_PRODUCER = common.scaled(2_500, 250)
N_PRODUCERS = 4
N_CONSUMERS = 4
CAPACITY = 128
_SENTINEL = object()

# Per-item consumer work: chained SHA-256 rounds so per-item CPU
# dominates over Condition wait/notify overhead.
HASH_ROUNDS = 32

BENCH_SPEC = {
    "name": "cv_bounded_buffer",
    "description": "Hand-rolled bounded buffer with Condition; 4 producers + 4 consumers.",
    "num_threads": N_PRODUCERS + N_CONSUMERS,
    "sync": "condition",
    "work_units": N_PRODUCERS * ITEMS_PER_PRODUCER,
}


class BoundedBuffer:
    """
    Bounded blocking buffer built directly on Condition + deque.

    `put` waits while full; `get` waits while empty. Every state change
    notifies one waiter.
    """

    def __init__(self, cap: int) -> None:
        self.cap = cap
        self.cv = threading.Condition()
        self.q: collections.deque = collections.deque()

    def put(self, x: object) -> None:
        with self.cv:
            self.cv.wait_for(lambda: len(self.q) < self.cap)
            self.q.append(x)
            self.cv.notify()

    def get(self) -> object:
        with self.cv:
            self.cv.wait_for(lambda: len(self.q) > 0)
            x = self.q.popleft()
            self.cv.notify()
            return x


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
    buf = BoundedBuffer(CAPACITY)
    tally = Tally()

    def producer(pid: int) -> None:
        base = pid * ITEMS_PER_PRODUCER + 1
        for i in range(ITEMS_PER_PRODUCER):
            buf.put(base + i)
        buf.put(_SENTINEL)

    def consumer(_cid: int) -> None:
        local = 0
        while True:
            item = buf.get()
            if item is _SENTINEL:
                break
            local += _hash_bytes_sum(item)  # type: ignore[arg-type]
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
    Same total work: hash items 1..N_PRODUCERS*ITEMS_PER_PRODUCER.
    """
    total = 0
    for item in range(1, N_PRODUCERS * ITEMS_PER_PRODUCER + 1):
        total += _hash_bytes_sum(item)
    return total % 10_000_019


if __name__ == "__main__":
    common.run_entry(main_parallel, main_serial)
