# [C5-REAL] Exergy-Maximized
"""
CLI Tool to detect linguistic entropy, lexical diversity, and LLM slop in text.
"""

import sys
import argparse
import yaml
from babylon60.utils.linguistic_entropy import LinguisticEntropyDetector


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect linguistic entropy, lexical diversity, and LLM slop."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--text", "-t",
        type=str,
        help="Literal text string to analyze."
    )
    group.add_argument(
        "--file", "-f",
        type=str,
        help="Path to file containing the text to analyze."
    )
    group.add_argument(
        "--stdin", "-s",
        action="store_true",
        help="Read text from standard input."
    )

    args = parser.parse_args()

    text: str = ""
    if args.text:
        text = args.text
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as file:
                text = file.read()
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.stdin:
        text = sys.stdin.read()

    detector = LinguisticEntropyDetector()
    results = detector.analyze(text)

    # Print results formatted as structured YAML to minimize anergy (R2 / reglaAA)
    print(yaml.dump(results, allow_unicode=True, sort_keys=False))


if __name__ == "__main__":
    main()
