#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-
# PDF2htmlEX WSL Auto Installer
# Automatically installs WSL (if needed) and pdf2htmlEX in WSL

param(
    [string]$Distro = "",
    [switch]$SkipWSLCheck = $false
)

$ErrorActionPreference = "Stop"

# Color output functions
function Write-Info {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Red
}

# Check if running as administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Check if WSL is installed
function Test-WSLInstalled {
    try {
        $result = wsl --status 2>&1
        if ($LASTEXITCODE -eq 0) {
            return $true
        }
        return $false
    } catch {
        return $false
    }
}

# Get WSL distributions
function Get-WSLDistributions {
    try {
        $output = wsl --list --verbose 2>&1
        if ($LASTEXITCODE -ne 0) {
            return @()
        }
        
        $distros = @()
        $lines = $output | Select-Object -Skip 1
        foreach ($line in $lines) {
            if ($line -match '^\s*(\S+)\s+(\S+)\s+(.*)') {
                $name = $matches[1]
                $version = $matches[2]
                if ($version -eq "1" -or $version -eq "2") {
                    $distros += $name
                }
            }
        }
        return $distros
    } catch {
        return @()
    }
}

# Get default WSL distribution
function Get-DefaultWSLDistro {
    try {
        $output = wsl --list --verbose 2>&1
        if ($LASTEXITCODE -ne 0) {
            return $null
        }
        
        $lines = $output | Select-Object -Skip 1
        foreach ($line in $lines) {
            if ($line -match '^\s*(\S+)\s+(\S+)\s+(.*)') {
                $name = $matches[1]
                $version = $matches[2]
                if ($version -eq "1" -or $version -eq "2") {
                    # Check if it's the default (marked with *)
                    if ($line -match '\*') {
                        return $name
                    }
                    # Otherwise return first one
                    return $name
                }
            }
        }
        return $null
    } catch {
        return $null
    }
}

# Get Ubuntu version from WSL
function Get-UbuntuVersion {
    param([string]$DistroName)
    
    try {
        $script = @"
. /etc/os-release
echo "ID=\$ID"
echo "VERSION_ID=\$VERSION_ID"
echo "VERSION_CODENAME=\$VERSION_CODENAME"
"@
        
        $output = wsl -d $DistroName -e bash -c $script 2>&1
        if ($LASTEXITCODE -ne 0) {
            return $null
        }
        
        $result = @{}
        foreach ($line in $output) {
            if ($line -match '^ID=(.+)$') {
                $result['ID'] = $matches[1]
            } elseif ($line -match '^VERSION_ID="?([^"]+)"?$') {
                $result['VERSION_ID'] = $matches[1]
            } elseif ($line -match '^VERSION_CODENAME=(.+)$') {
                $result['VERSION_CODENAME'] = $matches[1]
            }
        }
        
        return $result
    } catch {
        return $null
    }
}

# Get pdf2htmlEX .deb URL based on Ubuntu version
function Get-Pdf2htmlEXDebUrl {
    param([string]$VersionId, [string]$Codename)
    
    $baseUrl = "https://github.com/pdf2htmlEX/pdf2htmlEX/releases/download/v0.18.8.rc1"
    
    # Map Ubuntu versions to .deb packages
    $versionMap = @{
        "20.04" = "pdf2htmlEX-0.18.8.rc1-master-20200630-Ubuntu-focal-x86_64.deb"
        "22.04" = "pdf2htmlEX-0.18.8.rc1-master-20200630-Ubuntu-focal-x86_64.deb"  # Use focal as fallback
        "24.04" = "pdf2htmlEX-0.18.8.rc1-master-20200630-Ubuntu-focal-x86_64.deb"  # Use focal as fallback
    }
    
    $codenameMap = @{
        "focal" = "pdf2htmlEX-0.18.8.rc1-master-20200630-Ubuntu-focal-x86_64.deb"
        "jammy" = "pdf2htmlEX-0.18.8.rc1-master-20200630-Ubuntu-focal-x86_64.deb"  # Use focal as fallback
        "noble" = "pdf2htmlEX-0.18.8.rc1-master-20200630-Ubuntu-focal-x86_64.deb"  # Use focal as fallback
    }
    
    # Try codename first
    if ($Codename -and $codenameMap.ContainsKey($Codename)) {
        return "$baseUrl/$($codenameMap[$Codename])"
    }
    
    # Try version ID
    if ($VersionId -and $versionMap.ContainsKey($VersionId)) {
        return "$baseUrl/$($versionMap[$VersionId])"
    }
    
    # Default to focal
    return "$baseUrl/pdf2htmlEX-0.18.8.rc1-master-20200630-Ubuntu-focal-x86_64.deb"
}

# Install pdf2htmlEX in WSL
function Install-Pdf2htmlEXInWSL {
    param([string]$DistroName, [string]$DebUrl)
    
    Write-Info "正在在 WSL ($DistroName) 中安装 pdf2htmlEX..."
    
    $installScript = @"
set -e
cd ~
mkdir -p Downloads
cd Downloads

# Download .deb package
echo "正在下载 pdf2htmlEX..."
wget -O pdf2htmlEX.deb "$DebUrl" || curl -L -o pdf2htmlEX.deb "$DebUrl"

# Install
echo "正在安装 pdf2htmlEX..."
sudo apt update
sudo apt install -y ./pdf2htmlEX.deb

# Verify installation
echo "验证安装..."
pdf2htmlEX --version || pdf2htmlEX -v

# Cleanup
rm -f pdf2htmlEX.deb

echo "安装完成！"
"@
    
    try {
        $output = wsl -d $DistroName -e bash -c $installScript 2>&1
        $exitCode = $LASTEXITCODE
        
        if ($exitCode -eq 0) {
            Write-Success "pdf2htmlEX 安装成功！"
            Write-Host $output
            return $true
        } else {
            Write-Error "安装失败，退出代码: $exitCode"
            Write-Host $output
            return $false
        }
    } catch {
        Write-Error "安装过程中发生错误: $_"
        return $false
    }
}

