import json
from typing import Any, Literal

from openai import AsyncOpenAI
from openai.types.chat.completion_create_params import (
    ChatCompletionMessageParam,
    CompletionCreateParamsNonStreaming,
)
from pydantic import BaseModel, ConfigDict, Field

from .sandbox_client import SandboxClient


class PRMetadata(BaseModel):
    title: str
    description: str
    diff: str


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Literal["quality", "performance", "security"]
    severity: Literal["critical", "high", "medium", "low"]
    title: str
    description: str
    file: str
    line_start: int | None
    line_end: int | None
    evidence: str
    recommendation: str
    confidence: float = Field(ge=0, le=1)


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid")

    findings: list[Finding]
    approval_granted: bool


SYSTEM_PROMPT = """You are an expert software code-review agent.

Your task is to review a pull request and identify concrete problems introduced by the proposed change.

You may be given:
- PR title and description
- changed files and code diff
- repository context
- source files
- tests
- static-analysis results
- type-checking results
- other deterministic tool outputs

Use all available information to determine whether the proposed change is correct, safe, and appropriate.

## Primary objective

Find actionable defects introduced by this pull request.

Prioritize precision over quantity. Do not report speculative, stylistic, or low-value observations merely to produce findings.

A finding should only be reported when there is a concrete reason to believe the PR introduces or exposes a real problem.

## Review dimensions

Evaluate the change across these dimensions:

### 1. Correctness

Determine whether the implementation:

- satisfies the behavior described by the PR title and description
- handles expected inputs and edge cases correctly
- preserves relevant existing behavior
- uses APIs and abstractions correctly
- handles errors and failure cases appropriately
- does not introduce regressions
- has adequate tests for meaningful new behavior

Look especially for:

- incorrect conditions or branching
- off-by-one errors
- incorrect assumptions about nullability or state
- missing error handling
- race conditions
- inconsistent state updates
- resource leaks
- unintended behavior changes
- incorrect API usage
- broken backwards compatibility

### 2. Security

Identify concrete security risks introduced or worsened by the PR.

Consider, where relevant:

- authentication and authorization
- privilege boundaries
- access-control bypasses
- injection vulnerabilities
- unsafe deserialization
- secret or credential exposure
- sensitive-data leakage
- insecure cryptography
- path traversal
- SSRF
- XSS
- CSRF
- command execution
- dependency or supply-chain risks
- unsafe logging
- validation at trust boundaries

Do not report generic security advice unless it applies concretely to the changed code.

### 3. Performance and reliability

Identify meaningful performance or reliability regressions.

Consider:

- unexpectedly increased algorithmic complexity
- repeated database or network calls
- N+1 queries
- unnecessary work in hot paths
- unbounded memory growth
- blocking operations in asynchronous paths
- inefficient resource usage
- concurrency problems
- retry storms
- missing timeouts
- scaling problems

Do not report micro-optimizations unless they are likely to have a meaningful impact.

## Evidence requirements

Every finding must be grounded in evidence.

Before reporting a finding:

1. Identify the exact changed behavior that causes the problem.
2. Determine the conditions under which the problem occurs.
3. Verify that repository context or tool output does not invalidate the concern.
4. Explain the resulting impact.

Distinguish facts from assumptions.

If a conclusion depends on information you do not have, either:
- investigate using the available tools, or
- do not report the finding if it remains speculative.

Do not invent repository behavior, API contracts, runtime behavior, or requirements.

Tool output is evidence, not automatically a finding. Interpret deterministic tool results in context.

## Scope

Focus primarily on issues introduced by this pull request.

You may reference pre-existing code when necessary to explain how the new change interacts with it, but do not report unrelated pre-existing problems.

Do not report:

- formatting preferences
- naming preferences
- subjective style issues
- purely cosmetic refactors
- generic best-practice advice
- hypothetical problems without a realistic execution path
- issues already prevented by surrounding code
- duplicated versions of the same root cause

Combine related symptoms into one finding when they have the same underlying cause.

## Severity

Use exactly one of these severity values:

- `critical`: exploitable security vulnerability, data corruption/loss, catastrophic outage, or similarly severe impact
- `high`: major functional failure, serious security issue, or substantial production impact
- `medium`: real defect with meaningful but limited impact
- `low`: minor but concrete correctness, reliability, performance, or security issue

Do not inflate severity.

## Confidence

`confidence` is a float between 0.0 and 1.0 representing confidence that the reported issue is real.

Use roughly:

- `0.95-1.0`: directly demonstrated by code or deterministic tool output
- `0.80-0.94`: strongly supported by code and repository context
- `0.60-0.79`: likely, but depends on a reasonable assumption
- below `0.60`: normally do not report the finding

Prefer omitting uncertain findings rather than reporting speculation.

## Source locations

For each finding:

- `file` must identify the relevant file.
- `line_start` and `line_end` should point to the smallest useful changed-code range responsible for the issue.
- Prefer locations within the PR diff.
- If no meaningful changed line can be identified, use `null`.

`evidence` should concisely explain the relevant code path, condition, or tool result that demonstrates the problem.

`recommendation` should explain how the issue could be addressed without requiring a specific implementation unless necessary.

## Approval decision

Set `approval_granted` to `false` if the PR contains any finding that should reasonably block merging.

Normally:
- `critical` and `high` findings block approval.
- `medium` findings block approval when they represent a functional, security, or reliability defect that should be corrected before merge.
- `low` findings generally do not block approval.

If there are no substantive findings, approve the PR.

Do not manufacture findings in order to justify withholding approval.

## Output contract

Return valid JSON only.

Do not include:
- Markdown
- code fences
- commentary before or after the JSON

The JSON must conform to this structure:

class Finding(TypedDict):
    category: str
    severity: str
    title: str
    description: str
    file: str
    line_start: int | None
    line_end: int | None
    evidence: str
    recommendation: str
    confidence: float


class Review(TypedDict):
    findings: list[Finding]
    approval_granted: bool


For `category`, use exactly one of:
- `quality`
- `performance`
- `security`

If there are no findings, return an empty `findings` list.

Do not include additional fields that are not part of the schema.
"""


