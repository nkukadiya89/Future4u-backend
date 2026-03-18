@echo off
echo Running Black...
black .
if %errorlevel% neq 0 exit /b %errorlevel%

echo Running isort...
isort . --profile=black --skip=env
if %errorlevel% neq 0 exit /b %errorlevel%

echo Running Flake8...
flake8 . --exclude=env
if %errorlevel% neq 0 exit /b %errorlevel%

echo All checks passed.
