# Render every slide of a .pptx to PNG with the locally installed PowerPoint (Windows only).
# Repository review tool: compare advanced-chart exports against the SVGs rendered in a browser.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools/pptd/render_powerpoint.ps1 `
#     -Pptx .artifacts/pptd/charts.pptx -OutDir .artifacts/pptd/charts-powerpoint
param(
  [Parameter(Mandatory = $true)][string]$Pptx,
  [Parameter(Mandatory = $true)][string]$OutDir,
  [int]$Width = 1920,
  [int]$Height = 1080
)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$source = (Resolve-Path $Pptx).Path
$target = (Resolve-Path $OutDir).Path
$powerpoint = New-Object -ComObject PowerPoint.Application
# ReadOnly, no title change, no window.
$presentation = $powerpoint.Presentations.Open($source, -1, 0, 0)
try {
  $presentation.Export($target, 'PNG', $Width, $Height)
} finally {
  $presentation.Close()
  # Leave PowerPoint running if the user has other presentations open.
  if ($powerpoint.Presentations.Count -eq 0) { $powerpoint.Quit() }
}
