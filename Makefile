DEV_ENV ?= .env
DEV = ENV_FILE=$(DEV_ENV) docker compose --env-file $(DEV_ENV) \
	-p code-review-agent-system-dev \
	-f docker-compose.yml -f docker-compose.dev.yml

.PHONY: ensure-dev-env dev dev-sandbox dev-down migrate prod-check

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
	fi; \
	dry_run=$$dry_run find ./apps/web -type f -name .env.example \
	  -exec sh -c ' \
	    for src do \
	      dst=$${src%.example}; \
	      if [ ! -e "$$dst" ]; then \
	        printf "\033[2mcp \"%s\" \"%s\"\033[0m\n" "$$src" "$$dst"; \
	        if [ "$$dry_run" = 1 ]; then \
	          printf "\033[0;38;5;240;49mWould copy \033[36m%s\033[0m to \033[32m%s\033[0m\n" "$$src" "$$dst"; \
	        else \
	          cp "$$src" "$$dst" || exit 1; \
	          printf "\033[0;38;5;240;49mCreated %s from %s\033[0m\n" "$$dst" "$$src"; \
	        fi; \
	      else \
	        printf "\033[0;38;5;240;49mUsing existing \033[36m%s\033[0m \033[0;38;5;240;49mfor nextjs app\033[0m\n" "$$dst"; \
	      fi; \
	    done \
	  ' sh {} +

dev dev-sandbox: ensure-dev-env

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
