import argparse
import json
from .pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local virtauto Decision Intelligence MVP.")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", default="local_mvp/output")
    args = parser.parse_args()
    result = run_pipeline(args.csv, args.config, args.output)
    print(json.dumps({"status": result["governance"].status, "paths": result["paths"]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
