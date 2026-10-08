from http.server import ThreadingHTTPServer
from threading import Thread

import pytest
from src.agent.fake_openai import Handler


@pytest.fixture(scope="module")
def fake_openai_url():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario,status,requests,cost_status,partial",
    [
        ("success", "finished", 2, "estimated", False),
        ("findings", "finished", 2, "estimated", False),
        ("api-error", "failed", 0, "usage-unavailable", True),
        ("error-after-tool", "failed", 1, "estimated", True),
        ("invalid-output", "failed", 2, "estimated", True),
        ("missing-usage", "finished", 2, "estimated", True),
        ("step-limit", "failed", 3, "estimated", True),
    ],
)
async def test_simulation_lifecycle(
    review_execution,
    fake_openai_url,
    scenario,
    status,
    requests,
    cost_status,
    partial,
):
    execution = review_execution
    execution.config.agent_mode = "simulation"
    execution.config.simulation_base_url = fake_openai_url
    execution.config.simulation_scenario = scenario
    execution.config.model = "gpt-4o-mini"
    execution.config.max_steps = 3
    execution.config.job_timeout_seconds = 10

    async with execution.executor.open("simulation-job") as session:
        completion = await session.run(execution.payload)

    assert completion.status == status
    assert completion.usage["request_count"] == requests
    assert completion.cost["status"] == cost_status
    assert completion.cost["partial"] is partial
    execution.sandbox.create.assert_awaited_once()
    execution.sandbox.destroy.assert_awaited_once_with("sandbox-1")
    execution.sandbox.close.assert_awaited_once()
    tool_calls = [
        call
        for call in execution.sandbox.exec.await_args_list
        if call.args[1] == ["git", "status", "--short"]
    ]
    assert len(tool_calls) == (
        0 if scenario == "api-error" else 3 if scenario == "step-limit" else 1
    )
    if scenario == "success":
        assert completion.usage["input_tokens"] == 2000
        assert completion.usage["cached_input_tokens"] == 400
        assert completion.usage["output_tokens"] == 200
        assert completion.usage["reasoning_tokens"] == 40
        assert completion.cost["estimated_usd"] == "0.000390000000"
    if scenario == "findings":
        assert completion.result["approval_granted"] is False
        assert len(completion.result["findings"]) == 1
    if scenario == "missing-usage":
        assert completion.usage["responses_without_usage"] == 1


@pytest.mark.asyncio
async def test_simulation_rejects_external_provider(review_execution):
    execution = review_execution
    execution.config.agent_mode = "simulation"
    execution.config.simulation_base_url = "https://api.openai.com/v1"
    async with execution.executor.open("simulation-job") as session:
        completion = await session.run(execution.payload)
    assert completion.status == "failed"
    assert "local fake OpenAI URL" in completion.error
