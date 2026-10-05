param(
    [string]$UserDataPath = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Paradox Interactive\Hearts of Iron IV'),
    [string]$PackagePath = $PSScriptRoot
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

function Get-BoundedPath([string]$Root, [string]$Relative) {
    if ([IO.Path]::IsPathRooted($Relative)) { throw "Absolute payload path: $Relative" }
    $base = [IO.Path]::GetFullPath($Root).TrimEnd('\', '/')
    $full = [IO.Path]::GetFullPath((Join-Path $base $Relative))
    if (-not $full.StartsWith($base + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Payload outside target: $Relative"
    }
    return $full
}

function Assert-NoReparse([string]$Path) {
    $current = [IO.Path]::GetFullPath($Path)
    while ($current) {
        if (Test-Path -LiteralPath $current) {
            $item = Get-Item -LiteralPath $current -Force
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "Reparse point in installation path: $current"
            }
        }
        $parent = [IO.Path]::GetDirectoryName($current)
        if ($parent -eq $current) { break }
        $current = $parent
    }
}

function Get-Sha([string]$Path) {
    $stream = [IO.File]::OpenRead($Path)
    $hasher = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($hasher.ComputeHash($stream))).Replace('-', '').ToLowerInvariant() }
    finally { $stream.Dispose(); $hasher.Dispose() }
}

if (Get-Process -Name hoi4 -ErrorAction SilentlyContinue) { throw 'Save and close HOI4 before installing.' }
$package = [IO.Path]::GetFullPath($PackagePath)
$userData = [IO.Path]::GetFullPath($UserDataPath)
$manifest = Get-Content -LiteralPath (Join-Path $package 'focus-art-manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($manifest.kind -ne 'exclusive-focus-art' -or $manifest.version -ne '4.2.0' -or
    $manifest.folder -ne 'shadows_of_france_unification' -or @($manifest.files).Count -ne 476) {
    throw 'Unexpected focus art manifest.'
}
$modRoot = Get-BoundedPath $userData ('mod/' + $manifest.folder)
$outer = Get-BoundedPath $userData ('mod/' + $manifest.folder + '.mod')
$inner = Get-BoundedPath $modRoot 'descriptor.mod'
$descriptors = @($inner, $outer)
$descriptorText = @{}
foreach ($file in $descriptors) {
    Assert-NoReparse $file
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Existing standalone installation required: $file" }
    $content = [IO.File]::ReadAllText($file)
    $version = [regex]::Match($content, '(?m)^version="([^"]+)"\r?$').Groups[1].Value
    if ($version -notin @('4.1.0', '4.2.0') -or -not $content.Contains('name="' + $manifest.name + '"')) {
        throw "Unexpected installed descriptor: $file"
    }
    $descriptorText[$file] = $content
}
$rows = @()
$seen = @{}
foreach ($row in $manifest.files) {
    $relative = [string]$row.path
    if ($relative -cnotmatch '^shadows_of_france_unification/(gfx/interface/sof_focus_unique/[a-z0-9_]+\.dds|interface/sof_focus_unique\.gfx|common/national_focus/sofzh_(paris|corsica)\.txt)$' -or $seen.ContainsKey($relative)) {
        throw "Unexpected or repeated payload: $relative"
    }
    $seen[$relative] = $true
    $source = Get-BoundedPath $package $relative
    $target = Get-BoundedPath (Join-Path $userData 'mod') $relative
    Assert-NoReparse $source
    Assert-NoReparse $target
    if (-not (Test-Path -LiteralPath $source -PathType Leaf) -or (Get-Sha $source) -ne $row.sha256) {
        throw "Package hash mismatch: $relative"
    }
    if ($relative -match '/common/national_focus/') {
        if (-not (Test-Path -LiteralPath $target -PathType Leaf) -or
            (Get-Sha $target) -notin @($row.previous_sha256, $row.sha256)) {
            throw "Installed focus contains other changes; refusing to overwrite: $relative"
        }
    }
    $rows += [pscustomobject]@{ relative = $relative; source = $source; target = $target }
}
if (@($rows | Where-Object { $_.relative -match '\.dds$' }).Count -ne 473 -or
    @($rows | Where-Object { $_.relative -match '\.gfx$' }).Count -ne 1 -or
    @($rows | Where-Object { $_.relative -match '\.txt$' }).Count -ne 2) { throw 'Incorrect patch coverage.' }
