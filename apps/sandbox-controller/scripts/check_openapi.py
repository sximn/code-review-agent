import argparse
from pathlib import Path

from scripts.export_openapi import render_openapi_artifact


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check the committed sandbox-controller OpenAPI document."
    )
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()

    actual = args.artifact.read_text(encoding="utf-8")
    expected = render_openapi_artifact()
    if actual != expected:
        raise SystemExit(
            f"{args.artifact} is stale. Run `make contracts` from the repository root."
        )


if __name__ == "__main__":
    main()
