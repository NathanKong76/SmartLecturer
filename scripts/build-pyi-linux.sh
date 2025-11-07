#!/bin/bash
# -*- coding: utf-8 -*-
# PyInstaller Build Script for Linux
# Packages the Streamlit application into a standalone executable

set -e

VERSION=${1:-"1.0.0"}
CLEAN=${2:-"false"}

# Color output functions
function info() {
    echo -e "\033[0;36m$1\033[0m"
}

function success() {
    echo -e "\033[0;32m$1\033[0m"
}

function warning() {
    echo -e "\033[0;33m$1\033[0m"
}

function error() {
    echo -e "\033[0;31m$1\033[0m"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DIST_DIR="$PROJECT_ROOT/dist"
BUILD_DIR="$PROJECT_ROOT/build"

info "=========================================="
info "PyInstaller Linux 打包脚本"
info "=========================================="
echo ""

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    error "此脚本仅支持 Linux 系统"
    exit 1
fi

# Check if PyInstaller is installed
info "检查 PyInstaller..."
if ! python3 -m PyInstaller --version &> /dev/null; then
    warning "PyInstaller 未安装，正在安装..."
    python3 -m pip install pyinstaller
    if [ $? -ne 0 ]; then
        error "PyInstaller 安装失败"
        exit 1
    fi
    success "PyInstaller 安装完成"
else
    PYI_VERSION=$(python3 -m PyInstaller --version 2>&1)
    success "PyInstaller 已安装: $PYI_VERSION"
fi

# Clean previous builds
if [ "$CLEAN" = "true" ]; then
    info "清理旧的构建文件..."
    rm -rf "$DIST_DIR" "$BUILD_DIR"
    success "清理完成"
fi

# Create PyInstaller spec file
info "生成 PyInstaller 配置文件..."

SPEC_FILE="$PROJECT_ROOT/lecturer.spec"
cat > "$SPEC_FILE" << 'EOF'
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['pyi_entry.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('app', 'app'),
    ],
    hiddenimports=[
        'streamlit',
        'streamlit.web.cli',
        'streamlit.runtime.scriptrunner.script_runner',
        'streamlit.runtime.state',
        'streamlit.components.v1',
        'streamlit.version',
        'streamlit.config',
        'streamlit.runtime',
        'streamlit.runtime.caching',
        'streamlit.runtime.legacy_caching',
        'streamlit.runtime.metrics_util',
        'streamlit.runtime.scriptrunner',
        'streamlit.runtime.state.session_state',
        'streamlit.runtime.state.widgets',
        'streamlit.web',
        'streamlit.web.server',
        'importlib.metadata',
        'importlib_metadata',
        'langchain',
        'langchain_google_genai',
        'langchain_openai',
        'google.generativeai',
        'openai',
        'PIL',
        'pymupdf',
        'dotenv',
        'tqdm',
        'markdown',
        'beautifulsoup4',
        'pymdown_extensions',
        'pkg_resources',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='lecturer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='lecturer',
)
EOF

success "配置文件已生成: $SPEC_FILE"

# Build with PyInstaller
echo ""
info "开始打包..."
info "这可能需要几分钟时间..."

cd "$PROJECT_ROOT"
python3 -m PyInstaller lecturer.spec --clean --noconfirm

if [ $? -ne 0 ]; then
    error "打包失败"
    exit 1
fi

# Create package directory
PACKAGE_NAME="lecturer-linux-v$VERSION"
PACKAGE_DIR="$DIST_DIR/$PACKAGE_NAME"
rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR"

# Copy built files
info "复制打包文件..."
LECTURER_DIR="$DIST_DIR/lecturer"
if [ -d "$LECTURER_DIR" ]; then
    cp -r "$LECTURER_DIR"/* "$PACKAGE_DIR/"
    success "文件已复制到: $PACKAGE_DIR"
else
    error "未找到打包输出目录: $LECTURER_DIR"
    exit 1
fi

# Copy additional files
info "复制额外文件..."
cp "$PROJECT_ROOT/README.md" "$PACKAGE_DIR/" 2>/dev/null || true
cp "$PROJECT_ROOT/RELEASE.md" "$PACKAGE_DIR/" 2>/dev/null || true
cp "$PROJECT_ROOT/HTML-pdf2htmlEX版使用说明.md" "$PACKAGE_DIR/" 2>/dev/null || true

# Create .env.example
cat > "$PACKAGE_DIR/.env.example" << 'EOF'
GEMINI_API_KEY=your_gemini_api_key_here
EOF

# Create startup script
cat > "$PACKAGE_DIR/start.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
./lecturer
EOF
chmod +x "$PACKAGE_DIR/start.sh"

echo ""
success "=========================================="
success "Linux 打包完成！"
success "=========================================="
echo ""
info "打包目录: $PACKAGE_DIR"
info "可执行文件: $PACKAGE_DIR/lecturer"
echo ""

