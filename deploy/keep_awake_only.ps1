# Empeche la mise en veille SANS lancer le scheduler (pour les posts manuels
# programmes). Garde cette fenetre ouverte = PC eveille.
$sig = '[DllImport("kernel32.dll", SetLastError=true)] public static extern uint SetThreadExecutionState(uint esFlags);'
$power = Add-Type -MemberDefinition $sig -Name Power -Namespace Win32 -PassThru
[void]$power::SetThreadExecutionState([uint32]2147483649)   # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
Write-Host "Anti-veille actif (sans scheduler). Garde cette fenetre OUVERTE."
try {
    while ($true) { Start-Sleep -Seconds 3600 }
}
finally {
    [void]$power::SetThreadExecutionState([uint32]2147483648)
}
