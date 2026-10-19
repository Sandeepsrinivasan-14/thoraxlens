@echo off
rem Starts the ThoraxLens web app and opens it in the default browser.
cd /d "%~dp0\.."
"C:\Users\sndps\AppData\Local\Programs\Python\Python311\python.exe" ui\server.py %*
