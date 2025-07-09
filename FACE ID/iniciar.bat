@echo off
cd /d %~dp0
set PYTHONPATH=%~dp0python_embebido
set PATH=%PYTHONPATH%;%PATH%

echo Instalando dependencias...
%PYTHONPATH%\python.exe -m pip install --upgrade pip
%PYTHONPATH%\python.exe -m pip install -r requirements.txt

echo Dependencias instaladas. Iniciando la aplicación...
%PYTHONPATH%\python.exe -m hypercorn app:app --bind 0.0.0.0:5000

echo La aplicación ha terminado. Presiona una tecla para salir.
pause
