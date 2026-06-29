#!/bin/bash
# ============================================================
#  Ai Studio macOS Build Script
#  在 Mac 上运行: chmod +x build_macos.sh && ./build_macos.sh
# ============================================================
set -e

echo "============================================"
echo "  Ai Studio macOS Builder"
echo "============================================"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ── 1. Check environment ──
if ! command -v python3 &>/dev/null; then
    echo "请先安装 Python 3.12: brew install python@3.12"
    exit 1
fi
echo "Python: $(python3 --version)"

if [[ "$(uname)" != "Darwin" ]]; then
    echo "此脚本只能在 macOS 上运行!"
    exit 1
fi

# ── 2. Install dependencies ──
echo ""
echo "=== 安装依赖 ==="
pip3 install --upgrade pip --quiet
pip3 install -r requirements_mac.txt --quiet

if ! command -v sox &>/dev/null; then
    echo "安装 sox..."
    brew install sox
fi
if ! command -v ffmpeg &>/dev/null; then
    echo "安装 ffmpeg..."
    brew install ffmpeg
fi

# ── 3. Prepare tools & assets ──
echo ""
echo "=== 准备音频工具 ==="
mkdir -p tools assets
cp "$(which sox)" tools/sox 2>/dev/null || true
cp "$(which ffmpeg)" tools/ffmpeg 2>/dev/null || true
cp "$(which ffprobe)" tools/ffprobe 2>/dev/null || true
echo "工具已复制到 tools/"

# ── 4. Handle engine module (use .pyc bytecode, skip Windows .pyd) ──
echo ""
echo "=== 处理 engine 模块 ==="
# Delete Windows .pyd files so Python falls back to cross-platform .pyc
# The PYZ.pyz_extracted/ dir has engine.pyc and other .pyc modules
find . -name "*cp312-win_amd64.pyd" -delete 2>/dev/null || true
echo "已删除 Windows .pyd 文件，将使用 .pyc 字节码"

# ── 5. Compile Python → native .so with Cython ──
echo ""
echo "=== Cython 编译 ==="
python3 -c "
from Cython.Build import cythonize
from setuptools import setup, Extension
from pathlib import Path

targets = ['settings.py', 'schemes.py', 't3_config.py', 't3sdk.py', 't3_bridge.py', 'main.py', 'launcher.py']
extensions = []
for name in targets:
    src = Path(name)
    if src.exists():
        mod = name.replace('.py','')
        extensions.append(Extension(mod, sources=[str(src)]))
        print(f'  {name} -> {mod}.so')

if not extensions:
    print('ERROR: No source files found!')
    exit(1)

ext_modules = cythonize(extensions, compiler_directives={
    'language_level': '3', 'boundscheck': False, 'wraparound': False,
    'embedsignature': False,
}, nthreads=0)

setup(name='ai_studio', ext_modules=ext_modules, script_args=['build_ext','--inplace'])
"

# Move source to backup, keep only launcher.py for PyInstaller entry
mkdir -p src_backup
for f in settings.py schemes.py t3_config.py t3sdk.py t3_bridge.py main.py; do
    [ -f "$f" ] && mv "$f" src_backup/
done
echo ""
echo "编译完成:"
ls *.so 2>/dev/null

# ── 6. Build macOS .app with PyInstaller ──
echo ""
echo "=== PyInstaller 打包 ==="
python3 -m PyInstaller \
    --name="Ai Studio" \
    --windowed \
    --icon=assets/audioflow.icns \
    --add-data="tools:tools" \
    --add-data="assets:assets" \
    --add-data="PYZ.pyz_extracted:PYZ.pyz_extracted" \
    --hidden-import=engine \
    --hidden-import=license_client \
    --hidden-import=platform_presets \
    --hidden-import=security_guard \
    --hidden-import=updater \
    --hidden-import=settings \
    --hidden-import=schemes \
    --hidden-import=platform \
    --hidden-import=t3_bridge \
    --hidden-import=t3_config \
    --hidden-import=t3sdk \
    --hidden-import=main \
    --hidden-import=PySide6.QtWebEngineWidgets \
    --hidden-import=PySide6.QtWebEngineCore \
    --noconfirm \
    launcher.py 2>&1 | tail -5

echo ""
echo "============================================"
echo "  构建完成!"
echo "  输出: dist/Ai Studio.app"
echo "  大小: $(du -sh dist/Ai Studio.app 2>/dev/null | cut -f1)"
echo "============================================"
echo ""
echo "测试运行:"
echo "  open 'dist/Ai Studio.app'"
echo ""
echo "签名 + 公证 (分发前必须):"
echo "  codesign --deep --force --verify --sign 'Developer ID Application: YOUR NAME' 'dist/Ai Studio.app'"
echo "  xcrun notarytool submit 'dist/Ai Studio.app' --apple-id YOUR_APPLE_ID --team-id YOUR_TEAM_ID --wait"
