@echo off
echo [%date% %time%] Inicio de ejecución >> "log_tarea.txt"

cd /d "%~dp0"
call venv\Scripts\activate.bat
python main.py >> "log_tarea.txt" 2>&1

echo [%date% %time%] Fin de ejecución >> "log_tarea.txt"