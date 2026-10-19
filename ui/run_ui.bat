@echo off
rem Starts the ThoraxLens web app and opens it in the default browser.
cd /d "%~dp0\.."
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" ui\server.py %*
