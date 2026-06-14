.PHONY: test mypy

test:
	pytest tests

mypy:
	mypy .