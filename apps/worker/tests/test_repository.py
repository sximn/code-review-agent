import httpx
import pytest
from src.repository import (
    GitHubError,
    InvalidRepositoryHandle,
    PullRequestMetadata,
    _github_get,
    fetch_pr_metadata,
    parse_repository_handle,
    uriEncode,
)

parse_handle_testdata = [
    ("sximn/code-review-agent", ("sximn", "code-review-agent")),
    ("random/name.with-dots", ("random", "name.with-dots")),
]


@pytest.mark.parametrize("repository,expected", parse_handle_testdata)
def test_parse_repository_handle(repository: str, expected: tuple[str, str]):
    computed = parse_repository_handle(repository)

    assert computed == expected


@pytest.mark.parametrize(
    "repository",
    [
        "",
        "repository",
        "/repository",
        "owner/",
        "/",
        "owner/repository/extra",
        " owner/repository",
        "owner/repository ",
    ],
)
def test_parse_repository_handle_rejects_invalid_values(repository):
    with pytest.raises(InvalidRepositoryHandle):
        parse_repository_handle(repository)


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

    def handler(request: httpx.Request) -> httpx.Response:

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
            repository=REPO,
            pr_number=PR,
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
