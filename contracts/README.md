# Internal API contracts

The OpenAPI documents in this directory are generated.
They serve as contracts for the HTTP boundaries between the worker and the services it calls.

After changing an API contract regenerate them by running:
```bash
make contracts
```

To check whether the current contracts are up to date run:
```bash
make contracts-check
```

CI runs `make contracts-check` and fails if a committed contract is stale.


The services publish their own contracts:

- `web.openapi.json` is generated from the web's oRPC contract
- `sandbox-controller.openapi.json` is generated from the sandbox-controller's FastAPI application.

__Do not edit the JSON files by hand.__
