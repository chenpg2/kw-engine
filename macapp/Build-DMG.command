#!/bin/bash
# 双击即可打包 DMG（也可由 Claude 通过屏幕控制触发）
cd "$(dirname "$0")"
bash ./build_dmg.sh
status=$?
echo
if [ $status -eq 0 ]; then
  echo "✅ 完成：DMG 已生成在 macapp 文件夹中。"
else
  echo "❌ 失败（退出码 $status）。"
  echo "   若未安装完整版 Xcode：从 App Store 安装后执行："
  echo "   sudo xcode-select -s /Applications/Xcode.app && sudo xcodebuild -license accept"
fi
read -n 1 -s -r -p "按任意键关闭窗口…"
echo
