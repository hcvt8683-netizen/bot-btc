@echo off
setlocal
cd /d "%~dp0"
title Bot xac suat BTC
chcp 65001 >nul
echo === Bot xac suat BTC ===
set "PY="
where py >nul 2>nul && py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 7) else 1)" >nul 2>nul && set "PY=py -3"
if not defined PY python -c "import sys; sys.exit(0 if sys.version_info >= (3, 7) else 1)" >nul 2>nul && set "PY=python"
if not defined PY python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 7) else 1)" >nul 2>nul && set "PY=python3"
if defined PY goto run
echo.
echo May chua co Python 3, nen mo bot truc tiep trong trinh duyet.
echo Neu muc "Nguon du lieu" trong bot bao loi, hay cai Python (xem HUONG_DAN.txt)
echo roi bam dup lai file nay.
start "" "%~dp0bot-xac-suat.html"
timeout /t 10 >nul
goto end
:run
echo Dung Python: %PY%
echo Giu cua so nay mo trong luc dung bot. Dong cua so de tat bot.
echo.
%PY% chay_bot_xac_suat.py
if errorlevel 1 (
  echo.
  echo Bot dung vi gap loi o tren. Chup man hinh cua so nay neu can ho tro.
  pause
)
:end
endlocal
