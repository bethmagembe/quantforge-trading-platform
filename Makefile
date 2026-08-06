.PHONY: install test lint data backtest benchmark api dashboard docker-up

install:
	python -m pip install -e '.[dev]'

test:
	python -m pytest

lint:
	ruff check src tests app scripts

data:
	python -m trading_system.cli generate-data

backtest:
	python -m trading_system.cli backtest --strategy sma_crossover

benchmark:
	python -m trading_system.cli benchmark --rows 2000000

api:
	uvicorn trading_system.api:app --reload

dashboard:
	streamlit run app/dashboard.py

docker-up:
	docker compose up --build
