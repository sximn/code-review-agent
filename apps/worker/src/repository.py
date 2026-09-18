import urllib.parse
from collections.abc import Mapping
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class ReviewRequestPayload(BaseModel):
    model_config = ConfigDict(
        strict=True,
        populate_by_name=True,
    )

    repository_handle: str
    repository_owner: str
    repository_name: str
    pull_request_number: int = Field(ge=1, validation_alias="pull_request")

    @model_validator(mode="before")
    @classmethod
    def parse_repository(cls, data: Any) -> Any:
        if not isinstance(data, Mapping):
            return data

        values = dict(data)
        repository_handle = values.pop("repository", None)

        if not isinstance(repository_handle, str):
            raise ValueError("repository must be a string")  # noqa: TRY004 - pydantic translates ValueError into ValidationError

        if "/" not in repository_handle:
            raise ValueError("Invalid repository handle.")

        parts = repository_handle.split("/")
        if len(parts) != 2 or not all(parts):
            raise ValueError(
                f"Invalid repository handle: {repository_handle!r}. Expected 'owner/name'."
            )

        owner, name = repository_handle.split("/")
        if owner != owner.strip() or name != name.strip():
            raise ValueError(
                f"Invalid repository handle {repository_handle!r}; expected 'owner/name'."
            )

        values.update(
            repository_handle=repository_handle,
            repository_owner=owner,
            repository_name=name,
        )
        return values


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


async def fetch_pr_metadata(
    github_client: httpx.AsyncClient,
    payload: ReviewRequestPayload,
    token: str | None = None,
) -> PullRequestMetadata:
    if token:
        await _validate_token(github_client, token)

    # check if the repository is visible to this request
    repo_url = f"{API_ROOT}/repos/{uriEncode(payload.repository_owner)}/{uriEncode(payload.repository_name)}"

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
    pr_url = f"{repo_url}/pulls/{payload.pull_request_number}"

    metadata_response = await _github_get(
        github_client,
        pr_url,
        token=token,
        accept="application/vnd.github+json",
        not_found_message=(
            f"Repository is {visibility}, but pull request #{payload.pull_request_number} does not exist."
        ),
    )

    diff_response = await _github_get(
        github_client,
        pr_url,
        token=token,
        accept="application/vnd.github.v3.diff",
        not_found_message=f"Pull request #{payload.pull_request_number} does not exist.",
    )
    metadata = metadata_response.json()

    try:
        return PullRequestMetadata(
            repository=payload.repository_handle,
            visibility=visibility,
            pr_number=payload.pull_request_number,
            title=metadata["title"],
            description=metadata["body"] or "",
            diff=diff_response.text,
            base_sha=metadata["base"]["sha"],
            head_sha=metadata["head"]["sha"],
        )
    except (TypeError, KeyError) as error:
        raise GitHubError("GitHub returned unexpected PR metadata.") from error
