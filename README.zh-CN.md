<div align="center">

# kw-engine

**别再重读论文。开始复用"为什么有效"。**

一个**方法学进化引擎**——把文献蒸馏成可迁移的解题原则。当你遇到一个新问题，按它的*结构*检索，拿回一个能用的机制，外加它为什么有效。

[![CI](https://github.com/chenpg2/kw-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/chenpg2/kw-engine/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Tests](https://img.shields.io/badge/tests-41%20passing-brightgreen)
![Types](https://img.shields.io/badge/mypy-strict-blue)
![License](https://img.shields.io/badge/license-MIT-green)

[English](README.md) · **简体中文**

</div>

---

## 它解决什么问题

你读了一篇论文，提取了一个巧妙的技巧，然后忘了。半年后你遇到一个问题，*同一个技巧*正好能解——但它来自另一个领域、用了不同的术语，而你的笔记是一堆 PDF。你的瓶颈从来不是"找不到论文"，而是**跨领域复用底层方法**。

kw-engine 把这件事本身当作要解决的问题。

## 它做什么

它把文献通过三层蒸馏，剥离领域、保留可迁移的逻辑：

```
 论文 PDF
   │
   ├─  L1  忠实提取    原样记录论文说了什么（带章节定位，不解读）
   │
   ├─  L2  抽象        剥离生物/领域，留下可迁移的内核：
   │                     problem-signature   ·  何时适用（问题的结构特征）
   │                     ↔ mechanism + math  ·  做什么（数学机制）
   │                     ↔ rationale         ·  为什么这个结构↔机制的映射成立
   │
   └─  L3  综合        把原则聚成"设计空间地图"，暴露矛盾与空白(gaps)——
                       知识在这里进化
```

然后是回报：

```
新问题出现  →  按它的结构检索  →  匹配的机制 + 原理 + 失效边界
```

## 它和别的有什么不同

|  | 检索回什么 | 按什么索引 |
|---|---|---|
| **RAG / 向量检索** | 文本块 | 表层语义 |
| **Zotero / 文献管理** | 引用与 PDF | 元数据、标签 |
| **技能库**（如 Voyager） | 可执行任务代码 | 任务名 |
| **kw-engine** | **机制 + 为什么有效 + 何时失效** | **问题结构** |

它不是文本上的检索索引——它是一个从*经验结果*到*可复用解题策略*的编译器。

## 亮点

- 🧪 **按结构检索** —— 用问题的形状查询，而不是关键词
- 🧬 **领域剥离的原则** —— 一个微生物组技巧和一个扩散模型技巧，当数学结构匹配时会落到同一个簇
- 🔁 **会进化的知识** —— L3 综合暴露真实的 gap，gap 就是你的下一份阅读清单
- 🪶 **Markdown 是唯一真相源** —— 可 git diff、可审查；SQLite + JSON 都是可重建的派生索引
- ⚛️ **确定性 + 原子写入** —— 每次写入都是临时文件改名 + 文件锁；不会有半写状态
- 🤖 **两层架构** —— LLM agent 负责推理，类型化的 Python CLI 负责记账（便宜模型读取，强模型抽象）
- 🔌 **作为 Claude Code 插件发布** —— `/kw` 编排整个循环；也可以自己驱动 `kw` CLI
- ✅ **生产级底座** —— 41 个测试，`mypy --strict`，`ruff`，Python 3.11–3.13 上 CI

## 安装

```bash
# 作为命令行工具（推荐——直接得到 kw 命令）
uv tool install git+https://github.com/chenpg2/kw-engine

# 或作为项目依赖
uv add git+https://github.com/chenpg2/kw-engine

# 或克隆开发
git clone https://github.com/chenpg2/kw-engine
cd kw-engine && uv sync
```

## 快速上手

```bash
# 1. 在任意项目里初始化工作区
kw init
kw status                                  # 0 篇论文、0 条原则——空引擎

# 2. 获取一篇论文（多源开放获取回退 + PDF 校验）
kw fetch 2304.04740

# 3. 登记并蒸馏（agent 读后填写；也可手动）
kw add-paper 2304.04740 --title "Flow Matching for Generative Modeling"
kw add-principle \
  --title "把困难的动力学优化降为静态耦合 + 对桥的回归" \
  --abstract "当一个定理把动态最优解刻画为简单条件桥的混合时，用耦合 + 闭式回归替换路径优化。" \
  --sig "未配对的边缘快照" --sig "连续时间生成过程" \
  --math "optimal-transport" --math "conditional-flow" \
  --mechanism "先解一个静态耦合，再把向量场回归到闭式条件桥上。" \
  --rationale "动态最小作用量最优解分解为逐对的桥，所以难点坍缩成一个耦合问题。" \
  --regime "需要可配对或可 OT 耦合的边缘；N 足够大以估计耦合" \
  --prediction "拉直耦合可在不重训的情况下减少采样步数" \
  --boundaries "如果桥族与真实条件过程不匹配则失效" \
  --prov "2304.04740 §3.2"

# 4. 回报——按问题结构检索
kw search "optimal transport dynamics"

# 5. 保持诚实
kw verify                                  # 校验溯源、链接、必填字段
```

### 或者让 Claude Code 来驱动

作为插件安装后，直接运行 skill——它会编排 fetch → read → distill → synthesize → verify，并在每一步用正确的模型：

```
/kw          # 检测状态，给出菜单，运行循环——你从不手动编辑任何文件
/kw-init     # 用自然语言初始化工作区
```

## CLI 命令参考

| 命令 | 用途 |
|---|---|
| `kw init [dir]` | 初始化工作区（`memory/`、`.kw/`、`process/`、`paper/`） |
| `kw fetch <id\|doi\|title>` | 通过 OA 回退链获取 PDF + 校验 + 登记 |
| `kw add-paper <id>` | 登记一篇论文（创建记录 + 索引条目） |
| `kw add-principle …` | 分配 `P-####`，写入原则，更新 index + SQLite |
| `kw add-link <from> <to> <type>` | 建立原则间的链接（`generalizes`/`contrasts`/`composes`/…） |
| `kw search "<query>"` | 按 problem-signature / math-basis 检索原则 |
| `kw reindex` | 从 markdown 重建 `index.json` + SQLite |
| `kw verify` | 校验完整性不变量（溯源、链接、必填字段） |
| `kw status` | 计数、待处理论文、综合是否过期 |

## 架构

```
 memory/papers/*.md          ┐
 memory/principles/*.md       ├─ 唯一真相源（git 跟踪、人可读）
 memory/synthesis/*.md        ┘
        │  kw reindex
        ▼
 memory/index.json     （可 diff 的目录投影，提交进 git）
 .kw/index.db          （SQLite 查询索引，gitignore，可重建）
```

- **Markdown 是真相。** 索引是派生的——随时可删可重建。
- **原子写入。** 临时文件改名 + 对索引加 `flock`；不会有 pid 碰撞或写一半。
- **不静默回退。** 校验失败就报错；引擎从不写占位记录。

## 诚实的边界

kw-engine 是一个**工具和方法**，不是一个跑过基准的研究结论。它（目前）并没有证明"按结构检索"在某个下游任务上优于 RAG——那需要一个对照实验。它今天给你的，是一个有纪律、可复现的底座，用来构建和查询可迁移方法学库，并把 LLM 推理与确定性存储干净地分离。

## 开发

```bash
uv sync
uv run pytest -v          # 41 个测试
uv run ruff check .       # lint
uv run mypy src/          # 严格类型检查
```

## 许可证

MIT © 2026
