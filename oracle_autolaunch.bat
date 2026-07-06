@echo off
REM AutoMontage - cherche en boucle une capacite Oracle Free et cree la VM des
REM qu'elle se libere, puis notifie sur Telegram. Garde cette fenetre OUVERTE.
REM Pre-requis : pip install oci  +  cle API dans %USERPROFILE%\.oci\config
REM             +  deploy\oracle_autolaunch.config.json renseigne.
cd /d "C:\Users\User\Desktop\auto-montage"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
python deploy\oracle_autolaunch.py
echo.
echo --- recherche terminee ---
pause
