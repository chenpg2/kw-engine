<div align="center">

<img src="banner.png" alt="kw-engine banner" width="100%">

# kw-engine

**别再重读论文。开始复用"为什么有效"。**

一个方法学进化引擎:把文献蒸馏成可迁移的解题原则。当你遇到一个新问题,按它的*结构*检索,拿回一个能用的机制——外加它为什么有效、何时失效。

[![CI](https://github.com/chenpg2/kw-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/chenpg2/kw-engine/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Tests](https://img.shields.io/badge/tests-52%20passing-brightgreen)
![Types](https://img.shields.io/badge/mypy-strict-blue)
![License](https://img.shields.io/badge/license-MIT-green)

[English](README.md) · **简体中文**

</div>

---

## 它解决什么问题

你读了一篇论文,提取了一个巧妙的技巧,然后忘了。半年后你遇到一个问题,*同一个技巧*正好能解——但它来自另一个领域、用了不同术语,而你的笔记是一堆 PDF。你的瓶颈从来不是"找不到论文",而是**跨领域复用底层方法**。

kw-engine 把这件事本身当作要解决的问题。

## 它做什么

它把文献通过三层蒸馏,剥离领域、保留可迁移的逻辑:

```
 论文 PDF
   │
   ├─  L1  忠实提取    原样记录论文说了什么(带章节定位,不解读)
   │
   ├─  L2  抽象        剥离领域,留下可迁移的内核:
   │                     problem-signature   ·  何时适用(问题的结构特征)
   │                     ↔ mechanism + math  ·  做什么
   │                     ↔ rationale         ·  为什么 结构 ↔ 机制 成立
   │
   └─  L3  综合        把原则聚成设计空间地图,暴露矛盾与 GAP——你的下一份阅读清单
```

然后是回报:

```
新问题  →  按它的结构检索  →  匹配的机制 + 原理 + 失效边界
```

它不是文本上的检索索引,而是一个从*经验结果*到*可复用解题策略*的编译器。(为什么有效的数学,见[文末](#底层为什么这两个环会收敛)。)

## 它和别的有什么不同

|  | 检索回什么 | 按什么索引 |
|---|---|---|
| **RAG / 向量检索** | 文本块 | 表层语义 |
| **Zotero / 文献管理** | 引用与 PDF | 元数据、标签 |
| **技能库**(如 Voyager) | 可执行任务代码 | 任务名 |
| **kw-engine** | **机制 + 为什么有效 + 何时失效** | **问题结构** |

---

## 快速上手

### 1. 安装 CLI

```bash
uv tool install git+https://github.com/chenpg2/kw-engine   # 得到 kw 命令
```

### 2.(可选)安装 Claude Code 插件

插件提供推理层——`/kw` skill 和五个子 agent,替你读取、蒸馏、综合。在终端运行:

```bash
claude plugins marketplace add chenpg2/kw-engine
claude plugins install kw-engine@kw-engine
```

> `kw` CLI 是确定性底座;插件是驱动它的 LLM 推理。完整体验两者都要;只用 CLI 也能手动跑通。

### 3. 六十秒上手

```bash
kw init                                    # 初始化工作区(memory/、.kw/、process/、paper/)
kw fetch 2304.04740                        # 获取 PDF(开放获取回退链 + 校验)
kw add-paper 2304.04740 --title "Flow Matching for Generative Modeling"
kw add-principle \
  --title "把困难的动力学优化降为静态耦合 + 对桥的回归" \
  --sig "未配对的边缘快照" --sig "连续时间生成过程" \
  --math "optimal-transport" --math "conditional-flow" \
  --mechanism "先解一个静态耦合,再把向量场回归到闭式条件桥上。" \
  --rationale "动态最优解分解为逐对的桥,所以坍缩成一个耦合问题。" \
  --regime "需要可配对或可 OT 耦合的边缘;N 足够大以估计耦合" \
  --prediction "拉直耦合可在不重训的情况下减少采样步数" \
  --boundaries "如果桥族与真实条件过程不匹配则失效" \
  --prov "2304.04740 §3.2"

kw search "optimal transport dynamics"     # ← 回报:按问题结构检索
kw verify                                  # 校验完整性(溯源、链接、必填字段)
kw ui                                      # 可选:终端 UI 里浏览/检索/校验
```

### 让 Claude Code 来驱动

装了插件后,你从不手动编辑记录——skill 编排整个循环,用便宜模型读取、强模型抽象:

```
/kw          # 检测状态,给出菜单,运行 fetch → read → distill → synthesize → verify
/kw-init     # 用自然语言初始化工作区
```

---

## 知识库:一个库,多个项目

知识库存在一处,任何项目按名称链接,不复制文件。

```bash
# 一次性注册按主题划分的库(存在 ~/.kw/registry.yaml)
kw kb add microbiome  ~/research/microbiome-kb/memory
kw kb add causal      ~/research/causal-inference-kb/memory
kw kb list

# 在任意项目里按名称链接——之后所有 kw 命令都用这个库
cd ~/my-project
kw link microbiome
kw search "simplex dynamics"

# 随时切换主题
kw link causal
kw search "intervention identifiability"
```

`kw link` 写一个小小的 `.kw/config.yaml` 指向共享库。多个项目可同时共享一个知识库。

---

## 它如何自我改进

有两个环。**环 1 是核心**——它是知识进化的方式,只要你吸收论文它就在跑。**环 2 是可选的**——一个 opt-in 增强,用于你想让蒸馏器本身随时间变好的时候。关掉环 2 引擎照样完整运行(你只是不去跑 `kw rubric` 命令而已)。

### 环 1 — 知识扩张(核心,gap 驱动)

`L3 综合`把已知聚成设计空间地图,并计算 **gap**——还没有好机制对应的问题结构。Gap 就是你的下一份阅读清单。每篇新论文被去重、链接进图,所以重新综合会得到*更锐利*的 gap。目标(下一步读什么)由当前状态生成,不是外部塞进来的。

### 环 2 — 蒸馏器变锐(可选,半自动)

*完全跳过它引擎照样工作——蒸馏器只是一直用静态 rubric。* 当你吸收了足够多论文、注意到反复出现、值得一次性修掉的蒸馏错误时,再打开它。

每一次蒸馏失败(抽象泄漏了领域名词、rationale 偏弱、漏了去重)都能变成一条改进 rubric 的规则。这是 [SkillOpt](https://github.com/microsoft/SkillOpt) 式"让失败编辑 skill"的廉价内核,砍掉了训练 harness——因为失败信号本来就由 verifier 免费产生。

**它刻意不是全自动的。** 捕获教训既便宜又安全;改动 live rubric 则被审计关卡守着:

| 步骤 | 命令 | 谁执行 | 为什么 |
|---|---|---|---|
| **捕获** | `kw rubric add` | `/kw` agent,在批次中 | 把一个具体失败变成通用规则(暂存,**不碰** live rubric) |
| **审计** | `kw rubric review` | **你** | Codex 把暂存规则与 live rubric 比对一致性,产出清理后的版本 |
| **提升** | `kw rubric promote` | **你**,看过提案之后 | 把审过的 rubric 换进去;归档旧版,清空队列 |

手动的 `review` + `promote` 就是**验证门**:它们防止 rubric 漂移、膨胀、堆积矛盾。一条坏规则永远不会悄悄进入 live rubric。(想要 Codex 判定为"纯增量"时自动 `--auto` promote?那是计划中的可选项;安全默认保持手动。)

#### 不懂命令行?直接跟 Claude 说

装了插件后,你**一条 `kw` 命令都不用敲**——用大白话驱动环 2,Claude 替你跑工具:

1. **你读论文时**,Claude 自己就把蒸馏教训记下来了。你什么都不用做。
2. **想应用这些教训时**,说一句:
   > *"审一下蒸馏 rubric,把会改动的地方给我看看。"*

   Claude 会跑审计,并用大白话总结提议的改动。
3. **想正式生效**,说一句:
   > *"可以,应用吧。"*

   Claude 把它提升为正式版。它总会先把提议给你看、先问你——live rubric 绝不会悄悄改动。

这就是不用终端的整个环 2:照常读论文,然后偶尔说一句*"审一下规则"*、*"应用吧"*。

---

## CLI 命令参考

| 命令 | 用途 |
|---|---|
| **知识库** | |
| `kw kb add <name> <path>` | 注册一个命名知识库 |
| `kw kb list` / `kw kb remove <name>` | 列出 / 取消注册(不删文件) |
| `kw link <name-or-path>` | 将当前项目链接到某个知识库 |
| **工作区** | |
| `kw init [dir]` | 初始化一个新工作区 |
| `kw status` | 计数、待处理论文、综合是否过期 |
| `kw ui` | 终端 UI:浏览、检索、校验、重建索引 |
| `kw reindex` | 从 markdown 重建 `index.json` + SQLite |
| `kw verify` | 校验完整性不变量 |
| **论文与原则** | |
| `kw fetch <id\|doi\|title>` | 获取 PDF(OA 回退链)+ 校验 + 登记 |
| `kw add-paper <id>` | 登记一篇论文 |
| `kw add-principle …` | 分配 `P-####`,写入原则,更新 index + SQLite |
| `kw add-link <from> <to> <type>` | 建立原则间的链接(`generalizes`/`contrasts`/`composes`/…) |
| `kw search "<query>"` | 按 problem-signature / math-basis 检索原则 |
| **自我改进的 rubric**(见[环 2](#环-2--蒸馏器变锐半自动)) | |
| `kw rubric add --rule … --trigger …` | 把一次失败的教训沉淀成候选规则(暂存) |
| `kw rubric status` | 查看待处理的候选规则数 |
| `kw rubric review` | Codex 审候选 → 产出清理后的 rubric |
| `kw rubric promote` | 把审过的 rubric 提升为 live |

---

## 架构

```
 memory/papers/*.md          ┐
 memory/principles/*.md       ├─ 唯一真相源(git 跟踪、人可读)
 memory/synthesis/*.md        ┘
        │  kw reindex
        ▼
 memory/index.json     (可 diff 的目录投影,提交进 git)
 .kw/index.db          (SQLite 查询索引,gitignore,可重建)
```

- **Markdown 是真相。** 索引是派生的——随时可删可重建。
- **原子写入。** 临时文件改名 + 对索引加 `flock`;不会写一半,不会 pid 碰撞。
- **不静默回退。** 校验失败就报错;引擎从不写占位记录。
- **两层架构。** LLM agent 负责推理,类型化 Python CLI 负责记账(便宜模型读取,强模型抽象)。

---

## 底层:为什么这两个环会收敛

给好奇的人——"self-evolving"背后的机制,三步。

**1 · 蒸馏是一个商映射。** L2 抽象把具体方法 `m` 映到一个等价类,等价关系是*"相同问题结构、相同机制"*:

```
φ :  具体方法  ──►  ( problem_signature , math_basis , mechanism , rationale )
```

两个来自不相关领域、结构*相同*的方法映到同一类——这就是为什么一个微生物组技巧和一个扩散模型技巧能聚到一起。φ 折叠**领域距离**、暴露**结构距离**。迁移就是这个商映射在按设计工作。

**2 · 已知集生成自己的目标。** 在当前 principle 集 `P` 上,综合定义一张覆盖图;**gap** 就是欠覆盖的区域。gap 是*从 `P` 算出来的*——内生目标,不是外部 prompt。

**3 · 这个环是闭合且单调的。**

```
 P_n  ──综合──►  gaps(P_n)  ──获取 + 蒸馏──►  P_{n+1} = P_n ⊕ 新原则
```

`⊕` 是去重-链接合并:新原则要么扩展 `P`,要么挂到已有的上。图只增不减,所以在更丰富的 `P_{n+1}` 上重新综合会得到更锐利的 gap。这个反馈——知识状态 → 下一个目标 → 更丰富的状态——就是 self-evolving 里的"self"。本质上是**设计空间上的 active learning**。

> **诚实的边界。** kw-engine 是一个工具和方法,不是跑过基准的研究结论。它还没证明"按结构检索"在某个下游任务上优于 RAG——那需要对照实验。它今天给你的,是一个有纪律、可复现的底座,用来构建和查询可迁移方法学库,把推理与确定性存储干净地分离。

---

## 开发

```bash
uv sync
uv run pytest -v          # 52 个测试
uv run ruff check .       # lint
uv run mypy src/          # 严格类型检查
```

## 许可证

MIT © 2026
