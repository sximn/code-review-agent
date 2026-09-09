from openai import OpenAI
from pydantic.dataclasses import dataclass

from env import environment


@dataclass
class PRMetadata:
    title: str
    description: str
    diff: str


@dataclass
class Finding:
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


@dataclass
class Review:
    pr_metadata: PRMetadata
    changed_files: list[dict]

    quality_findings: list[Finding]
    performance_findings: list[Finding]
    security_findings: list[Finding]

    approval_granted: bool


client = OpenAI(api_key=environment.openai_api_key)

SYSTEM_PROMPT = """You are a code-review agent.
You are given details of a PR - title, description and the code diff.
You review and verify the change.
Focus on:
  1. functionaity - it works as intended (given the PR title & description) and whether it doesn't break anything else given the context.
  2. performance - it is performant
  3. security - it does not expose what is not inteded and is secure

Return back a JSON output - nothing else, just the JSON.
The JSON should follow Python class hierarchy:
```python
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
    pr_metadata: dict
    changed_files: list[dict]

    quality_findings: list[Finding]
    performance_findings: list[Finding]
    security_findings: list[Finding]

    approval_granted: bool
```
"""


def run_agent_review(pr_metadata: PRMetadata):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
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
    response = client.chat.completions.create(
        model=environment.model,
        messages=messages,
    )
    review = response.choices[0].message.content
    messages.append(review)

    return review
