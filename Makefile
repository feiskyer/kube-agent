# make run ARGS='execute "find all kube-dns pods"'

.PHONY: run
run:
	poetry run kube-agent $(ARGS)

.PHONY: build
build:
	poetry build

.PHONY: install
install: build
	pip install --force-reinstall --no-deps dist/$(shell ls -t dist | head -n 1)

.PHONY: release
release: build
	poetry publish
	# gh release create v$(shell poetry version -s)

.PHONY: update
update:
	poetry up
	poetry update

.PHONY: clean
clean:
	rm -rf dist

.PHONY: install-dev
install-dev:
	poetry install

.PHONY: install-poetry
install-poetry:
	# curl -sSL https://install.python-poetry.org | python3 -
	# brew install pipx && pipx ensurepath
	pipx install poetry
	poetry self add poetry-plugin-up
