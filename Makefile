PYTHON ?= python

.PHONY: setup test demo validate release-check

setup:
	$(PYTHON) -m pip install -r requirements-dev.txt

test:
	$(PYTHON) -m pytest -q tests/public_release

demo:
	$(PYTHON) scripts/run_demo.py

validate:
	$(PYTHON) scripts/validate_environment.py

release-check:
	$(PYTHON) scripts/run_public_quality_gate.py --root . --output public_release/PUBLIC_RELEASE_QUALITY_GATE.json
