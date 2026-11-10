. "$PSScriptRoot\prelude.ps1"
$z = 'ffmpeg-release-essentials.zip'
$got = (Fetch "https://www.gyan.dev/ffmpeg/builds/$z" "$R\dl\$z") -and (Fetch "https://www.gyan.dev/ffmpeg/builds/$z.sha256" "$R\dl\$z.sha256")
$want = if ($got) { ((Get-Content -LiteralPath "$R\dl\$z.sha256" -Raw).Trim() -split '\s+')[0].ToLower() } else { '' }
$hashok = $got -and ((Sha "$R\dl\$z") -eq $want)
New-Item -ItemType Directory -Force -Path "$R\dl\ff", "$R\ffmpeg\bin" | Out-Null
& tar.exe -xf "$R\dl\$z" -C "$R\dl\ff"
Get-ChildItem -LiteralPath "$R\dl\ff" -Recurse -Filter 'ff*.exe' | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination "$R\ffmpeg\bin" -Force }
$ver = (& ffmpeg -hide_banner -version | Select-Object -First 1)
$enc = (& ffmpeg -hide_banner -encoders 2>&1 | Out-String); $flt = (& ffmpeg -hide_banner -filters 2>&1 | Out-String)
$has = @{}; foreach ($f in 'zscale', 'lut3d', 'loudnorm', 'drawtext', 'tonemap') { $has[$f] = $flt -match "\s$f\s" }
$x264 = $enc -match 'libx264'; $vp9 = $enc -match 'libvpx-vp9'
function Try-FF([string[]]$a) { & ffmpeg -v error -hide_banner @a 2> "$R\logs\ff-last.txt"; return ($LASTEXITCODE -eq 0) }
# frames tagged as iPhone HDR (HLG) first: untagged test frames give zscale nothing to convert from, on a Mac too
$hlg = Try-FF @('-f', 'lavfi', '-i', 'testsrc2=s=320x240:d=1', '-vf', 'format=yuv420p10le,setparams=color_primaries=bt2020:color_trc=arib-std-b67:colorspace=bt2020nc:range=tv,zscale=tin=arib-std-b67:pin=bt2020:min=bt2020nc:t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p', '-f', 'null', '-')
Copy-Item -LiteralPath "$R\logs\ff-last.txt" "$R\logs\ff-hlg.txt" -ErrorAction SilentlyContinue
$lutFull = Try-FF @('-f', 'lavfi', '-i', 'testsrc2=s=320x240:d=1', '-vf', "lut3d=file='$ENG\luts\warm.cube'", '-f', 'null', '-')
Push-Location -LiteralPath $ENG
$lutRel = Try-FF @('-f', 'lavfi', '-i', 'testsrc2=s=320x240:d=1', '-vf', 'lut3d=file=luts/warm.cube', '-f', 'null', '-')
Pop-Location
$loud = Try-FF @('-f', 'lavfi', '-i', 'sine=d=2', '-af', 'loudnorm=I=-14:TP=-1.5', '-f', 'null', '-')
$dtNone = Try-FF @('-f', 'lavfi', '-i', 'testsrc2=s=320x240:d=1', '-vf', 'drawtext=text=Hi:fontsize=40:fontcolor=white', '-frames:v', '1', "$R\out\drawtext-default.png", '-y')
Copy-Item 'C:\Windows\Fonts\arial.ttf' "$R\font.ttf"
Push-Location -LiteralPath $R
$dtFile = Try-FF @('-f', 'lavfi', '-i', 'testsrc2=s=320x240:d=1', '-vf', 'drawtext=fontfile=font.ttf:text=Hi:fontsize=40:fontcolor=white', '-frames:v', '1', 'out/drawtext-fontfile.png', '-y')
Pop-Location
$enc264 = Try-FF @('-f', 'lavfi', '-i', 'testsrc2=s=320x240:d=1', '-c:v', 'libx264', '-f', 'null', '-')
$ok = $hashok -and $x264 -and $vp9 -and $has.zscale -and $has.lut3d -and $has.loudnorm -and $hlg -and $lutRel -and $loud -and ($dtNone -or $dtFile) -and $enc264
Row '7 ffmpeg (gyan.dev essentials)' $ok "$ver; checksum $hashok; libx264 $x264, libvpx-vp9 $vp9; filters: $(($has.GetEnumerator() | Sort-Object Name | ForEach-Object { "$($_.Name) $($_.Value)" }) -join ', '); HLG tonemap $hlg; lut3d full Windows path $lutFull, relative $lutRel; loudnorm $loud; drawtext no font $dtNone, font file $dtFile; x264 encode $enc264"
