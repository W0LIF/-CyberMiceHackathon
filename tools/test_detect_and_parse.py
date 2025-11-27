#!/usr/bin/env python3
"""
Test category detection and one-shot background parser.

Usage:
    python tools/test_detect_and_parse.py "Как получить паспорт"
"""
import sys
import os
# Ensure project root is in path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import ai_engine
from parsing.background_parser import start_background_parsing

def main():
    if len(sys.argv) < 2:
        print('Usage: python tools/test_detect_and_parse.py "text"')
        return
    text = sys.argv[1]
    cats = ai_engine.detect_category(text)
    print('Detected categories (ranked):', cats)

    print('\nRunning one-shot parser (run_once=True)')
    start_background_parsing(interval_seconds=5, run_once=True)
    print('One-shot parsing run completed.')

if __name__ == '__main__':
    main()