$backupDir = Get-BoundedPath $userData 'mod-backups'
Assert-NoReparse $backupDir
[IO.Directory]::CreateDirectory($backupDir) | Out-Null
$backup = Get-BoundedPath $backupDir ('sof-focus-art-4.2.0-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '.zip')
$oldFiles = @($rows | Where-Object { Test-Path -LiteralPath $_.target -PathType Leaf })
$newFiles = @($rows | Where-Object { -not (Test-Path -LiteralPath $_.target) } | ForEach-Object { $_.relative })
$archive = [IO.Compression.ZipFile]::Open($backup, [IO.Compression.ZipArchiveMode]::Create)
try {
    foreach ($row in $oldFiles) {
        [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $row.target, $row.relative) | Out-Null
    }
    foreach ($file in $descriptors) {
        $name = $file.Substring(([IO.Path]::GetFullPath((Join-Path $userData 'mod'))).Length + 1).Replace('\', '/')
        [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $file, $name) | Out-Null
    }
    $entry = $archive.CreateEntry('rollback-manifest.json')
    $writer = New-Object IO.StreamWriter($entry.Open(), (New-Object Text.UTF8Encoding($false)))
    try { $writer.Write((@{ version = '4.2.0'; introduced_files = $newFiles; scope = 'focus-art-only' } | ConvertTo-Json -Depth 4)) }
    finally { $writer.Dispose() }
} finally { $archive.Dispose() }
$archive = [IO.Compression.ZipFile]::OpenRead($backup)
try {
    foreach ($row in $oldFiles) {
        $entry = $archive.GetEntry($row.relative)
        $stream = $entry.Open()
        $hasher = [Security.Cryptography.SHA256]::Create()
        try { $digest = ([BitConverter]::ToString($hasher.ComputeHash($stream))).Replace('-', '').ToLowerInvariant() }
        finally { $stream.Dispose(); $hasher.Dispose() }
        if ($digest -ne (Get-Sha $row.target)) { throw "Backup verification failed: $($row.relative)" }
    }
} finally { $archive.Dispose() }
try {
    foreach ($row in $rows) {
        Assert-NoReparse $row.target
        [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($row.target)) | Out-Null
        Copy-Item -LiteralPath $row.source -Destination $row.target
        if ((Get-Sha $row.target) -ne (Get-Sha $row.source)) { throw "Installed hash mismatch: $($row.relative)" }
    }
    foreach ($file in $descriptors) {
        $updated = [regex]::Replace($descriptorText[$file], '(?m)^version="[^"]+"', 'version="4.2.0"')
        [IO.File]::WriteAllText($file, $updated, (New-Object Text.UTF8Encoding($false)))
        if ([IO.File]::ReadAllText($file) -cne $updated) { throw "Descriptor verification failed: $file" }
    }
} catch {
    $failure = $_
    $archive = [IO.Compression.ZipFile]::OpenRead($backup)
    try {
        foreach ($entry in $archive.Entries) {
            if ($entry.FullName -eq 'rollback-manifest.json') { continue }
            $target = Get-BoundedPath (Join-Path $userData 'mod') $entry.FullName
            Assert-NoReparse $target
            [IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $target, $true)
        }
        foreach ($relative in $newFiles) {
            $target = Get-BoundedPath (Join-Path $userData 'mod') $relative
            Assert-NoReparse $target
            if (Test-Path -LiteralPath $target -PathType Leaf) { Remove-Item -LiteralPath $target }
        }
    } finally { $archive.Dispose() }
    throw $failure
}
@{ ok = $true; version = '4.2.0'; payload_files = $rows.Count; backup = $backup;
   introduced_files = $newFiles.Count; game_engine_verified = $false } | ConvertTo-Json -Compress
