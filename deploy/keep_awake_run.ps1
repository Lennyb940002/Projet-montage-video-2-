# Lance le scheduler AutoMontage en EMPECHANT la mise en veille du PC.
# Tant que cette fenetre reste ouverte, Windows ne se met pas en veille.
# A la fermeture, la veille est reautorisee.
# Usage : powershell -ExecutionPolicy Bypass -File keep_awake_run.ps1 [args python]
Set-Location "C:\Users\User\Desktop\auto-montage"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$sig = '[DllImport("kernel32.dll", SetLastError=true)] public static extern uint SetThreadExecutionState(uint esFlags);'
$power = Add-Type -MemberDefinition $sig -Name Power -Namespace Win32 -PassThru

# ES_CONTINUOUS (0x80000000=2147483648) | ES_SYSTEM_REQUIRED (0x1) = 2147483649
# -> pas de veille systeme. (Valeurs en decimal : 0x80000001 deborde Int32 en PS 5.1.)
[void]$power::SetThreadExecutionState([uint32]2147483649)
Write-Host "==================================================================="
Write-Host " AutoMontage lance - PC maintenu eveille."
Write-Host " GARDE CETTE FENETRE OUVERTE = ca poste aux creneaux."
Write-Host " Ferme la fenetre = ca s'arrete (et la veille redevient normale)."
Write-Host "==================================================================="

try {
    python -m backend.distribution.scheduler @args
}
finally {
    # Reautorise la veille en sortie (ES_CONTINUOUS seul = 0x80000000).
    [void]$power::SetThreadExecutionState([uint32]2147483648)
    Write-Host "--- scheduler arrete, veille reautorisee ---"
}
