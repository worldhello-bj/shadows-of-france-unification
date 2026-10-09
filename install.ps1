param(
    [string]$UserDataPath = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Paradox Interactive\Hearts of Iron IV'),
    [string]$PackagePath = $PSScriptRoot,
    [string]$TargetPath = ''
)
$ErrorActionPreference = 'Stop'
$source = Join-Path $PackagePath 'mod'
if (Get-Process -Name hoi4 -ErrorAction SilentlyContinue) {
    throw 'Save and close HOI4 before replacing its mod files.'
}
$source = (Resolve-Path -LiteralPath $source).Path
$folder = 'shadows_of_france_unification'
$writeLauncherDescriptor = [string]::IsNullOrWhiteSpace($TargetPath)
if ($writeLauncherDescriptor) { $TargetPath = Join-Path (Join-Path $UserDataPath 'mod') $folder }
$target = [IO.Path]::GetFullPath($TargetPath)
if ($target.Equals($source, [StringComparison]::OrdinalIgnoreCase)) { throw 'Choose a target outside the source directory.' }
$oldDescriptor = Join-Path $target 'descriptor.mod'
$publication = $null
if (Test-Path -LiteralPath $oldDescriptor) {
    $previous = Get-Content -LiteralPath $oldDescriptor -Raw -Encoding UTF8
    $match = [Regex]::Match($previous, '(?m)^\s*remote_file_id\s*=\s*"?([0-9]+)"?\s*$')
    if ($match.Success) { $publication = $match.Groups[1].Value }
}
if (Test-Path -LiteralPath $target) {
    $backup = Join-Path (Join-Path $UserDataPath 'mod-backups') ('shadows-of-france-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
    New-Item -ItemType Directory -Path $backup -Force | Out-Null
    Copy-Item -LiteralPath $target -Destination $backup -Recurse -Force
    Write-Host "Backup: $backup"
}
New-Item -ItemType Directory -Path $target -Force | Out-Null
Get-ChildItem -LiteralPath $source -Force | Copy-Item -Destination $target -Recurse -Force
$descriptor = Get-Content -LiteralPath (Join-Path $target 'descriptor.mod') -Raw -Encoding UTF8
if ($publication) {
    $descriptor = [Regex]::Replace($descriptor, '(?m)^\s*remote_file_id\s*=.*(?:\r?\n|$)', '')
    $descriptor = $descriptor.TrimEnd() + "`r`nremote_file_id=`"$publication`"`r`n"
    [IO.File]::WriteAllText((Join-Path $target 'descriptor.mod'), $descriptor, [Text.UTF8Encoding]::new($false))
}
if ($writeLauncherDescriptor) {
    $outer = Join-Path (Join-Path $UserDataPath 'mod') ($folder + '.mod')
    $descriptor = [Regex]::Replace($descriptor, '(?m)^\s*path\s*=.*(?:\r?\n|$)', '')
    $descriptor = $descriptor.TrimEnd() + "`r`npath=`"$($target.Replace('\','/'))`"`r`n"
    [IO.File]::WriteAllText($outer, $descriptor, [Text.UTF8Encoding]::new($false))
}
Write-Host "Installed source files to $target"
