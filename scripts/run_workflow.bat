@echo off

if "%~1"=="" (
    echo Error: Please specify a workflow name
    echo Usage: run_workflow.bat [workflow_name]
    echo Example: run_workflow.bat trade
    exit /b 1
)

poetry run python -m poe_sidekick --workflow %1
