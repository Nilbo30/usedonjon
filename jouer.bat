@echo off
rem Lanceur Windows : double-clique ce fichier pour jouer.
rem Il se place tout seul dans le bon dossier, ce qui evite l'erreur
rem "No module named donjon" quand la ligne de commande n'est pas au bon endroit.

cd /d "%~dp0"

set LANCEUR=python
where python >nul 2>&1
if errorlevel 1 set LANCEUR=py

where %LANCEUR% >nul 2>&1
if errorlevel 1 (
    echo.
    echo Python n'est pas installe, ou n'a pas ete ajoute au PATH.
    echo Installe-le depuis https://www.python.org/downloads/
    echo en cochant "Add python.exe to PATH" avant de cliquer Install.
    echo.
    pause
    exit /b 1
)

rem pythonw lance la fenetre de jeu sans garder une console noire ouverte
rem derriere. S'il manque, on retombe sur python : mieux vaut une console en
rem trop qu'un jeu qui ne demarre pas.
where %LANCEUR%w >nul 2>&1
if not errorlevel 1 (
    start "" %LANCEUR%w -m donjon %*
    exit /b 0
)

%LANCEUR% -m donjon %*

if errorlevel 1 (
    echo.
    echo Le jeu s'est arrete sur une erreur.
    pause
)
