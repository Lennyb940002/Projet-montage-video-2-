@echo off
REM AutoMontage — pipeline de distribution (scheduler 7h/11h30/15h/17h/21h + bot Telegram).
REM Double-clique pour lancer. Garde cette fenetre OUVERTE = ca poste aux creneaux.
REM Ferme la fenetre = ca s'arrete. (Pour du 24/7 sans PC -> hebergement Oracle.)
REM IMPORTANT : une seule instance a la fois (sinon conflit Telegram).
cd /d "C:\Users\User\Desktop\auto-montage"
python -m backend.distribution.scheduler
echo.
echo --- scheduler arrete ---
pause
