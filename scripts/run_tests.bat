@echo off
poetry run pytest --cov --cov-config=pyproject.toml --cov-report=xml
