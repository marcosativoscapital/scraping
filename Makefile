.PHONY: install setup run server test clean lint format

install:
	pip install -r requirements.txt
	playwright install chromium

setup: install
	cp -n .env.example .env || true
	@echo "→ Edite .env e adicione ANTHROPIC_API_KEY"

run:
	python -m src.main --vertical all

run-betting:
	python -m src.main --vertical betting --limit 50

run-pagamentos:
	python -m src.main --vertical pagamentos --limit 50

run-cobranca:
	python -m src.main --vertical cobranca --limit 50

run-saas:
	python -m src.main --vertical saas_b2b --limit 50

server:
	python -m src.api.server

monitor-bets:
	python -c "from src.jobs.monitor import run_monitor; print(run_monitor('betting'))"

monitor-ips:
	python -c "from src.jobs.monitor import run_monitor; print(run_monitor('pagamentos'))"

rescore:
	python -c "from src.jobs.rescore import run_rescore; print(run_rescore())"

dashboard:
	@echo "Sobe o servidor em uma janela ('make server') e abre:"
	@echo "  http://127.0.0.1:8765/dashboard/"
	@open "http://127.0.0.1:8765/dashboard/" 2>/dev/null || xdg-open "http://127.0.0.1:8765/dashboard/" 2>/dev/null || true

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/

format:
	black src/ tests/
	ruff check --fix src/ tests/

clean:
	rm -rf data/raw/* data/processed/*
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
