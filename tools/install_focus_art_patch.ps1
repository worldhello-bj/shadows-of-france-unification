# Install current source files through the common installer.
& (Join-Path (Split-Path $PSScriptRoot -Parent) 'install.ps1') @args
