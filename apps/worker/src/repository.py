import urllib.parse
from typing import Literal

import httpx
from pydantic import BaseModel


class GitHubError(Exception):
    pass


class InvalidRepositoryHandle(Exception):
    pass


class PullRequestMetadata(BaseModel):
    repository: str
    visibility: Literal["private", "public"]
    pr_number: int
    title: str
    description: str
    diff: str
    base_sha: str
    head_sha: str


API_ROOT = "https://api.github.com"


def _github_headers(token: str | None, accept: str) -> dict[str, str]:
    headers = {
        "Accept": accept,
        "X-GitHub-Api-Version": "2026-03-10",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    return headers


async def _validate_token(client: httpx.AsyncClient, token: str) -> None:
    response = await client.get(
        f"{API_ROOT}/user",
        headers=_github_headers(token, "application/vnd.github+json"),
    )

    if response.status_code == 401:
        raise GitHubError("The GITHUB_TOKEN is invalid or expired.")

    if response.status_code == 403:
        raise GitHubError(
            "The GITHUB_TOKEN was rejected or GitHub rate limits were exceeded."
        )

    response.raise_for_status()


async def _github_get(
    client: httpx.AsyncClient,
    url: str,
    *,
    token: str | None,
    accept: str,
    not_found_message: str,
) -> httpx.Response:
    try:
        response = await client.get(
            url,
            headers=_github_headers(token, accept),
        )
    except httpx.RequestError as error:
        raise GitHubError(f"Could not reach GitHub: {error}") from error

    if response.status_code == 401:
        raise GitHubError("GITHUB_TOKEN is invalid or expired.")

    if response.status_code == 403:
        raise GitHubError(
            "GitHub denied the request. Check token permissions and rate limits."
        )

    if response.status_code == 404:
        raise GitHubError(not_found_message)

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise GitHubError(f"GitHub returned HTTP {response.status_code}.") from error

    return response


def uriEncode(part: str) -> str:
    return urllib.parse.quote(part, safe="~()*!.'-")


def parse_repository_handle(repository: str) -> tuple[str, str]:
    if "/" not in repository:
        raise InvalidRepositoryHandle("Invalid repository handle.")

    parts = repository.split("/")
    if len(parts) != 2 or not all(parts):
        raise InvalidRepositoryHandle(
            f"Invalid repository handle: {repository!r}. Expected 'owner/name'."
        )

    owner, name = repository.split("/")
    if owner != owner.strip() or name != name.strip():
        raise InvalidRepositoryHandle(
            f"Invalid repository handle {repository!r}; expected 'owner/name'."
        )
    return owner, name


async def fetch_pr_metadata(
    github_client: httpx.AsyncClient,
    repository: str,
    pr_number: int,
    token: str | None = None,
) -> PullRequestMetadata:

    owner, name = parse_repository_handle(repository)

    if pr_number <= 0:
        raise ValueError("Pull request number must be positive.")

    if token:
        await _validate_token(github_client, token)

    # check if the repository is visible to this request
    repo_url = f"{API_ROOT}/repos/{uriEncode(owner)}/{uriEncode(name)}"

    repo_response = await _github_get(
        github_client,
        repo_url,
        token=token,
        accept="application/vnd.github+json",
        not_found_message=(
            "The repository does not exist or is not accessible with this token."
            if token
            else "The repository does not exist or requires authentication."
        ),
    )

    repo_data = repo_response.json()
    visibility = "private" if repo_data["private"] else "public"

    # fetch PR metadata: title + description
    pr_url = f"{repo_url}/pulls/{pr_number}"

    metadata_response = await _github_get(
        github_client,
        pr_url,
        token=token,
        accept="application/vnd.github+json",
        not_found_message=(
            f"Repository is {visibility}, but pull request #{pr_number} does not exist."
        ),
    )

    diff_response = await _github_get(
        github_client,
        pr_url,
        token=token,
        accept="application/vnd.github.v3.diff",
        not_found_message=f"Pull request #{pr_number} does not exist.",
    )
    metadata = metadata_response.json()

    try:
        return PullRequestMetadata(
            repository=repository,
            visibility=visibility,
            pr_number=pr_number,
            title=metadata["title"],
            description=metadata["body"] or "",
            diff=diff_response.text,
            base_sha=metadata["base"]["sha"],
            head_sha=metadata["head"]["sha"],
        )
    except (TypeError, KeyError) as error:
        raise GitHubError("GitHub returned unexpected PR metadata.") from error
