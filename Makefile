DEV_ENV ?= .env
DEV = ENV_FILE=$(DEV_ENV) docker compose --env-file $(DEV_ENV) \
	-p code-review-agent-system-dev \
	-f docker-compose.yml -f docker-compose.dev.yml

.PHONY: dev dev-sandbox dev-down migrate prod-check

dev:
	$(DEV) up -d --build
	@$(DEV) watch --no-up worker & \
	  watch_pid=$$!; \
	  trap 'kill $$watch_pid 2>/dev/null || true' EXIT INT TERM; \
	  cd apps/web && pnpm run dev

dev-sandbox:
	$(DEV) --profile sandbox up --build --watch

dev-down:
	$(DEV) down

migrate:
	$(DEV) build migrate
	$(DEV) run --rm migrate

prod-check:
	docker compose -f compose.yaml config --quiet
