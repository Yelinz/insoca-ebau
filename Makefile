SHELL:=/bin/sh

# http://clarkgrubb.com/makefile-style-guide#phony-targets

.DEFAULT_GOAL := help

GIT_USER=$(shell git config user.email)

define set_env
	sed 's/^\(APPLICATION=\).*$//\1$(1)/' -i .env django/.env
endef

.PHONY: help
help: ## Show the help messages
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort -k 1,1 | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'


.PHONY: js
js:
	npm run build --prefix ./php/public


.PHONY: js-watch
js-watch:
	npm run watch --prefix ./kt_uri/configuration/public


.PHONY: css
css: ## Create the css files from the sass files
	@cd camac/configuration/public/css/; make css


.PHONY: css-watch
css-watch: ## Watch the sass files and create the css when they change
	@cd camac/configuration/public/css/; make watch


.PHONY: install-api-doc
install-api-doc: ## installs the api doc generator tool
	npm i -g apidoc


.PHONY: generate-api-doc
generate-api-doc: ## generates documentation for the i-web portal API
	apidoc -i kt_uri/configuration/Custom/modules/portal/controllers/ -o doc/
	@echo "Documentation was saved in /doc folder."

.PHONY: clear-cache
clear-cache: ## Clear the memcache
	@docker-compose exec php php -d xdebug.remote_enable=off /var/www/camac/cronjob/clear-cache.php

.PHONY: dumpconfig
dumpconfig: ## Dump the current camac and caluma configuration
	docker-compose exec django python manage.py dumpconfig

.PHONY: dumpdata
dumpdata: ## Dump the current camac and caluma data
	docker-compose exec django /app/manage.py dumpcamacdata

.PHONY: loadconfig-camac
loadconfig-camac: ## Load the camac configuration
	@docker-compose exec django ./wait-for-it.sh -t 300 0.0.0.0:80 -- python manage.py loadconfig --user $(GIT_USER)

.PHONY: loadconfig-dms
loadconfig-dms: ## Load the DMS configuration
	@docker-compose exec document-merge-service python manage.py loaddata /tmp/document-merge-service/dump.json

.PHONY: loadconfig
loadconfig: loadconfig-camac loadconfig-dms ## Load the DMS and camac configuration

.PHONY: dbshell
dbshell: ## Start a psql shell
	@docker-compose exec db psql -Ucamac


######### Changes from eBau Bern #########

.PHONY: mergeconfig
mergeconfig: ## Merge config.json
	git mergetool --tool=jsondiff

.PHONY: migrate
migrate:  ## Migrate schema
	docker-compose exec django /app/manage.py migrate
	make sequencenamespace

.PHONY: grunt-build-be
grunt-build-be: ## Grunt build
	docker-compose exec php sh -c "cd ../camac/public && npm run build-be"

.PHONY: grunt-watch-be
grunt-watch-be: ## Grunt watch
	docker-compose exec php sh -c "cd ../camac/public && npm run build-be && npm run watch-be"

.PHONY: grunt-build-sz
grunt-build-sz: ## Grunt build
	docker-compose exec php sh -c "cd ../camac/public && npm run build-sz"

.PHONY: grunt-watch-sz
grunt-watch-sz: ## Grunt watch
	docker-compose exec php sh -c "cd ../camac/public && npm run build-sz && npm run watch-sz"

.PHONY: format
format:
	@yarn --cwd=php install
	@yarn --cwd=php lint --fix
	@yarn --cwd=php prettier-format
	@yarn --cwd=ember-caluma-portal install
	@yarn --cwd=ember-caluma-portal lint:js --fix
	@yarn --cwd=ember install
	@yarn --cwd=ember lint:js --fix
	@black django
	@prettier --write *.yml

.PHONY: makemigrations
makemigrations: ## Create schema migrations
	docker-compose exec django /app/manage.py makemigrations

.PHONY: flush
flush:
	@docker-compose exec django /app/manage.py flush --no-input

# Directory for DB snapshots
.PHONY: _db_snapshots_dir
_db_snapshots_dir:
	@mkdir -p db_snapshots

.PHONY: db_snapshot
db_snapshot: _db_snapshots_dir  ## Make a snapshot of the current state of the database
	@docker-compose exec db  pg_dump -Ucamac -c > db_snapshots/$(shell date -Iseconds).sql

.PHONY: db_restore
db_restore:  _db_snapshots_dir ## Restore latest DB snapshot created with `make db_snapshot`
	@echo "restoring from $(SNAPSHOT)"
	@docker-compose exec -T db psql -Ucamac < $(SNAPSHOT) > /dev/null

.PHONY: sequencenamespace
sequencenamespace:  ## Set the Sequence namespace for a given user. GIT_USER is detected from your git repository.
	@docker-compose exec django make sequencenamespace GIT_USER=$(GIT_USER)

.PHONY: log
log: ## Show logs of web container
	@docker-compose logs --follow php

.PHONY: test
test: ## Run backend tests
	@docker-compose exec django make test

.PHONY: kt_uri
kt_uri: ## Set APPLICATION to kt_uri
	$(call set_env,kt_uri)

.PHONY: kt_schwyz
kt_schwyz: ## Set APPLICATION to kt_uri
	$(call set_env,kt_schwyz)

.PHONY: kt_bern
kt_bern: ## Set APPLICATION to kt_uri
	$(call set_env,kt_bern)

.PHONY: demo
demo: ## Set APPLICATION to kt_uri
	$(call set_env,demo)

.PHONY: clean
clean: ## Remove temporary files / build artefacts etc
	@find . -name node_modules -type d | xargs rm -rf
	@rm -rf ./ember/dist ./ember-caluma-portal/dist ./php/kt_uri/public/js/dist ./php/kt_schwyz/public/js/dist
	@rm -rf ./ember/tmp ./ember-caluma-portal/tmp
	@rm -rf ./ember/build ./ember-caluma-portal/build

.PHONY: release
release: ## Draft a new release
	@if [ -z $(version) ]; then echo "Please pass a version: make release version=x.x.x"; exit 1; fi
	@echo $(version) > VERSION.txt
	@sed -i -e 's/"version": ".*",/"version": "$(version)",/g' ember-caluma-portal/package.json
	@sed -i -e 's/appVersion = ".*"/appVersion = "$(version)"/g' php/kt_bern/configs/application.ini

.PHONY: release-folder
release-folder: ## Add a template for a release folder
	@if [ -z $(version) ]; then echo "Please pass a version: make release-folder version=x.x.x"; exit 1; fi
	@mkdir -p "releases/$(version)"
	@echo "# Neu\n-\n# Korrekturen\n-" >> "releases/$(version)/CHANGELOG.md"
	@echo "# Änderungen\n# Ansible (Rolle / Variablen)\n-\n# Keycloak\n-\n# DB\n-\n# Apache" >> "releases/$(version)/MANUAL.md"
	@prettier --loglevel=silent --write "releases/$(version)/*.md"

clear-silk:
	@docker-compose exec django python manage.py silk_clear_request_log
