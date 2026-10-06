$source = Split-Path -Parent $PSScriptRoot
$target = 'E:\软件工程'
New-Item -ItemType Directory -Force -Path (Join-Path $target 'calculator-frontend'), (Join-Path $target 'calculator-backend\data') | Out-Null
Copy-Item -Path (Join-Path $source 'calculator-frontend\*') -Destination (Join-Path $target 'calculator-frontend') -Recurse -Force
Copy-Item -Path (Join-Path $source 'calculator-backend\server.py'), (Join-Path $source 'calculator-backend\README.md'), (Join-Path $source 'calculator-backend\codestyle.md') -Destination (Join-Path $target 'calculator-backend') -Force
Copy-Item -Path (Join-Path $source 'README.md'), (Join-Path $source 'assignment-blog.md') -Destination $target -Force
Write-Host "已复制到 $target"

