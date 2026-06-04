# kw-engine 手把手教程(零基础)

这份教程假设你**从没用过命令行**,也**没用过 Claude Code**。跟着做,大约 20 分钟你就能让它帮你读论文、攒方法、推进自己的研究项目。

可以用 **Claude、Kimi、或 DeepSeek** 任意一个模型——下面都会讲到。

---

## 0. 它到底能帮你做什么

一句话:**你给它论文,它帮你把"为什么这个方法有效"提炼成可复用的卡片;以后你遇到新问题,按问题的结构去搜,就能找到能用的方法和它背后的道理。**

更进一步:你带着**自己的研究想法 + 一堆论文**(哪怕不够),它能帮你:
- 把想法拆成"问题的结构"
- 看看你的论文覆盖了哪些、还缺哪些
- 提议该补读哪些论文
- 最后拼出一个**每个决策都有出处**的方案草案

---

## 1. 准备:你需要什么

- 一台电脑(Mac、Windows、或 Linux 都行)
- 一个 AI 模型账号,**三选一**:
  - Claude(Anthropic 账号),或
  - Kimi(月之暗面 / Moonshot 的 API key),或
  - DeepSeek(深度求索的 API key)

> Kimi 和 DeepSeek 的 API key 在它们各自的开放平台网站注册后获取,通常需要充一点点钱(读几十篇论文也就几块钱)。

---

## 2. 第一步:装 Claude Code

**Claude Code 是一个"外壳"程序,kw-engine 跑在它里面。** 它本身能接 Claude、Kimi、DeepSeek 任意一个。

### 2.1 先装 Node.js
打开浏览器到 <https://nodejs.org>,下载 **LTS** 版本,一路点"下一步"装好。

### 2.2 打开"终端"
- **Mac**:按 `Command + 空格`,输入 `Terminal`,回车。
- **Windows**:开始菜单搜 `PowerShell`,打开。

(终端就是一个能打字给电脑下命令的黑框。别怕,你只需要复制粘贴。)

### 2.3 装 Claude Code
在终端里**粘贴这一行,回车**:

```bash
npm install -g @anthropic-ai/claude-code
```

等它跑完(可能要一两分钟)。

---

## 3. 第二步:接入你的模型(三选一)

Claude Code 默认连 Claude。如果你用 Kimi 或 DeepSeek,需要告诉它"改连这家"。最省事的办法是写进一个配置文件,**一次配好,以后不用管**。

在终端里打开配置文件(任选一个编辑器,这里用最简单的):

```bash
mkdir -p ~/.claude
open ~/.claude/settings.json     # Mac;Windows 用 notepad %USERPROFILE%\.claude\settings.json
```

然后按你的情况,把下面对应的内容粘进去、保存:

### 用 Claude(原生)
不用配。跳过这一步。

### 用 Kimi
```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.moonshot.cn/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "把你的-Kimi-key-粘到这里"
  }
}
```

### 用 DeepSeek
```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "把你的-DeepSeek-key-粘到这里"
  }
}
```

> DeepSeek 会自动把"强模型/弱模型"映射到它的对应型号,所以 kw-engine"便宜模型读、强模型想"的分工依然有效,省钱。

保存关闭。**接入完成。**

---

## 4. 第三步:装 kw-engine

回到终端,粘贴这三行(一行一行来,每行回车):

```bash
# 1) 装一个叫 uv 的工具(用来装 Python 程序)
curl -LsSf https://astral.sh/uv/install.sh | sh
# 2) 装 kw-engine 引擎
uv tool install git+https://github.com/chenpg2/kw-engine
# 3) 装 Claude Code 插件(让 Claude 会用这个引擎)
claude plugins marketplace add chenpg2/kw-engine
claude plugins install kw-engine@kw-engine
```

> Windows 上第 1 行换成:`powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`

**装好了。** 以后你只跟 Claude 对话,不用再碰这些命令。

---

## 5. 第四步:开始用(跟着案例做)

下面是一个完整的小案例。**你要做的只有一件事:打开 Claude Code,然后像聊天一样打字。** 引擎的活儿都是 Claude 替你干,它会把结果给你看。

先在终端进入一个你想放资料的文件夹,然后启动 Claude Code:

```bash
mkdir ~/我的研究 && cd ~/我的研究
claude
```

现在你进入了对话界面。下面每一步,**「你说」就是你打的字,「会发生」是你会看到的**。

### 第 1 步:建一个知识库

> **你说:** 在这里建一个知识库。

**会发生:** Claude 初始化好文件夹结构,告诉你"知识库已就绪"。(这一步一辈子做一次。)

### 第 2 步:喂它一篇论文

> **你说:** 处理这篇论文:https://arxiv.org/abs/2304.04740

**会发生:** Claude 自动下载 PDF → 读它 → 提炼出几条"原则"卡片,然后把学到的东西列给你看(每条原则:什么时候适用、用什么机制、为什么有效)。

多喂几篇就重复这一步,换链接就行。论文不够也没关系,下一步会帮你发现缺口。

### 第 3 步:问它你们知道了什么

> **你说:** 我们现在关于"受约束的生成模型"知道些什么?

**会发生:** Claude 按"问题结构"检索,把匹配的机制 + 为什么有效列给你,而不是甩一堆原文。

### 第 4 步(重头戏):推进你自己的项目

> **你说:** 我想设计一个能处理"成分数据(加起来=1)"的生成模型,这是我手上的几篇论文。帮我捋一下该怎么做。

**会发生:** Claude 启动**问题驱动循环**,带你走:
1. 把你的想法拆成"问题的结构特征",**先跟你确认**对不对;
2. 吸收你给的论文;
3. 给你一张**覆盖图**:哪些子问题已经有现成机制、哪些还是**空白**;
4. 针对空白,**提议该补读哪些论文**——你点头它就去下载吸收;
5. 把命中的原则拼成一个**方案草案**,每个决定都标注"这一步依据哪条原则",还没着落的标红;
6. 把方案、依据、下一步**写进你的项目文件夹**,下次打开能接着干。

### 第 5 步:继续迭代

> **你说:** 把第 3 条空白补上,然后更新方案。

**会发生:** Claude 提议论文 → 你选 → 它吸收 → 重新检查覆盖 → 更新你的方案。**读得越多,方案越锐利。**

---

## 6. 卡住了怎么办

| 现象 | 解决 |
|---|---|
| 终端提示 `command not found: claude` | Node.js 没装好,或要重开一个终端窗口 |
| 终端提示 `command not found: kw` 或 `uv` | 重开终端;还不行就重跑第 4 步第 1、2 行 |
| Claude 回复报错、连不上模型 | 检查 `~/.claude/settings.json` 里的 key 有没有贴对、有没有多余空格 |
| 下载论文失败 | 付费墙论文下不了;把 PDF 自己下好放进项目的 `paper/` 文件夹,再跟 Claude 说"处理 paper 文件夹里的 xxx" |
| 不想敲命令 | 在对话里直接输入 `/kw` 会弹出一个引导菜单 |

---

## 7. 接下来

- 想了解它**为什么能越用越聪明**(自我进化的原理)、或想用命令行脚本化:看 [README](../README.zh-CN.md)。
- 想为不同课题分开建库:跟 Claude 说"把我的 XX 知识库注册成 microbiome",以后说"切到 microbiome 知识库"即可。

有问题就直接问 Claude——它知道这个工具怎么用。
