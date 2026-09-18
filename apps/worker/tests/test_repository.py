from typing import Any

import httpx
import pytest
from pydantic import ValidationError
from src.repository import (
    GitHubError,
    PullRequestMetadata,
    ReviewRequestPayload,
    _github_get,
    _validate_token,
    fetch_pr_metadata,
    uriEncode,
)

parse_handle_testdata = [
    (
        {"repository": "sximn/code-review-agent", "pull_request": 2},
        {
            "repository_handle": "sximn/code-review-agent",
            "pull_request_number": 2,
            "repository_owner": "sximn",
            "repository_name": "code-review-agent",
        },
    ),
    (
        {"repository": "random/name.with-dots", "pull_request": 42},
        {
            "repository_handle": "random/name.with-dots",
            "pull_request_number": 42,
            "repository_owner": "random",
            "repository_name": "name.with-dots",
        },
    ),
]


@pytest.mark.parametrize("raw_payload,expected", parse_handle_testdata)
def test_parse_review_request_payload_passes(
    raw_payload: dict[str, Any], expected: dict[str, Any]
):
    computed = ReviewRequestPayload.model_validate(raw_payload)
    computed.model_dump()
    assert computed.model_dump() == expected


@pytest.mark.parametrize(
    "raw_payload",
    [
        # invalid `repository` values
        {"repository": "", "pull_request": 2},
        {"repository": "repo", "pull_request": 2},
        {"repository": "/repository", "pull_request": 2},
        {"repository": "owner/", "pull_request": 2},
        {"repository": "/", "pull_request": 2},
        {"repository": "owner/repository/extra", "pull_request": 2},
        {"repository": " owner/repository", "pull_request": 2},
        {"repository": "owner/repository ", "pull_request": 2},
        # invalid `pull_request` values
        {"repository": "sximn/code-review-agent ", "pull_request": 0},
        {"repository": "sximn/code-review-agent ", "pull_request": ""},
        {"repository": "sximn/code-review-agent ", "pull_request": "2"},
        {"repository": "sximn/code-review-agent ", "pull_request": "blabla"},
    ],
)
def test_parse_review_request_payload_rejects_invalid_values(raw_payload):
    with pytest.raises(ValidationError):
        _ = ReviewRequestPayload.model_validate(raw_payload)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("hello-world", "hello-world"),
        ("hello world", "hello%20world"),
        ("owner/name", "owner%2Fname"),
        ("name@example", "name%40example"),
    ],
)
def test_uri_encode(value, expected):
    assert uriEncode(value) == expected


@pytest.mark.asyncio
async def test_validate_token_success():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, request=request)

    await _validate_token(
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)), token="token"
    )


@pytest.mark.parametrize(
    "status_code,error,error_match",
    [
        (401, GitHubError, "invalid"),
        (403, GitHubError, "rejected"),
        (400, httpx.HTTPStatusError, None),
    ],
)
@pytest.mark.asyncio
async def test_validate_token_raises_on_bad_status(status_code, error, error_match):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=status_code, request=request)

    with pytest.raises(error, match=error_match):
        await _validate_token(
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
            token="token",
        )


@pytest.mark.asyncio
async def test_github_get_translates_network_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection failed", request=request)

    transport = httpx.MockTransport(handler=handler)

    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(GitHubError, match="Could not reach GitHub"):
            await _github_get(
                client,
                "https://api.github.com/example",
                token=None,
                accept="application/vnd.github+json",
                not_found_message="Not found.",
            )


@pytest.mark.asyncio
async def test_fetch_pr_metadata():
    REPO = "sximn/code-review-agent"
    PR = 2

    requests_called: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests_called.append(request)

        if request.url.path == f"/repos/{REPO}":
            return httpx.Response(status_code=200, json={"private": False})

        if request.url.path == f"/repos/{REPO}/pulls/{PR}":
            accept = request.headers["Accept"]

            if accept == "application/vnd.github+json":
                return httpx.Response(
                    status_code=200,
                    json={
                        "title": "Cool change",
                        "body": None,
                        "base": {"sha": "base123"},
                        "head": {"sha": "head456"},
                    },
                )

            if accept == "application/vnd.github.v3.diff":
                return httpx.Response(
                    200,
                    text="diff --git a/README.md b/README.md",
                )

        raise AssertionError(
            f"Unexpected request: {request.method} {request.url} | path: {request.url.path}"
        )

    transport = httpx.MockTransport(handler=handler)

    async with httpx.AsyncClient(transport=transport) as client:
        result = await fetch_pr_metadata(
            client,
            payload=ReviewRequestPayload.model_validate(
                {"repository": REPO, "pull_request": PR}
            ),
        )

    assert result == PullRequestMetadata(
        repository=REPO,
        pr_number=PR,
        visibility="public",
        title="Cool change",
        description="",
        diff="diff --git a/README.md b/README.md",
        base_sha="base123",
        head_sha="head456",
    )

    assert len(requests_called) == 3
