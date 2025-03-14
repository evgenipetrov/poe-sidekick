@echo off
echo Running type checks...
call scripts\run_type_check.bat
if %errorlevel% neq 0 exit /b %errorlevel%

echo.
echo Running tests...
call scripts\run_tests.bat
if %errorlevel% neq 0 exit /b %errorlevel%

echo.
echo Running pre-commit checks...
call scripts\run_pre_commit.bat
if %errorlevel% neq 0 exit /b %errorlevel%
