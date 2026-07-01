.PHONY: help up down restart ps logs logs-api logs-n8n build rebuild backup health cert-renew db redis-cli clean prereqs

.COMPILER: docker compose

COMPOSE_FILE := $(shell find .. -name docker-compose.yml -maxdepth 2 2>/dev/null | head -1)
ifeq ($(COMPOSE_FILE),)
  COMPOSE_FILE := ../docker-compose.yml
endif

export COMPOSE_FILE

GREEN  := $(shell tput setaf 2 2>/dev/null || echo '')
RED    := $(shell tput setaf 1 2>/dev/null || echo '')
YELLOW := $(shell tput setaf 3 2>/dev/null || echo '')
RESET  := $(shell tput sgr0 2>/dev/null || echo '')

info  = @echo "$(GREEN)[INFO]$(RESET) $(1)"
warn  = @echo "$(YELLOW)[WARN]$(RESET) $(1)"
err   = @echo "$(RED)[ERR]$(RESET)  $(1)"

.DEFAULT_GOAL := help

help:
	@grep -E '^## ' Makefile | sed 's/## /  /'

up:
	$(call info,"Starting all services...")
	docker compose -f $(COMPOSE_FILE) up -d

down:
	$(call info,"Stopping all services...")
	docker compose -f $(COMPOSE_FILE) down

restart: down up

ps:
	docker compose -f $(COMPOSE_FILE) ps

logs:
	docker compose -f $(COMPOSE_FILE) logs -f --tail=100

logs-%:
	docker compose -f $(COMPOSE_FILE) logs -f --tail=100 "$(subst logs-,,$(MAKECMDGOALS))"

build:
	$(call info,"Building API image...")
	docker compose -f $(COMPOSE_FILE) build api

rebuild:
	$(call warn,"Full rebuild — no cache...")
	docker compose -f $(COMPOSE_FILE) down
	docker compose -f $(COMPOSE_FILE) build --no-cache api
	docker compose -f $(COMPOSE_FILE) up -d

backup:
	chmod +x $(dir $(COMPOSE_FILE))/scripts/backup.sh
	$(dir $(COMPOSE_FILE))/scripts/backup.sh

health:
	chmod +x $(dir $(COMPOSE_FILE))/scripts/healthcheck.sh
	$(dir $(COMPOSE_FILE))/scripts/healthcheck.sh

cert-renew:
	$(call info,"Renewing SSL certificates...")
	docker compose -f $(COMPOSE_FILE) run --rm certbot renew
	docker compose -f $(COMPOSE_FILE) exec nginx nginx -s reload

db:
	docker compose -f $(COMPOSE_FILE) exec postgres psql -U bunche -d bunche

redis-cli:
	docker compose -f $(COMPOSE_FILE) exec redis redis-cli -a "$$REDIS_PASSWORD"

clean:
	$(call warn,"This removes ALL data volumes...")
	@read -p "Continue? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 0
	docker compose -f $(COMPOSE_FILE) down -v --remove-orphans
	docker image prune -f

prereqs:
	@which docker >/dev/null 2>&1 || { $(call err,"docker not found"); exit 1; }
	@which docker compose >/dev/null 2>&1 || { $(call err,"docker compose not found"); exit 1; }
	$(call info,"All prerequisites met.")
