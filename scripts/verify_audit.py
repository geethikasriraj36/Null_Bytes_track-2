
import argparse
import json

from aegis.audit.chain import verify_chain


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the integrity of an Aegis audit log."
    )
    parser.add_argument(
        "log",
        nargs="?",
        default="results/audit.jsonl",
        help="Path to the JSONL audit log",
    )
    args = parser.parse_args()

    result = verify_chain(args.log)
    print(json.dumps(result, indent=2))

    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
