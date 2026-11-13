# Internal Windows COM bridge: export a font-faithful PDF for render_slides.py to rasterize.
# Direct Slide.Export PNG substitutes embedded fonts and is deliberately not used.
param(
  [Parameter(Mandatory = $true)][string]$Pptx,
  [Parameter(Mandatory = $true)][string]$OutDir,
  [string]$SessionFile,
  [switch]$Cleanup
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PptdWindowProcess {
  [DllImport("user32.dll")]
  public static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint processId);
}
'@
function Get-ApplicationPid($application) {
  [uint32]$applicationPid = 0
  # GetActiveObject can return an untyped IDispatch whose hidden HWND property is unavailable.
  $handle = $application.HWND
  if ($null -ne $handle) {
    [PptdWindowProcess]::GetWindowThreadProcessId([IntPtr]$handle, [ref]$applicationPid) | Out-Null
  }
  if ($applicationPid -ne 0) { return $applicationPid }
  $sessionId = [Diagnostics.Process]::GetCurrentProcess().SessionId
  $ids = @(Get-Process -Name POWERPNT -ErrorAction SilentlyContinue |
           Where-Object { $_.SessionId -eq $sessionId } | Select-Object -ExpandProperty Id)
  if ($ids.Count -eq 1) { return $ids[0] }
  throw 'Cannot safely identify PowerPoint: no HWND and multiple/no processes in this Windows session'
}
function Release-Com($object) {
  if ($null -ne $object -and [Runtime.InteropServices.Marshal]::IsComObject($object)) {
    [Runtime.InteropServices.Marshal]::FinalReleaseComObject($object) | Out-Null
  }
}
function Save-Session($state) {
  if ($SessionFile) {
    [IO.File]::WriteAllText([IO.Path]::GetFullPath($SessionFile), ($state | ConvertTo-Json -Compress), $utf8)
  }
}
function Close-Target($presentations, [string]$source) {
  # Open may have failed after creating a presentation but before returning its COM handle.
  for ($i = $presentations.Count; $i -ge 1; $i--) {
    $candidate = $null
    try {
      $candidate = $presentations.Item($i)
      if ([string]::Equals($candidate.FullName, $source, [StringComparison]::OrdinalIgnoreCase)) {
        if ($candidate.ReadOnly -ne -1) { throw 'Refusing to close a non-read-only presentation during cleanup' }
        $candidate.Close()
        break
      }
    } finally { Release-Com $candidate }
  }
}

