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
$manifest = Get-Content -LiteralPath (Join-Path $package 'integration-manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($manifest.kind -ne 'focus-integration' -or $manifest.version -ne '4.6.0' -or
    $manifest.folder -ne 'shadows_of_france_unification' -or @($manifest.files).Count -ne 12) {
    throw 'Unexpected script repair manifest.'
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
    if ($version -notin @('4.5.1', '4.6.0') -or -not $content.Contains('name="' + $manifest.name + '"')) {
        throw "Unexpected installed descriptor: $file"
    }
    $descriptorText[$file] = $content
}
$rows = @()
$seen = @{}
foreach ($row in $manifest.files) {
    $relative = [string]$row.path
    if ($relative -cnotin @('shadows_of_france_unification/common/characters/sof_vanilla_historical.txt', 'shadows_of_france_unification/common/ideas/sofzh_cabinet.txt', 'shadows_of_france_unification/common/on_actions/sof20_startup.txt', 'shadows_of_france_unification/common/scripted_effects/sof_vanilla_major.txt', 'shadows_of_france_unification/common/scripted_effects/sofzh_ideology_panel.txt', 'shadows_of_france_unification/common/scripted_guis/sofzh_ideology_panel.txt', 'shadows_of_france_unification/gfx/interface/sofzh_ideology_panel/swatches.dds', 'shadows_of_france_unification/interface/countrypoliticsview.gui', 'shadows_of_france_unification/interface/sofzh_ideology_panel.gfx', 'shadows_of_france_unification/interface/sofzh_ideology_panel.gui', 'shadows_of_france_unification/localisation/simp_chinese/replace/sof_vanilla_major_l_simp_chinese.yml', 'shadows_of_france_unification/localisation/simp_chinese/replace/sofzh_ideology_panel_l_simp_chinese.yml') -or $seen.ContainsKey($relative)) {
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
    $previousProperty = $row.PSObject.Properties['previous_sha256']
    $previousHash = if ($previousProperty) { $previousProperty.Value } else { '' }
    $acceptedHashes = @($previousHash, $row.sha256)
    $compatibleProperty = $row.PSObject.Properties['compatible_sha256']
    if ($compatibleProperty) { $acceptedHashes += @($compatibleProperty.Value) }
    if (Test-Path -LiteralPath $target -PathType Leaf) {
        if ((Get-Sha $target) -notin $acceptedHashes) {
            throw "Installed file contains other changes; refusing to overwrite: $relative"
        }
    } elseif ($previousProperty) { throw "Required script repair file is missing: $relative" }
    $rows += [pscustomobject]@{ relative = $relative; source = $source; target = $target }
}
if ($rows.Count -ne 12) { throw 'Incomplete script repair payload.' }
$deleteRows = @()
if (@($manifest.deletions).Count -ne 2) { throw 'Unexpected obsolete texture list.' }
foreach ($row in $manifest.deletions) {
    $relative = [string]$row.path
    if ($relative -cnotin @('shadows_of_france_unification/gfx/interface/sofzh_ideology_panel/segments.dds', 'shadows_of_france_unification/gfx/interface/sofzh_ideology_panel/disc.dds') -or $seen.ContainsKey($relative)) {
        throw 'Unexpected or repeated obsolete texture.'
    }
    $seen[$relative] = $true
    $target = Get-BoundedPath (Join-Path $userData 'mod') $relative
    Assert-NoReparse $target
    if (Test-Path -LiteralPath $target) {
        if (-not (Test-Path -LiteralPath $target -PathType Leaf) -or (Get-Sha $target) -ne $row.previous_sha256) {
            throw "Obsolete texture contains other changes; refusing to delete: $relative"
        }
    }
    $deleteRows += [pscustomobject]@{ relative = $relative; target = $target; previous = $row.previous_sha256 }
}
$backupDir = Get-BoundedPath $userData 'mod-backups'
Assert-NoReparse $backupDir
[IO.Directory]::CreateDirectory($backupDir) | Out-Null
$backup = Get-BoundedPath $backupDir ('sof-focus-integration-4.6.0-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '.zip')
$allTargets = @($rows) + @($deleteRows)
$oldFiles = @($allTargets | Where-Object { Test-Path -LiteralPath $_.target -PathType Leaf })
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
    try { $writer.Write((@{ version = '4.6.0'; introduced_files = $newFiles; scope = 'focus-integration-only' } | ConvertTo-Json -Depth 4)) }
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
    foreach ($row in $deleteRows) {
        Assert-NoReparse $row.target
        if (Test-Path -LiteralPath $row.target -PathType Leaf) {
            if ((Get-Sha $row.target) -ne $row.previous) { throw 'Obsolete texture changed during installation.' }
            Remove-Item -LiteralPath $row.target
        }
    }
    # integration-deletions-complete
    foreach ($file in $descriptors) {
        $updated = [regex]::Replace($descriptorText[$file], '(?m)^version="[^"]+"', 'version="4.6.0"')
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
@{ ok = $true; version = '4.6.0'; payload_files = $rows.Count; obsolete_texture_paths = $deleteRows.Count; backup = $backup;
   introduced_files = $newFiles.Count; game_engine_verified = $false } | ConvertTo-Json -Compress
