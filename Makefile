# Lệnh chung (Linux/Mac/GitHub Actions). Trên Windows chạy trực tiếp các lệnh python bên dưới.
PY ?= python

.PHONY: test backtest report build

build:
	$(PY) build.py

test: build
	$(PY) -m pytest

backtest:
	$(PY) -m bot.cli backtest

report:
	$(PY) -m bot.cli report
