@echo off
set "PYTHONPATH=%~dp0src"
python "%~dp0run.py" %*
exit /b %ERRORLEVEL%
