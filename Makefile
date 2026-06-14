.PHONY: test mypy docker-dev

test:
	pytest tests

mypy:
	mypy . --check-untyped-defs

ruff:
	ruff check .

ruff-format:
	ruff format .

docker-dev:
	@test -f docker/.env || (echo "Error: File 'docker/.env' does not exist" && exit 1)
	BUILDKIT_PROGRESS=plain	\
		docker compose -f docker/dev.docker-compose.yaml \
					   up \
					   --build \
					   --abort-on-container-failure
