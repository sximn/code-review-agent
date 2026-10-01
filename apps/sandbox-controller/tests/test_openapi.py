from typing import Any

from src.main import app


def test_openapi_describes_internal_authentication_and_responses() -> None:
    spec: dict[str, Any] = app.openapi()

    assert spec["info"] == {
        "title": "Sandbox Controller API",
        "version": "1.0.0",
        "description": "Internal API used by the review worker to manage sandboxes.",
    }
    assert spec["components"]["securitySchemes"] == {
        "sandboxControllerToken": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Sandbox-Controller-Token",
        }
    }
    assert spec["paths"]["/sandboxes"]["post"]["security"] == [
        {"sandboxControllerToken": []}
    ]
    destroy_responses = spec["paths"]["/sandboxes/{sandbox_id}"]["delete"]["responses"]
    assert destroy_responses["204"] == {"description": "Successful Response"}
    assert "200" not in destroy_responses
