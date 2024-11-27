all: test mypy black

PHONY: test
test:
	pytest

PHONY: coverage
coverage: bin/pytest
	pytest --cov src/ofxstatement

.PHONY: black
black:
	black --check src tests

.PHONY: mypy
mypy:
	mypy src tests

publish:
	rm -f dist/*
	python3 -m build
	python3 -m twine upload dist/* --verbose