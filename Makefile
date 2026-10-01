DEV_ENV ?= .env
DEV_ENV_ABS_PATH = $(realpath $(DEV_ENV))
DEV = ENV_FILE=$(DEV_ENV) docker compose --env-file $(DEV_ENV) \
	-p code-review-agent-system-dev \
	-f docker-compose.yml -f docker-compose.dev.yml

.PHONY: ensure-dev-env dev dev-sandbox dev-down migrate prod-check contracts contracts-check

ensure-dev-env:
	+@set -eu; \
	case "$${MAKEFLAGS%% *}" in *n*) dry_run=1 ;; *) dry_run=0 ;; esac; \
	test -f .env.example || { echo "Missing .env.example" >&2; exit 1; }; \
	if [ ! -e "$(DEV_ENV)" ]; then \
	  printf '\033[2mcp ".env.example" "%s"\033[0m\n' "$(DEV_ENV)"; \
	  if [ "$$dry_run" = 1 ]; then \
	    printf '\033[0;38;5;240;49mWould copy \033[36m.env.example\033[0m to \033[32m%s\033[0m\n' "$(DEV_ENV)"; \
	  else \
	    cp .env.example "$(DEV_ENV)"; \
	    printf '\033[0;38;5;240;49mCreated %s from .env.example\033[0m\n' "$(DEV_ENV)"; \
	  fi; \
	else \
		printf "\033[0;38;5;240;49mUsing existing \033[36m%s\033[0m \033[0;38;5;240;49mfor compose stack\033[0m\n" "$(DEV_ENV)"; \
	fi;

dev dev-sandbox: ensure-dev-env

dev:
	$(DEV) up -d
	@$(DEV) watch --no-up worker & \
	  watch_pid=$$!; \
	  trap 'kill $$watch_pid 2>/dev/null || true' EXIT INT TERM; \
	  env_abs_path=$$(realpath "$(DEV_ENV)") && \
	  cd apps/web && \
	  printf 'ENV_ABS_PATH=%s\n' "$$env_abs_path" && \
	  pnpm exec dotenv -e "$$env_abs_path" -o -- pnpm run dev

dev-sandbox:
	$(DEV) --profile sandbox up --build --watch

dev-down:
	$(DEV) down

migrate:
	$(DEV) build migrate
	$(DEV) run --rm migrate

prod-check:
	docker compose -f compose.yaml config --quiet

contracts:
	cd apps/web && pnpm contracts:generate
	cd apps/sandbox-controller && uv run --no-sync python -m scripts.export_openapi ../../contracts/sandbox-controller.openapi.json
