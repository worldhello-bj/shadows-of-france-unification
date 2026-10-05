param(
    [string]$UserDataPath = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Paradox Interactive\Hearts of Iron IV'),
    [string]$PackagePath = $PSScriptRoot
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$manifestFile = Join-Path $PackagePath 'package-manifest.json'
if (-not $PSBoundParameters.ContainsKey('PackagePath') -and -not (Test-Path -LiteralPath $manifestFile)) {
    $PackagePath = Join-Path $PSScriptRoot 'standalone-package'
    $manifestFile = Join-Path $PackagePath 'package-manifest.json'
}
$packageRoot = [IO.Path]::GetFullPath($PackagePath)
$packagePrefix = $packageRoot.TrimEnd([char[]]'\/') + [IO.Path]::DirectorySeparatorChar
$manifest = Get-Content -LiteralPath $manifestFile -Raw -Encoding UTF8 | ConvertFrom-Json
if ($manifest.format -ne 2 -or $manifest.kind -ne 'standalone' -or
    $manifest.folder -ne 'shadows_of_france_unification' -or $manifest.upstream_is_required -ne $false) {
    throw 'Unrecognized independent edition package.'
}
$userRoot = [IO.Path]::GetFullPath($UserDataPath)
$defaultUserRoot = [IO.Path]::GetFullPath((Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Paradox Interactive\Hearts of Iron IV'))
if ($userRoot.Equals($defaultUserRoot,[StringComparison]::OrdinalIgnoreCase) -and (Get-Process -Name hoi4 -ErrorAction SilentlyContinue)) {
    throw 'HOI4 is running. Save and close the game before installing this version.'
}
if (-not (Test-Path -LiteralPath $userRoot -PathType Container)) {
    throw "HOI4 user directory does not exist: $userRoot"
}
$modRoot = [IO.Path]::GetFullPath((Join-Path $userRoot 'mod'))
[IO.Directory]::CreateDirectory($modRoot) | Out-Null
$modPrefix = $modRoot.TrimEnd([char[]]'\/') + [IO.Path]::DirectorySeparatorChar
$existingFolder = Join-Path $modRoot $manifest.folder
$outerTarget = Join-Path $modRoot ($manifest.folder + '.mod')
$publication = [Collections.Generic.List[string]]::new()
$publishedPreview = $null
if (Test-Path -LiteralPath $outerTarget -PathType Leaf) {
    $previousDescriptor = Get-Content -LiteralPath $outerTarget -Raw -Encoding UTF8
    $identity = [Regex]::Match($previousDescriptor,'(?m)^remote_file_id="[0-9]+"\s*$')
    if ($identity.Success) {
        $publication.Add($identity.Value.Trim())
        $picture = [Regex]::Match($previousDescriptor,'(?m)^picture="([A-Za-z0-9_.-]+\.(?:png|jpg|jpeg))"\s*$')
        if ($picture.Success -and (Test-Path -LiteralPath (Join-Path $existingFolder $picture.Groups[1].Value) -PathType Leaf)) {
            $publication.Add($picture.Value.Trim())
            $publishedPreview = [IO.Path]::GetFullPath((Join-Path $existingFolder $picture.Groups[1].Value))
        }
    }
}
$fileList = [Collections.Generic.List[object]]::new()
$expectedTargets = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($entry in $manifest.files) {
    $relative = [string]$entry.path
    if ($relative -match '(^/|\\|(^|/)\.\.(/|$)|:)' -or
        ($relative -ne ($manifest.folder + '.mod') -and -not $relative.StartsWith($manifest.folder + '/'))) {
        throw "Unsafe package path: $relative"
    }
    $sourceFile = [IO.Path]::GetFullPath((Join-Path $packageRoot $relative))
    $targetFile = [IO.Path]::GetFullPath((Join-Path $modRoot $relative))
    if (-not $sourceFile.StartsWith($packagePrefix, [StringComparison]::OrdinalIgnoreCase) -or
        -not $targetFile.StartsWith($modPrefix, [StringComparison]::OrdinalIgnoreCase) -or
        -not $expectedTargets.Add($targetFile)) {
        throw "Duplicate or escaped package path: $relative"
    }
    if ((Get-FileHash -LiteralPath $sourceFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) {
        throw "Package hash mismatch: $relative"
    }
    if (Test-Path -LiteralPath $targetFile) {
        if ((Get-Item -LiteralPath $targetFile -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Refusing to overwrite a linked file: $targetFile"
        }
    }
    $fileList.Add([PSCustomObject]@{ Relative=$relative; Source=$sourceFile; Target=$targetFile; Hash=$entry.sha256 })
}
foreach ($rel in @(($manifest.folder + '/descriptor.mod'), ($manifest.folder + '.mod'))) {
    $text = Get-Content -LiteralPath (Join-Path $packageRoot $rel) -Raw -Encoding UTF8
    if ($text -match '(?im)^\s*(dependencies|remote_file_id|archive)\s*=') {
        throw 'Standalone descriptor contains a dependency or workshop identity.'
    }
}
if (Test-Path -LiteralPath $existingFolder) {
    if ((Get-Item -LiteralPath $existingFolder -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw 'Standalone target is a linked directory.'
    }
    foreach ($existing in Get-ChildItem -LiteralPath $existingFolder -Recurse -Force) {
        if ($existing.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Standalone target contains a linked path: $($existing.FullName)"
        }
        if (-not $existing.PSIsContainer -and -not $expectedTargets.Contains($existing.FullName) -and $existing.FullName -ne $publishedPreview) {
            throw "Unrecognized existing independent-edition file: $($existing.FullName)"
        }
    }
}
if (Test-Path -LiteralPath $outerTarget) {
    $text = Get-Content -LiteralPath $outerTarget -Raw -Encoding UTF8
    if ($text -notmatch ('(?m)^name="' + [Regex]::Escape($manifest.name) + '"\s*$')) {
        throw 'A different mod already uses the independent-edition descriptor.'
    }
}
$existingOwned = @($fileList | Where-Object { Test-Path -LiteralPath $_.Target })
$backupFile = $null
if ($existingOwned.Count -gt 0) {
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $backupDirectory = Join-Path $userRoot 'mod-backups'
    [IO.Directory]::CreateDirectory($backupDirectory) | Out-Null
    $backupFile = Join-Path $backupDirectory ('sof-unification-' + [DateTime]::Now.ToString('yyyyMMdd-HHmmss-fff') + '.zip')
    $backup = [IO.Compression.ZipFile]::Open($backupFile,[IO.Compression.ZipArchiveMode]::Create)
    try {
        foreach ($file in $existingOwned) {
            [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($backup,$file.Target,$file.Relative) | Out-Null
        }
    } finally { $backup.Dispose() }
}
$created = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($file in $fileList) {
    $directory = [IO.Path]::GetDirectoryName($file.Target)
    if ($created.Add($directory)) { [IO.Directory]::CreateDirectory($directory) | Out-Null }
    if ($file.Target -eq $publishedPreview) {
        $file.Hash = (Get-FileHash -LiteralPath $file.Target -Algorithm SHA256).Hash.ToLowerInvariant()
        continue
    }
    [IO.File]::Copy($file.Source,$file.Target,$true)
    if ($publication.Count -gt 0 -and $file.Relative -in @(($manifest.folder + '/descriptor.mod'), ($manifest.folder + '.mod'))) {
        $descriptorText = [IO.File]::ReadAllText($file.Target)
        foreach ($line in $publication) {
            $key = $line.Split('=')[0]
            $pattern = '(?m)^' + [Regex]::Escape($key) + '=.*$'
            if ([Regex]::IsMatch($descriptorText,$pattern)) {
                $literalLine = $line
                $descriptorText = [Regex]::Replace($descriptorText,$pattern,[Text.RegularExpressions.MatchEvaluator]{ param($m) $literalLine })
            } else { $descriptorText = $descriptorText.TrimEnd() + "`n" + $line + "`n" }
        }
        [IO.File]::WriteAllText($file.Target,$descriptorText,[Text.UTF8Encoding]::new($false))
        $file.Hash = (Get-FileHash -LiteralPath $file.Target -Algorithm SHA256).Hash.ToLowerInvariant()
    }
}
foreach ($file in $fileList) {
    if ((Get-FileHash -LiteralPath $file.Target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $file.Hash) {
        throw "Installed file hash mismatch: $($file.Relative)"
    }
}
[PSCustomObject]@{
    Installed=$true; Standalone=$true; Version=$manifest.version;
    ModDirectory=$existingFolder; Descriptor=$outerTarget; VerifiedFiles=$fileList.Count;
    Backup=$backupFile; ParentModRequired=$false; PlaysetChanged=$false;
    PreservedPublicationMetadata=@($publication); PreservedPreview=$publishedPreview;
    NextStep=('Enable only "' + $manifest.name + '"; disable the original Shadows of France and the old Chinese submod.')
} | ConvertTo-Json
