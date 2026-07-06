@echo off
title AutoMontage - Distribution (NE PAS FERMER)
REM Lance le scheduler quotidien (7h/11h30/15h/17h/21h) + bot Telegram, en
REM empechant la mise en veille du PC tant que cette fenetre reste ouverte.
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\User\Desktop\auto-montage\deploy\keep_awake_run.ps1"
echo.
pause
