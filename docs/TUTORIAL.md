# kw-engine Step-by-Step Tutorial (Zero Experience)

This tutorial assumes you've **never used a terminal** and **never used Claude Code**. Follow along and in about 20 minutes you'll have an AI that reads papers for you, distills reusable methods, and helps push your research forward.

Works with **Claude, Kimi, or DeepSeek** — all three are covered below.

---

## 0. What it actually does for you

In one sentence: **you give it papers, it distills "why this method works" into reusable cards; later, when you face a new problem, you search by the problem's *structure* and get back a method that fits — plus why it works.**

Even better: bring **your own research idea + a pile of papers** (even if they're not enough), and it can:
- Decompose your idea into its structural axes
- Show which axes your papers already cover and which are still **gaps**
- Suggest papers to fill those gaps
- Assemble a **draft design where every decision cites its source**

---

## 1. What you need

- A computer (Mac, Windows, or Linux)
- An AI model account — **pick one**:
  - Claude (Anthropic account), or
  - Kimi (Moonshot API key), or
  - DeepSeek (DeepSeek API key)

> Kimi and DeepSeek API keys are obtained from their respective platform websites after registration. They usually require a small top-up (processing dozens of papers costs just a few cents).

---

## 2. Step one: install Claude Code

**Claude Code is the shell program that kw-engine runs inside.** It can connect to Claude, Kimi, or DeepSeek.

### 2.1 Install Node.js first
Open your browser to <https://nodejs.org>, download the **LTS** version, and click through the installer.

### 2.2 Open a terminal
- **Mac**: press `Command + Space`, type `Terminal`, press Enter.
- **Windows**: search the Start menu for `PowerShell` and open it.

(A terminal is just a text window where you type commands for the computer. Don't worry — you'll just copy and paste.)

### 2.3 Install Claude Code
**Paste this line into the terminal and press Enter:**

```bash
npm install -g @anthropic-ai/claude-code
```

Wait for it to finish (a minute or two).

---

## 3. Step two: connect your model (pick one)

Claude Code connects to Claude by default. If you're using Kimi or DeepSeek, you need to tell it to connect there instead. The easiest way is to write it into a config file — **set it once, never touch it again**.

Open the config file in your terminal:

```bash
mkdir -p ~/.claude
open ~/.claude/settings.json     # Mac; on Windows use: notepad %USERPROFILE%\.claude\settings.json
```

Then paste the content that matches your situation, and save:

### Using Claude (native)
No config needed. Skip this step.

### Using Kimi
```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.moonshot.cn/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "paste-your-Kimi-key-here"
  }
}
```

### Using DeepSeek
```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "paste-your-DeepSeek-key-here"
  }
}
```

> DeepSeek automatically maps "strong model / cheap model" to its own tiers, so kw-engine's "cheap model reads, strong model thinks" split still works — and saves money.

Save and close. **Connection complete.**

---

## 4. Step three: install kw-engine

Back in the terminal, paste these lines (one at a time, press Enter after each):

```bash
# 1) Install uv (a tool for installing Python programs)
curl -LsSf https://astral.sh/uv/install.sh | sh
# 2) Install the kw-engine itself
uv tool install git+https://github.com/chenpg2/kw-engine
# 3) Install the Claude Code plugin (teaches Claude how to use the engine)
claude plugins marketplace add chenpg2/kw-engine
claude plugins install kw-engine@kw-engine
```

> On Windows, replace line 1 with: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`

**Done.** From now on you just talk to Claude — no more commands.

---

## 5. Step four: start using it (follow the example)

Here's a complete mini-walkthrough. **All you do is: open Claude Code and type like you're chatting.** The engine does the work; Claude shows you the results.

First, in the terminal, go to a folder where you want to keep your research, then launch Claude Code:

```bash
mkdir ~/my-research && cd ~/my-research
claude
```

Now you're in the chat interface. For each step below, **"You say" is what you type; "What happens" is what you'll see**.

### Step 1: Create a knowledge base

> **You say:** Set up a knowledge base here.

**What happens:** Claude scaffolds the folder structure and tells you "knowledge base is ready." (You do this once, ever.)

### Step 2: Feed it a paper

> **You say:** Process this paper: https://arxiv.org/abs/2304.04740

**What happens:** Claude downloads the PDF, reads it, distills a few "principle" cards, and shows you what it learned (each principle: when it applies, what mechanism, why it works).

Feed more papers by repeating this step with different links. Not enough papers? That's fine — the next step helps you find the gaps.

### Step 3: Ask what you know

> **You say:** What do we know about "constrained generative models"?

**What happens:** Claude searches by problem structure and lists matching mechanisms + why they work — not a wall of raw text.

### Step 4: Sharpen your research question (optional but recommended)

Before diving into a technical design, it's worth checking: *is this even a good question?*

> **You say:** Is this a good research question? I think community state types (CSTs) for vaginal microbiome classification are outdated — the taxonomy resolution is too low and the discrete types miss the continuous spectrum. Help me sharpen this.

**What happens:** Claude runs a **question-sharpening loop** that:
1. Pressure-tests your idea against seven criteria (Does it matter? Is it specific enough? Are there rival hypotheses? Can it be falsified? Can you pilot it in 2 weeks? Does a negative result still teach something? Is it grounded in evidence?);
2. Rewrites vague ideas into a real testable question;
3. Plays the **harshest reviewer** and hits you with the strongest objection;
4. Produces a **Question Card** — a one-page summary of the question, stakes, competing hypotheses, falsification conditions, and best next action.

Then Claude asks: *"The question is sharpened. Want to use /kw-explore to build a technical route? Or stop at this card?"*

- Say **yes** → continues to Step 5 below.
- Say **no** → keep the card for a proposal draft or lab discussion.

> You can skip this step and go straight to Step 5 if you already have a clear, well-formed question.

### Step 5 (the main event): Push your own project forward

> **You say:** I want to design a generative model for compositional data (sums to 1). Here are some papers I have. Help me figure out how to approach this.

**What happens:** Claude starts the **problem-driven loop** and walks you through:
1. Decomposing your idea into structural features, **confirming with you** first;
2. Absorbing your papers;
3. Showing a **coverage map**: which sub-problems already have proven mechanisms, which are still **gaps**;
4. For each gap, **suggesting papers to read** — you pick, it fetches and absorbs;
5. Assembling a **draft design** where every decision cites the principle it rests on, with unsupported parts flagged;
6. Writing the design, rationale, and next steps **into your project folder** so you can pick up where you left off.

### Step 6: Keep iterating

> **You say:** Fill in gap #3 and update the design.

**What happens:** Claude proposes papers, you choose, it absorbs, rechecks coverage, updates your design. **The more you read, the sharper the design gets.**

---

## 6. Stuck? Troubleshooting

| Symptom | Fix |
|---|---|
| Terminal says `command not found: claude` | Node.js wasn't installed properly, or reopen a new terminal window |
| Terminal says `command not found: kw` or `uv` | Reopen the terminal; if that doesn't help, re-run Step 4 lines 1-2 |
| Claude errors out or can't reach the model | Check that the key in `~/.claude/settings.json` is pasted correctly with no extra spaces |
| Paper download fails | Paywalled papers can't be fetched; download the PDF yourself into the project's `paper/` folder, then tell Claude "process the paper xxx in the paper folder" |
| Don't want to type commands | Type `/kw` in the chat to get a guided menu |

---

## 7. What's next

- Want to understand **why it gets smarter over time** (the self-evolution mechanism), or want to script it from the command line? See the [README](../README.md).
- Want separate knowledge bases for different research topics? Tell Claude "register my XX knowledge base as microbiome," then later say "switch to the microbiome knowledge base."

Questions? Just ask Claude — it knows how to use this tool.