# Verify pdf2htmlEX installation
function Test-Pdf2htmlEXInstalled {
    param([string]$DistroName)
    
    try {
        $output = wsl -d $DistroName -e bash -c "pdf2htmlEX --version 2>&1 || pdf2htmlEX -v 2>&1" 2>&1
        if ($LASTEXITCODE -eq 0 -or $output -match "pdf2htmlEX") {
            Write-Success "pdf2htmlEX 已安装: $output"
            return $true
        }
        return $false
    } catch {
        return $false
    }
}

# Main execution
Write-Info "=========================================="
Write-Info "PDF2htmlEX WSL 自动安装脚本"
Write-Info "=========================================="
Write-Host ""

# Check administrator privileges (needed for WSL installation)
if (-not $SkipWSLCheck) {
    $isAdmin = Test-Administrator
    if (-not $isAdmin) {
        Write-Warning "此脚本需要管理员权限来安装 WSL（如果未安装）"
        Write-Warning "请以管理员身份运行 PowerShell，然后重新执行此脚本"
        Write-Host ""
        Write-Info "或者，如果 WSL 已安装，可以使用 -SkipWSLCheck 参数跳过检查"
        exit 1
    }
}

# Check if WSL is installed
Write-Info "检查 WSL 安装状态..."
if (-not (Test-WSLInstalled)) {
    Write-Warning "WSL 未安装，正在自动安装..."
    Write-Info "这将可能需要几分钟时间，并可能需要重启系统"
    Write-Host ""
    
    try {
        wsl --install
        Write-Success "WSL 安装完成！"
        Write-Warning "如果系统提示需要重启，请重启后再次运行此脚本"
        Write-Host ""
        
        # Check if restart is needed
        $restart = Read-Host "是否需要立即重启系统？(Y/N)"
        if ($restart -eq "Y" -or $restart -eq "y") {
            Write-Info "正在重启系统..."
            shutdown /r /t 0
            exit 0
        } else {
            Write-Info "请手动重启系统后再次运行此脚本"
            exit 0
        }
    } catch {
        Write-Error "WSL 安装失败: $_"
        Write-Info "请手动运行: wsl --install"
        exit 1
    }
} else {
    Write-Success "WSL 已安装"
}

# Get WSL distribution
Write-Host ""
Write-Info "检测 WSL 发行版..."
$distros = Get-WSLDistributions

if ($distros.Count -eq 0) {
    Write-Error "未找到已安装的 WSL 发行版"
    Write-Info "请先安装 Ubuntu 发行版: wsl --install -d Ubuntu"
    exit 1
}

if ($Distro -eq "") {
    $defaultDistro = Get-DefaultWSLDistro
    if ($defaultDistro) {
        $Distro = $defaultDistro
        Write-Info "使用默认发行版: $Distro"
    } else {
        $Distro = $distros[0]
        Write-Info "使用第一个发行版: $Distro"
    }
} else {
    if ($distros -notcontains $Distro) {
        Write-Warning "指定的发行版 '$Distro' 未找到"
        Write-Info "可用发行版: $($distros -join ', ')"
        $Distro = $distros[0]
        Write-Info "使用: $Distro"
    }
}

# Get Ubuntu version
Write-Host ""
Write-Info "检测 Ubuntu 版本..."
$osInfo = Get-UbuntuVersion -DistroName $Distro

if (-not $osInfo) {
    Write-Error "无法检测 Ubuntu 版本信息"
    exit 1
}

if ($osInfo['ID'] -ne "ubuntu") {
    Write-Warning "检测到的发行版不是 Ubuntu: $($osInfo['ID'])"
    Write-Info "此脚本主要为 Ubuntu 设计，但将尝试安装兼容版本"
}

$versionId = $osInfo['VERSION_ID']
$codename = $osInfo['VERSION_CODENAME']

Write-Success "检测到: Ubuntu $versionId ($codename)"

# Get .deb URL
$debUrl = Get-Pdf2htmlEXDebUrl -VersionId $versionId -Codename $codename
Write-Info "下载 URL: $debUrl"

# Check if already installed
Write-Host ""
if (Test-Pdf2htmlEXInstalled -DistroName $Distro) {
    Write-Success "pdf2htmlEX 已经安装！"
    exit 0
}

# Install pdf2htmlEX
Write-Host ""
$success = Install-Pdf2htmlEXInWSL -DistroName $Distro -DebUrl $debUrl

if ($success) {
    Write-Host ""
    Write-Success "=========================================="
    Write-Success "安装完成！"
    Write-Success "=========================================="
    Write-Host ""
    Write-Info "验证安装..."
    Test-Pdf2htmlEXInstalled -DistroName $Distro
    Write-Host ""
    Write-Info "现在可以在 WSL 中使用 pdf2htmlEX 了！"
    Write-Info "在 Windows 中可以通过 'wsl pdf2htmlEX --version' 调用"
} else {
    Write-Host ""
    Write-Error "=========================================="
    Write-Error "安装失败！"
    Write-Error "=========================================="
    Write-Host ""
    Write-Info "请检查错误信息并手动安装，或参考文档: HTML-pdf2htmlEX版使用说明.md"
    exit 1
}

