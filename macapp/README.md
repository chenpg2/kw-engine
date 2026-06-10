# KW Engine.app — native macOS app

A native SwiftUI Mac app built on the **kw-engine** design: *distill → abstract → synthesize → search by problem structure.* It does not modify the existing project — it reuses the same on-disk knowledge-base format, so one workspace is shared between this app, the `kw` CLI, and the Claude Code plugin.

> 一个基于 kw-engine 设计、思想与逻辑的原生 macOS 应用。**不改动原项目**：完全沿用同一套磁盘格式（`memory/papers`、`memory/principles`、`index.json`、`.kw/index.db`），因此同一个知识库可被本 app、`kw` CLI 与 Claude Code 插件共享。LLM 的 API 地址、模型 ID、密钥全部由用户在「设置」中自行配置。

The UI is bilingual (中文 / English) and follows the system language.

---

## What it does (faithful to the engine)

The app implements the same four layers as the CLI, with the LLM doing the reasoning and a deterministic Swift store owning the files:

| Engine stage | In the app | Writes |
|---|---|---|
| **L1 — faithful read** (`kw-reader`) | *Read (L1)* on a paper: PDFKit extracts text, the LLM produces a faithful record with section locators, no abstraction | `memory/papers/<id>.md`, status → `L1` |
| **L2 — abstraction** (`kw-distiller`) | *Distill (L2)*: strips the domain, emits transferable principles `problem_signature ↔ mechanism+math ↔ rationale` (+ data_regime / falsifiable_prediction / boundaries), dedups & links against existing principles | `memory/principles/P-####.md`, `counters.principle++`, status → `complete` |
| **L3 — synthesis** (`kw-synthesizer`) | *Synthesize (L3)*: clusters principles into a design-space map, surfaces contradictions and gaps, applies discovered links | `memory/synthesis/{design-space,contradictions,gaps}.md` |
| **Search by structure** (`kw search`) | *Search / Ask*: keyword mode is the exact deterministic substring search over `problem_signature` + `math_basis`; Ask mode extracts a problem's structure, searches, then composes matched mechanism + rationale + when-it-breaks | read-only |

It also mirrors `kw status`, `kw verify` (SCHEMA §6 invariants), and `kw reindex` (rebuild `index.json` + SQLite from markdown — *markdown is truth*).

The engine's core rules are preserved: **markdown is truth**, SQLite + `index.json` are derived; paper id = PDF filename stem; principle id = `P-####`; and **no silent fallback** — invalid model output is rejected and logged in the Run Log, never coerced into the store.

---

## Build & run

Requirements: macOS 13+, Xcode 15 or 16.

```bash
open macapp/KWEngine.xcodeproj
# Select the "KWEngine" scheme → ⌘R
```

No third-party dependencies — only Apple frameworks (SwiftUI, PDFKit, SQLite3, Security/Keychain). The Xcode project uses the synchronized-folder format, so every file under `macapp/KWEngine/` is included automatically.

### Package as a DMG / 打包成 DMG

```bash
bash macapp/build_dmg.sh        # → macapp/KWEngine-1.0.dmg
```

Builds Release via `xcodebuild` and wraps the `.app` (plus an Applications shortcut) with `hdiutil`. Requires full Xcode (if needed: `sudo xcode-select -s /Applications/Xcode.app`).

The app is ad-hoc signed — fine for your own Macs. If you share the DMG, recipients must right-click → Open the first time (or `xattr -d com.apple.quarantine`); public distribution requires a Developer ID certificate + notarization (`xcrun notarytool`).

---

## Configure your LLM (Settings ⌘,)

Everything is user-set; nothing is hard-coded. Two protocols are supported:

**OpenAI-compatible** (`/chat/completions`) — covers most providers and local servers:

| Provider | Base URL | Strong model | Fast model |
|---|---|---|---|
| DeepSeek | `https://api.deepseek.com` | `deepseek-reasoner` | `deepseek-chat` |
| Kimi (Moonshot) | `https://api.moonshot.cn/v1` | `kimi-k2-0905-preview` | `moonshot-v1-8k` |
| Ollama (local) | `http://localhost:11434/v1` | `qwen2.5:32b` | `qwen2.5:7b` |
| LM Studio (local) | `http://localhost:1234/v1` | *(your loaded model)* | *(same)* |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` | `gpt-4o-mini` |

**Anthropic** (`/v1/messages`):

| Provider | Base URL | Model |
|---|---|---|
| Anthropic | `https://api.anthropic.com` | `claude-sonnet-4-6` |

The **strong model** runs distillation / synthesis / answer composition; the **fast model** runs reading and structure-extraction (empty = reuse the strong model). This preserves the engine's *read-cheap / distill-strong* routing. The endpoint is derived deterministically and previewed live, and **Test Connection** verifies it before you commit. The API key is stored in the macOS **Keychain**, never on disk.

---

## Design / 设计

Minimal, premium, Apple-style. Color is **semantic, never decorative**, drawn from a Pantone palette with full light/dark variants (`UI/Theme.swift`):

| Role | Pantone | Hex (light) |
|---|---|---|
| Accent / L1 | **19-4052 Classic Blue** | `#0F4C81` |
| Success / distilled | **17-5641 Emerald** | `#009473` |
| Warning / stale | **1235 C Saffron** | `#E8A317` |
| Error | **485 C Fiery Red** | `#DA291C` |
| Ask / links | **16-1546 Living Coral** | `#E85D4E` |
| math_basis tags | **18-3838 Ultra Violet** | `#5F4B8B` |
| data_regime tags | **3262 C Teal** | `#00897F` |
| Ink / canvas | **Black 6 C / Bright White 11-0601** | `#101820` / `#F4F5F0` |

Components: hairline-bordered cards on a Bright-White canvas, capsule tag chips, tracked uppercase section labels, SF Pro with rounded numerals, and a Swift Charts pipeline bar on the dashboard. The app icon is a Classic-Blue squircle with the brand glyph — three layers distilling into one point — generated at all macOS sizes in `Assets.xcassets`.

## Interop with the CLI

Open any existing `kw` workspace (the folder containing `memory/`) — the app reads it directly. New principles written by the app are picked up by `kw search` / `kw status`, and `kw reindex` and the app's *Rebuild index* are equivalent. The YAML front-matter writer/reader was validated against PyYAML in both directions over ~28,000 fuzz round-trips, so records written by either side parse identically on the other.

## License

MIT — same as the parent project.
