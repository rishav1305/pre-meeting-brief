.PHONY: install dev test lint seed migrate build deploy

install:
	npm install
	pip install -r requirements.txt

dev:
	npm run dev

test:
	python -m pytest tests/ -v

lint:
	ruff check api/ tests/
	npm run lint

migrate:
	alembic upgrade head

seed:
	python -m api.seeds.seed

build:
	npm run build

deploy:
	vercel --prod
