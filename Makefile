.PHONY: check test lint format run

check: lint test
	@echo "Check completed"

test:
	@echo "No automated tests configured yet"
	@echo "Manual API checks are listed in AGENTS.md"

lint:
	@echo "No lint configured yet"

format:
	@echo "No formatter configured yet"

run:
	uvicorn app.main:app --reload