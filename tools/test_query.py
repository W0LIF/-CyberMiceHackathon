#!/usr/bin/env python3
"""
Simple test harness for the parser + AI pipeline.

Usage:
    python tools/test_query.py "Как получить паспорт" --category documents

This runs a quick search using the API tool and then calls the GigaChat agent with the findings.
"""
import sys
import os
import argparse
# Ensure project root is in path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import ai_engine as ai_engine
from parsing.universal_parser import UniversalParser, CONFIGURATIONS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('query', type=str, help='Query text')
    parser.add_argument('--category', type=str, default='')
    args = parser.parse_args()

    print("Running quick API search...")
    try:
        cat = args.category or (ai_engine.detect_category(args.query)[0] if ai_engine.detect_category(args.query) else 'documents')
        api_result = ai_engine.search_city_services(args.query, cat)
        print('API result:')
        print(api_result)
    except Exception as e:
        print('API error:', e)

    # Try to use cached parsed data
    try:
        import json, os
        pf = 'parsing/gu_spb_knowledge.json'
        parsed_context = ''
        if os.path.exists(pf):
            data = json.load(open(pf, encoding='utf-8'))
            matches = []
            for item in data:
                title = item.get('title') or item.get('name') or ''
                content = item.get('content') or item.get('description') or ''
                if args.query.lower() in (title + ' ' + content).lower():
                    matches.append(f"- {title}: {content[:200]}")
            parsed_context = '\n'.join(matches)
            print('Parsed result matches:')
            print(parsed_context)
    except Exception as e:
        print('Parsed search error:', e)

    combined = ''
    if api_result:
        combined += str(api_result) + '\n\n'
    if parsed_context:
        combined += parsed_context

    print('\nCalling LLM agent...')
    answer = ai_engine.ask_agent(args.query, chat_history=[], extra_context=combined)
    print('\nLLM answer:')
    print(answer)


if __name__ == '__main__':
    main()

