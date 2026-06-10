#!/bin/bash
# Build KWEngine.app (Release) and package it into a DMG.
# 在 Mac 上运行：bash macapp/build_dmg.sh   （需要安装完整版 Xcode）
set -euo pipefail
cd "$(dirname "$0")"

APP_NAME="KWEngine"
VERSION="1.0"
BUILD_DIR="$PWD/build"
DMG_NAME="${APP_NAME}-${VERSION}.dmg"

# 若 xcodebuild 指向了 Command Line Tools，请先：
#   sudo xcode-select -s /Applications/Xcode.app

# 全量干净重建：清掉旧产物，确保新代码 / 新图标 / 资产目录全部生效
echo "▸ Cleaning previous build …"
rm -rf "$BUILD_DIR"
xcodebuild -project KWEngine.xcodeproj -target "$APP_NAME" -configuration Release clean >/dev/null 2>&1 || true

echo "▸ Building Release (clean) …"
xcodebuild -project KWEngine.xcodeproj \
  -target "$APP_NAME" \
  -configuration Release \
  SYMROOT="$BUILD_DIR" \
  OBJROOT="$BUILD_DIR" \
  build | tail -5

APP_PATH="$BUILD_DIR/Release/$APP_NAME.app"
[ -d "$APP_PATH" ] || { echo "✗ Build failed: $APP_PATH not found" >&2; exit 1; }

echo "▸ Staging DMG contents …"
STAGING="$(mktemp -d)"
cp -R "$APP_PATH" "$STAGING/"
ln -s /Applications "$STAGING/Applications"

echo "▸ Creating $DMG_NAME …"
# 若上一版 DMG 还挂载着，先弹出，避免同名卷混淆
hdiutil detach "/Volumes/$APP_NAME" >/dev/null 2>&1 || true
rm -f "$DMG_NAME"
hdiutil create -volname "$APP_NAME" -srcfolder "$STAGING" -ov -format UDZO "$DMG_NAME" >/dev/null
rm -rf "$STAGING"

echo "✓ Done: $PWD/$DMG_NAME  (built $(date '+%Y-%m-%d %H:%M'))"
echo "  注意：app 为本地 ad-hoc 签名。分发给他人时，对方首次打开需右键 →「打开」，"
echo "  或执行: xattr -d com.apple.quarantine /Applications/$APP_NAME.app"
echo "  公开分发需 Developer ID 签名 + notarytool 公证。"