$powerpoint = $null
$presentations = $null
$presentation = $null
$slides = $null
$pageSetup = $null
$state = $null
$canCleanup = $false
$ownedApplication = $false
$failure = $null
$generated = @()
$createdDirectory = $false
$slideCount = 0
try {
  $source = (Resolve-Path -LiteralPath $Pptx).ProviderPath
  if (-not [IO.File]::Exists($source) -or [IO.Path]::GetExtension($source) -ine '.pptx') {
    throw 'Pptx must be an existing local .pptx file'
  }
  if ($Cleanup) {
    # Timeout recovery must not activate COM or touch an application other than the recorded one.
    if (-not $SessionFile) { throw 'Cleanup requires a recorded SessionFile' }
    $state = Get-Content -LiteralPath $SessionFile -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($state.Format -ne 'pptd-powerpoint-session-v1' -or $state.Source -ine $source) {
      throw 'Invalid PowerPoint cleanup session'
    }
    try { $powerpoint = [Runtime.InteropServices.Marshal]::GetActiveObject('PowerPoint.Application') }
    catch [Runtime.InteropServices.COMException] { $powerpoint = $null }
    if ($null -ne $powerpoint -and (Get-ApplicationPid $powerpoint) -ne $state.ApplicationPid) {
      Release-Com $powerpoint
      $powerpoint = $null
    }
    if ($null -ne $powerpoint) {
      $canCleanup = $true
      $ownedApplication = [bool]$state.OwnedApplication
      $presentations = $powerpoint.Presentations
    }
  } else {
    $target = [IO.Path]::GetFullPath($OutDir)
    if (Test-Path -LiteralPath $target) {
      $directory = Get-Item -LiteralPath $target -Force
      if (-not $directory.PSIsContainer -or ($directory.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'OutDir must be a real directory, not a file or link'
      }
      if (@(Get-ChildItem -LiteralPath $target -Force).Count -ne 0) { throw 'OutDir must be empty; no files will be overwritten' }
    } else {
      [IO.Directory]::CreateDirectory($target) | Out-Null
      $createdDirectory = $true
    }
    $previousPids = @(Get-Process -Name POWERPNT -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)
    try { $powerpoint = [Runtime.InteropServices.Marshal]::GetActiveObject('PowerPoint.Application') }
    catch [Runtime.InteropServices.COMException] {
      $powerpoint = New-Object -ComObject PowerPoint.Application
    }
    $presentations = $powerpoint.Presentations
    $applicationPid = Get-ApplicationPid $powerpoint
    $ownedApplication = ($previousPids -notcontains $applicationPid)
    $canCleanup = $true
    $state = @{ Format = 'pptd-powerpoint-session-v1'; Source = $source; ApplicationPid = $applicationPid;
                OwnedApplication = $ownedApplication; OpenAttempted = $false; Closed = $false }
    Save-Session $state
    for ($i = 1; $i -le $presentations.Count; $i++) {
      $candidate = $null
      try {
        $candidate = $presentations.Item($i)
        if ([string]::Equals($candidate.FullName, $source, [StringComparison]::OrdinalIgnoreCase)) {
          throw 'The target is already open in PowerPoint; close it first to protect the user presentation'
        }
      } finally { Release-Com $candidate }
    }
    $state.OpenAttempted = $true
    Save-Session $state
    # ReadOnly = true, Untitled = false, WithWindow = false. Open belongs inside try/finally.
    $presentation = $presentations.Open($source, -1, 0, 0)
    $pageSetup = $presentation.PageSetup
    if ($pageSetup.SlideWidth -le 0 -or $pageSetup.SlideHeight -le 0) { throw 'Invalid slide canvas' }
    $slides = $presentation.Slides
    $slideCount = $slides.Count
    if ($slideCount -lt 1) { throw 'The presentation has no slides' }
    $pdf = Join-Path $target 'slides.pdf'
    $generated += $pdf
    # Unlike direct PNG export, Office's fixed-format PDF path preserves embedded fonts.
    # SaveAs PDF leaves the source identity/read-only state unchanged; ExportAsFixedFormat
    # has incompatible optional-argument COM bindings in some PowerShell/Office versions.
    $presentation.SaveAs($pdf, 32)
  }
} catch { $failure = $_.Exception.Message }
finally {
  if ($null -ne $powerpoint) {
    try {
      if ($canCleanup -and $null -ne $state -and $state.OpenAttempted -and -not $state.Closed) {
        if ($null -ne $presentation) { $presentation.Close() }
        else {
          if ($null -eq $presentations) { $presentations = $powerpoint.Presentations }
          Close-Target $presentations $source
        }
        $state.Closed = $true
      }
    } catch { $failure = "$failure PowerPoint presentation cleanup failed: $($_.Exception.Message)".Trim() }
    try {
      # Leave pre-existing PowerPoint sessions and any newly opened user presentations alone.
      if ($ownedApplication) {
        if ($null -eq $presentations) { $presentations = $powerpoint.Presentations }
        if ($presentations.Count -eq 0) { $powerpoint.Quit() }
      }
    } catch { $failure = "$failure PowerPoint application cleanup failed: $($_.Exception.Message)".Trim() }
  }
  Release-Com $pageSetup
  Release-Com $slides
  Release-Com $presentation
  Release-Com $presentations
  Release-Com $powerpoint
  if ($null -ne $state) {
    try { Save-Session $state }
    catch { $failure = "$failure Session recording failed: $($_.Exception.Message)".Trim() }
  }
  if ($failure -and -not $Cleanup) {
    foreach ($filename in $generated) {
      try { [IO.File]::Delete($filename) }
      catch { [Console]::Error.WriteLine("PDF cleanup failed: $($_.Exception.Message)") }
    }
    if ($createdDirectory -and @(Get-ChildItem -LiteralPath $target -Force).Count -eq 0) {
      [IO.Directory]::Delete($target) # Empty directory only; never recursive deletion.
    }
  }
}
if ($failure) {
  [Console]::Error.WriteLine($failure)
  exit 1
}
if ($Cleanup) { @{ status = 'cleaned' } | ConvertTo-Json -Compress }
else { @{ status = 'rendered'; slideCount = $slideCount } | ConvertTo-Json -Compress }
