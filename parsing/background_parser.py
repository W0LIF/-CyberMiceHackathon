import threading
import time
from concurrent.futures import ThreadPoolExecutor
from .universal_parser import UniversalParser, CONFIGURATIONS


def _run_parsing_once():
    parser = UniversalParser()
    results = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {}
        for key, cfg in CONFIGURATIONS.items():
            futures[ex.submit(parser.parse_site, cfg)] = key
        for fut in futures:
            key = futures[fut]
            try:
                items = fut.result()
                results[key] = items
            except Exception as e:
                print(f"Parsing error for {key}: {e}")
    return results


def start_background_parsing(interval_seconds: int = 3600, run_once=False):
    """Start a background thread that runs parser every `interval_seconds`.

    If `run_once` is True, run once and exit.
    """
    def _target():
        while True:
            try:
                print("[background_parser] Starting parse cycle...")
                _run_parsing_once()
                print("[background_parser] Parse cycle finished.")
            except Exception as e:
                print(f"[background_parser] Error: {e}")
            if run_once:
                break
            time.sleep(interval_seconds)

    th = threading.Thread(target=_target, daemon=True)
    th.start()
    return th


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--interval', type=int, default=3600, help='Seconds between parsing cycles')
    parser.add_argument('--run_once', action='store_true', help='Run parsing once and exit')
    args = parser.parse_args()
    start_background_parsing(interval_seconds=args.interval, run_once=args.run_once)
    if not args.run_once:
        # Keep main thread alive
        while True:
            time.sleep(60)
