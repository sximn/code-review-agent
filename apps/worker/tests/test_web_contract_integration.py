import os

import pytest
from src.review_state_client import ReviewStateClient, ReviewStateConfigurationError

REVIEW_ID = "22222222-2222-4222-8222-222222222222"


def contract_test_settings() -> tuple[str, str]:
    base_url = os.getenv("WEB_CONTRACT_TEST_URL")
    token = os.getenv("WEB_CONTRACT_TEST_TOKEN")
    if not base_url or not token:
        pytest.skip(
            "Set WEB_CONTRACT_TEST_URL and WEB_CONTRACT_TEST_TOKEN to run the "
            "live web contract test."
        )
    return base_url, token


@pytest.mark.integration
@pytest.mark.asyncio
async def test_review_state_client_matches_live_web_contract() -> None:
    base_url, token = contract_test_settings()

    async with ReviewStateClient(base_url, token) as client:
        assert await client.set_state(REVIEW_ID, "running") == "running"
        assert (
            await client.set_state(
                REVIEW_ID,
                "finished",
                result={"findings": [], "approval_granted": True},
            )
            == "finished"
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_review_state_client_authentication_matches_live_web_contract() -> None:
    base_url, _ = contract_test_settings()

    with pytest.raises(ReviewStateConfigurationError) as error:
        async with ReviewStateClient(base_url, "invalid-token", max_attempts=1) as client:
            await client.set_state(REVIEW_ID, "running")

    assert error.value.status_code == 401