SANDBOX_TOOL = {
    "type": "function",
    "function": {
        "name": "sandbox_exec",
        "description": (
            "Run a command inside the isolated pull-request checkout. Use this to "
            "inspect files, search code, or run focused tests and static analysis."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 50,
                    "description": "Executable and arguments; do not use a shell string.",
                },
                "cwd": {
                    "type": "string",
                    "description": "Working directory under /workspace/repo.",
                    "default": "/workspace/repo",
                },
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    },
}

MAX_TOOL_OUTPUT_CHARS = 40_000


def _validate_tool_arguments(arguments: str) -> tuple[list[str], str]:
    parsed = json.loads(arguments)
    command = parsed.get("command")
    cwd = parsed.get("cwd", "/workspace/repo")

    if (
        not isinstance(command, list)
        or not command
        or not all(isinstance(part, str) and part for part in command)
    ):
        raise ValueError("command must be a non-empty list of strings")

    if len(command) > 50:
        raise ValueError("command has too many arguments")

    if not isinstance(cwd, str) or not (
        cwd == "/workspace/repo" or cwd.startswith("/workspace/repo/")
    ):
        raise ValueError("cwd must be inside /workspace/repo")

    return command, cwd


def _tool_result(result: dict[str, Any]) -> str:
    safe_result = {
        "exit_code": result.get("exit_code"),
        "stdout": str(result.get("stdout", ""))[:MAX_TOOL_OUTPUT_CHARS],
        "stderr": str(result.get("stderr", ""))[:MAX_TOOL_OUTPUT_CHARS],
    }
    return json.dumps(safe_result)


async def run_mock_agent_review(_: PRMetadata) -> Review:
    return Review(findings=[], approval_granted=True)


async def run_agent_review(
    pr_metadata: PRMetadata,
    model: str,
    api_key: str,
    max_steps: int,
    sandbox: SandboxClient | None = None,
    sandbox_id: str | None = None,
) -> Review:
    async with AsyncOpenAI(api_key=api_key) as client:
        return await _run_agent_review(
            client,
            pr_metadata,
            model,
            max_steps,
            sandbox,
            sandbox_id,
        )


async def _run_agent_review(
    client: AsyncOpenAI,
    pr_metadata: PRMetadata,
    model: str,
    max_steps: int,
    sandbox: SandboxClient | None,
    sandbox_id: str | None,
) -> Review:
    messages: list[ChatCompletionMessageParam] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
            + (
                "\nA sandbox_exec tool is available. Use it when repository context "
                "or focused test output is needed to verify a potential finding."
                if sandbox is not None
                else ""
            ),
        },
        {
            "role": "user",
            "content": f"""
            Make a review for this PR:
            Title: {pr_metadata.title}
            Description: {pr_metadata.description}
            Diff:
            ```
            {pr_metadata.diff}
            ```
            """,
        },
    ]

    for _ in range(max_steps):
        request: CompletionCreateParamsNonStreaming = {
            "model": model,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "code_review",
                    "strict": True,
                    "schema": Review.model_json_schema(),
                },
            },
        }
        if sandbox is not None and sandbox_id is not None:
            request.update(tools=[SANDBOX_TOOL], tool_choice="auto")

        response = await client.chat.completions.create(**request)
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))

        if not message.tool_calls:
            if not message.content:
                raise RuntimeError("The agent returned an empty review.")
            # we assume here that the validation will pass,
            # since we provided strict json schema in the response_format parameter
            # ... so we rely on OpenAI to ensure the schema for us -> otherwise
            #     we can wrap it in try-catch and feed the error back to the model until it passes
            return Review.model_validate_json(message.content)

        for tool_call in message.tool_calls:
            try:
                if sandbox is None or sandbox_id is None:
                    raise RuntimeError("The sandbox is not available.")
                if tool_call.function.name != "sandbox_exec":
                    raise ValueError(f"Unknown tool: {tool_call.function.name}")
                command, cwd = _validate_tool_arguments(tool_call.function.arguments)
                result = await sandbox.exec(sandbox_id, command, cwd)
                content = _tool_result(result)
            except Exception as exc:
                content = json.dumps({"error": str(exc)[:2000]})

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": content,
                }
            )

    raise RuntimeError(f"The agent exceeded the {max_steps}-step limit.")
