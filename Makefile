# Lệnh chung (Linux/Mac/GitHub Actions). Trên Windows chạy trực tiếp các lệnh python bên dưới.
PY ?= python

.PHONY: test backtest report build hoi-cuu

build:
	$(PY) build.py

test: build
	$(PY) -m pytest

backtest:
	$(PY) -m bot.cli backtest

report:
	$(PY) -m bot.cli report

# Hồi cứu mở rộng: dự báo tại các thời điểm quá khứ đúng hay sai → docs/HOI_CUU_MO_RONG.md (không cần mạng)
hoi-cuu:
	$(PY) tools/hoi_cuu_mo_rong.py
