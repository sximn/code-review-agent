import os

import requests

API_ROOT = "https://api.github.com"


class GitHubError(Exception):
    pass


def github_headers(token: str | None, accept: str) -> dict[str, str]:
    headers = {
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    return headers


def validate_token(session: requests.Session, token: str) -> None:
    response = session.get(
        f"{API_ROOT}/user",
        headers=github_headers(token, "application/vnd.github+json"),
        timeout=30,
    )

    if response.status_code == 401:
        raise GitHubError("The GITHUB_TOKEN is invalid or expired.")

    if response.status_code == 403:
        raise GitHubError(
            "The GITHUB_TOKEN was rejected or GitHub rate limits were exceeded."
        )

    response.raise_for_status()


def fetch_pr(repo: str, pr_number: int):
    token = os.getenv("GITHUB_TOKEN")

    with requests.Session() as session:
        # if present, verify the token before request
        if token:
            try:
                validate_token(session, token)
            except GitHubError as error:
                raise GitHubError(str(error)) from error

        # check if the repository is visible to this request
        repo_response = session.get(
            f"{API_ROOT}/repos/{repo}",
            headers=github_headers(token, "application/vnd.github+json"),
            timeout=30,
        )

        if repo_response.status_code == 401:
            raise GitHubError("The GITHUB_TOKEN is invalid or expired.")

        if repo_response.status_code == 404:
            if token:
                raise GitHubError(
                    "The repository does not exist, or this token does not have access "
                    "to the private repository."
                )

            raise GitHubError(
                "The repository is either private and GITHUB_TOKEN is missing, "
                "or the repository does not exist."
            )

        if repo_response.status_code == 403:
            raise GitHubError(
                "Access was forbidden. Check token permissions or GitHub rate limits."
            )

        repo_response.raise_for_status()

        repo_data = repo_response.json()
        visibility = "private" if repo_data["private"] else "public"

        # fetch PR metadata: title + description
        pr_url = f"{API_ROOT}/repos/{repo}/pulls/{pr_number}"

        metadata_response = session.get(
            pr_url,
            headers=github_headers(token, "application/vnd.github+json"),
            timeout=30,
        )

        if metadata_response.status_code == 404:
            raise GitHubError(
                f"Repository is {visibility}, but pull request "
                f"#{pr_number} does not exist."
            )

        if metadata_response.status_code == 401:
            raise GitHubError("GITHUB_TOKEN is invalid or expired.")

        if metadata_response.status_code == 403:
            raise GitHubError(
                "PR access forbidden or GitHub rate limits were exceeded."
            )

        metadata_response.raise_for_status()
        metadata = metadata_response.json()

        # fetch the unified diff
        diff_response = session.get(
            pr_url,
            headers=github_headers(token, "application/vnd.github.v3.diff"),
            timeout=30,
        )
        diff_response.raise_for_status()

        return {
            "repository": repo,
            "visibility": visibility,
            "pr_number": pr_number,
            "title": metadata["title"],
            "description": metadata["body"] or "",
            "diff": diff_response.text,
        }
