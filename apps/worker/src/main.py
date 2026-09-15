import sys

import requests

from apps.worker.src.agent import PRMetadata, run_agent_review
from apps.worker.src.pr_diff import GitHubError, fetch_pr


def main() -> int:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} OWNER/REPOSITORY PR_NUMBER")
        return 2

    repo = sys.argv[1]
    pr_number = int(sys.argv[2])

    try:
        pr = fetch_pr(repo, pr_number)

        review = run_agent_review(
            pr_metadata=PRMetadata(
                title=pr["title"], description=pr["description"], diff=pr["diff"]
            )
        )

        print(f"Repository: {pr['repository']} ({pr['visibility']})")
        print(f"PR #{pr['pr_number']}: {pr['title']}")
        print("\nDescription:")
        print(pr["description"] or "(No description)")

        print("\nDiff:")
        print(pr["diff"])

        print("\n\nReview:")
        print(review)

        return 0

    except GitHubError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    except requests.RequestException as error:
        print(f"Network error while contacting GitHub: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
