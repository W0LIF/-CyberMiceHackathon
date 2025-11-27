#!/usr/bin/env python3
"""
Run background parsing service as a standalone process.
"""
import os
from parsing.background_parser import start_background_parsing

def main():
    interval = int(os.getenv('PARSER_INTERVAL_SECONDS', '3600'))
    run_once = os.getenv('PARSER_RUN_ONCE', 'false').lower() in ('1','true','yes')
    print(f"Starting parser service with interval={interval}, run_once={run_once}")
    th = start_background_parsing(interval_seconds=interval, run_once=run_once)
    if run_once:
        return
    try:
        while True:
            # keep the main thread alive
            th.join(timeout=60)
    except KeyboardInterrupt:
        print('Stopping parser service...')

if __name__ == '__main__':
    main()
