# KW Engine — Windows 版 (.exe) / cross-platform desktop app

与 `macapp/` 的 SwiftUI 版功能完全对齐的 **Python + PySide6** 实现，可打包为单文件 `KWEngine.exe`。同样**不改动原项目**：沿用同一套磁盘格式（`memory/`、`index.json`、`.kw/index.db`），同一个知识库可在 Mac 版、Windows 版、`kw` CLI 与 Claude Code 插件之间无缝共用。LLM 的协议（OpenAI 兼容 / Anthropic）、API 地址、模型 ID、密钥全部在「设置」页配置，密钥存入 Windows 凭据管理器。

> Functional parity with the macOS app: status dashboard with pipeline chart, papers (import PDF → L1 read → L2 distill), principles browser, structure search + LLM Ask, L3 synthesis, verify/reindex, Pantone theme (light/dark), bilingual UI. The YAML layer *is* PyYAML — the same library the CLI uses — so on-disk interop is exact by construction. The Unix-only `fcntl` lock from the original package is replaced with a portable lock, which is why this app ships its own storage module instead of importing `kw_engine`.

## 直接运行（无需打包，三平台皆可）

```bash
cd winapp
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -e .
python -m kwengine_app
```

## 打包成 exe

**方式一 — 本地 Windows 机器（一键）**：双击 `build_exe.bat`（需已安装 Python 3.10+ 并勾选 Add to PATH）。产物：`winapp/dist/KWEngine.exe`（单文件，含图标，免安装）。

**方式二 — GitHub Actions（无需 Windows 机器）**：把 `ci/build-windows.yml` 复制到仓库的 `.github/workflows/` 后 push；到 Actions 页面下载 `KWEngine-windows` 产物。

> 提示：未签名的 exe 首次运行可能被 SmartScreen 拦截 — 点「更多信息 → 仍要运行」。正式分发需代码签名证书。

## 配置 LLM（设置页）

| 提供方 | 协议 | Base URL | 强模型 / 快模型 |
|---|---|---|---|
| DeepSeek | OpenAI 兼容 | `https://api.deepseek.com` | `deepseek-reasoner` / `deepseek-chat` |
| Kimi (Moonshot) | OpenAI 兼容 | `https://api.moonshot.cn/v1` | `kimi-k2-0905-preview` / `moonshot-v1-8k` |
| Ollama（本地） | OpenAI 兼容 | `http://localhost:11434/v1` | 你加载的模型 |
| Anthropic | Anthropic | `https://api.anthropic.com` | `claude-sonnet-4-6` |

强模型负责蒸馏/综合/回答，快模型负责读取/结构抽取（留空则复用强模型）— 与 kw-engine 的 read-cheap / distill-strong 路由一致。端点实时预览，「测试连接」一键验证。

## 结构

```
winapp/
  src/kwengine_app/
    models.py  store.py  templates.py     # 存储基底（markdown 为真相；与 CLI 字节兼容）
    llm.py  prompts.py  pipeline.py       # LLM 客户端 + L1/L2/L3/Ask 流水线
    theme.py  settings.py  l10n.py        # 潘通色主题 / 设置持久化 / 双语
    ui/                                   # PySide6 界面（六个页面 + 组件 + 工作线程）
  assets/icon.ico  icon.png               # 与 Mac 版同源的应用图标
  kwengine.spec  build_exe.bat            # PyInstaller 打包
  ci/build-windows.yml                    # GitHub Actions 模板
```

MIT — 与上游项目一致。
