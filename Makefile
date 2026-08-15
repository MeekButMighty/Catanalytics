.DEFAULT_GOAL:=start
.EXPORT_ALL_VARIABLES:
include ./.env

DOCKER_COMPOSE=/usr/bin/docker compose -f docker-compose.yml
DOCKER=/usr/bin/docker
INSTANCE=$(notdir $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST)))))


.PHONY: start stop multitail

start:
	$(DOCKER_COMPOSE) up -d

stop:
	$(DOCKER_COMPOSE) down

pull:
	$(DOCKER_COMPOSE) pull

restart: stop start

db:
	$(DOCKER) exec -it tns mysql -uroot -p$(MYSQL_ROOT_PW) -A

upgrade : pull stop start

log:
	multitail -o beep_method:popup                                        \
                  -cT ansi -l '$(DOCKER) logs -f --tail=50 catanalytics-dashboard'  \
                  -cT ansi -l '$(DOCKER) logs -f --tail=50 catanalytics-api'  \
                  -cT ansi -l '$(DOCKER) logs --tail=50 -f traefik'

err:
	multitail -o beep_method:popup                                        \
                  -cT ansi /docker/tns/logs/nginx_error.log 
logs:
	$(if $(SERVICE_NAME), $(info -- Tailing logs for $(SERVICE_NAME)), $(info -- Tailing all logs, SERVICE_NAME not set.))
	$(DOCKER_COMPOSE) logs -f $(SERVICE_NAME)
