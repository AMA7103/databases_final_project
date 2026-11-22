import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from queries import QUERIES, close, connect


# python queries/run_queries.py             # time all 13 (median of 3 runs)
# python queries/run_queries.py 5           # time query 5 only
# python queries/run_queries.py 5 --show    # also print query 5's result


RUNS = 3
LIMIT_SECONDS = 2.0


def time_query(func, c):
    times, result = [], None
    for _ in range(RUNS):
        start = time.perf_counter()
        result = func(c)
        times.append(time.perf_counter() - start)
    return statistics.median(times), result


def main():
    args = sys.argv[1:]
    flags = {a for a in args if a.startswith("--")}
    numbers = [int(a) for a in args if not a.startswith("--")] or sorted(QUERIES)

    c = connect()
    try:
        for n in numbers:
            try:
                median, result = time_query(QUERIES[n], c)
            except NotImplementedError:
                print(f"q{n:<2} not implemented")
                continue
            status = "ok" if median <= LIMIT_SECONDS else "SLOW"
            print(f"q{n:<2} {median:8.3f}s  {status}")
            if "--show" in flags:
                print(result)
    finally:
        close(c)


if __name__ == "__main__":
    main()
