import argparse
import json
from pathlib import Path

from src.main import app


def render_openapi_artifact() -> str:
    return f"{json.dumps(app.openapi(), indent=2, sort_keys=True)}\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export the sandbox-controller OpenAPI document."
    )
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_openapi_artifact(), encoding="utf-8")


if __name__ == "__main__":
    main()
