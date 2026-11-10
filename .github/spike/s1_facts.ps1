. "$PSScriptRoot\prelude.ps1"
$cv = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
$c = Get-Command curl.exe -ErrorAction SilentlyContinue; $t = Get-Command tar.exe -ErrorAction SilentlyContinue
$vc = (@('vcruntime140.dll', 'vcruntime140_1.dll', 'msvcp140.dll') | ForEach-Object { "$_ $(Test-Path "C:\Windows\System32\$_")" }) -join ', '
$note = "$($cv.ProductName) build $($cv.CurrentBuild).$($cv.UBR); Windows PowerShell $($PSVersionTable.PSVersion); " +
  "pwsh 7 $(Test-Path 'C:\Program Files\PowerShell\7\pwsh.exe'); Git Bash $(Test-Path 'C:\Program Files\Git\bin\bash.exe'); " +
  "C: free $([math]::Round((Get-PSDrive C).Free / 1GB, 1)) GB, D: free $([math]::Round((Get-PSDrive D).Free / 1GB, 1)) GB; " +
  "RAM $([math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)) GB, $env:NUMBER_OF_PROCESSORS cores; " +
  "curl.exe $([bool]$c), tar.exe $([bool]$t); C++ runtime on the runner: $vc"
Row '1 runner facts' ([bool]$c -and [bool]$t) $note
