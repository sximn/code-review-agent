# Development

This section describes how to run the whole stack in dev-mode
and outlines the differences that are applied during development and compared to how they are run in production.


differences:
  - container runtime
    - `runsc` is Linux-only container runtime, for development `runc` is used
    - configured as environment variable `SANDBOX_RUNTIME` in .env.example

  - OpenAI API calls 
    - 3 agent modes are implemented - `live`, `mock` & `simulation`
      - `live` - calls real OpenAI APIs (requires API token)
      - `mock` - skips the whole sandbox and worker setup and returns empty finding with approval
      - `simulation` - simulates whole end-to-end flow by using a fake-openai API service and returns based on configured `simulation scenario` 
        - configured as environment variable `SIMULATION_SCENARIO` in .env.example (requires `AGENT_MODE=simulation`)
        - scenarios selected by `SIMULATION_SCENARIO`:

            | Scenario | Behavior |
            | --- | --- |
            | `success` | Tool call, then approved review |
            | `findings` | Tool call, then one clearly synthetic finding |
            | `api-error` | HTTP 429 before any completion; usage unavailable |
            | `error-after-tool` | HTTP 429 after the tool response; retains partial usage/cost |
            | `invalid-output` | Invalid final JSON; retains usage/cost from both responses |
            | `missing-usage` | Final response omits usage; partial cost estimate |
            | `step-limit` | Repeated tool calls until `MAX_STEPS` is exhausted |

  - Sign Up (email + password)
    - in production only OAuth sign ups are supported (with github & google providers)
    - email + password is exposed during development for "low effort setup" purposes
    - enforced through environment variable `NODE_ENV` - when set to "development"
