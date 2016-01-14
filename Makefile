SHELL:=/bin/bash

.PHONY: docs help up reset-db init-db watch fancy-up

fancy-up:
	tmux new-session -n 'camac runner' -d 'make up'
	tmux split-window -v 'make watch'
	tmux split-window -v 'tail -f camac/logs/application.log'
	tmux -2 attach-session -d

reset-db:
	docker cp docker/db docker_db_1:/usr/local/src
	docker exec -it docker_db_1 chmod +x /usr/local/src/db/drop_user.sh
	docker exec -it docker_db_1 /usr/local/src/db/drop_user.sh
	#make init-db

init-db:
	docker cp docker/db docker_db_1:/usr/local/src/
	docker exec -it docker_db_1 chmod +x /usr/local/src/db/init_db.sh
	docker exec -it docker_db_1 /usr/local/src/db/init_db.sh

up:
	docker-compose -f docker/docker-compose.yml up

init: up init-db
	docker exec -it docker_front_1 chown -R www-data /var/www/html/logs /var/www/html/cache

css:
	@cd camac/configuration/public/css/; make css

watch:
	@cd camac/configuration/public/css/; make watch

log:
	echo "TODO"
	exit 3 
	tmux new-session -n camac-log -d 'tail -f camac/logs/application.log'
	tmux split-window -v 'vagrant ssh -c "sudo tail -f /var/log/apache2/vagrant-error.log"'
	tmux -2 attach-session -d
