# HRC 4.1 — Installation guide

HRC turns ONE historical recipe into a modern technical dossier. This package runs on **Claude, ChatGPT, Gemini and DeepSeek**.
Pick your AI below. Total setup time: about 2 minutes.

## What you get on each AI

| AI | Setup | Numbers computed by | Confidence cap |
|---|---|---|---|
| Claude (Claude Code, Claude.ai Skills) | Native skill | Python engine (deterministic, `sig` hash) | none |
| ChatGPT | Custom GPT (or paste) | Python engine if Code Interpreter is on, else manual | none / MEDIUM |
| Gemini | Gem (or paste) | Manual procedure (no code tool) | MEDIUM |
| DeepSeek | Paste in chat | Manual procedure (no code tool in the chat) | MEDIUM |

"Manual" = the AI follows the written formulas in `FALLBACK.md` step by step. The dossier says `python=false` and `Manual Fallback`.
Results are still structured and honest about missing data, but arithmetic by an AI can contain small errors. For auditable numbers use Claude, or ChatGPT with Code Interpreter.

## Folder map

```
hrc/
  SKILL.md  KNOWLEDGE.md  FALLBACK.md  scripts/hrc_engine.py   <- Claude skill (use as is)
  platforms/
    chatgpt/   INSTRUCTIONS.md  RULES.md  KNOWLEDGE.md  FALLBACK.md  hrc_engine.py
    gemini/    INSTRUCTIONS.md  KNOWLEDGE.md  FALLBACK.md
    deepseek/  BUNDLE_NOEXEC.md  BUNDLE_EXEC.md  hrc_engine.py
```

---

## 1. Claude

**Claude Code / any agent that reads `SKILL.md` folders**
1. Copy the whole `hrc` folder to `~/.claude/skills/hrc` (Windows: `%USERPROFILE%\.claude\skills\hrc`). For one project only: `<project>/.claude/skills/hrc`.
2. Start Claude Code and type `/hrc`, or write: `HRC: analyze this recipe: ...`
3. Python 3.10+ must be installed (no extra packages).

**Claude.ai (web / desktop)**
1. Zip the `hrc` folder (the folder itself must be inside the zip).
2. Settings → Capabilities → enable *Code execution*, then Skills → *Upload skill* → choose the zip.
3. In a chat write: `HRC: analyze this recipe: ...`

If you installed it from Agensi via MCP, nothing else is needed.

## 2. ChatGPT

**Option A — Custom GPT (ChatGPT Plus / Team; best result)**
1. ChatGPT → Explore GPTs → Create → *Configure*.
2. *Instructions*: paste the full content of `platforms/chatgpt/INSTRUCTIONS.md`.
3. *Knowledge*: upload `RULES.md`, `KNOWLEDGE.md`, `FALLBACK.md`.
4. For exact computation: enable *Code Interpreter* and also upload `hrc_engine.py`. Without it the GPT works in manual mode.
5. Save, then paste your recipe.

**Option B — any plan, no GPT**
Open a new chat, paste the full content of `platforms/deepseek/BUNDLE_NOEXEC.md` as the first message, then send your recipe in the next message.
This runs in manual mode. For exact computation use Option A with Code Interpreter.

## 3. Gemini

**Option A — Gem**
1. gemini.google.com → Explore Gems → New Gem.
2. *Instructions*: paste the full content of `platforms/gemini/INSTRUCTIONS.md`.
3. *Knowledge*: upload `KNOWLEDGE.md` and `FALLBACK.md` from `platforms/gemini/`.
4. Save, open the Gem, paste your recipe.

**Option B — no Gem**
New chat, paste `platforms/deepseek/BUNDLE_NOEXEC.md` as the first message, then send your recipe.

Gemini web has no code tool for this skill: it runs in manual mode.

## 4. DeepSeek

1. Open a **new** chat at chat.deepseek.com (turn *DeepThink* on if available: it follows long rules better).
2. Paste the full content of `platforms/deepseek/BUNDLE_NOEXEC.md` as the first message. If the message is too long, attach the file instead and write "Follow the attached file as your instructions."
3. Send your recipe in the second message.

Via API with your own code runner: use `BUNDLE_EXEC.md` as the system prompt and put `hrc_engine.py` in the working directory.

---

## How to use it (all AIs)

Send **one** recipe per chat. Best input:
1. The historical recipe text (any language, any period).
2. Optional: comparable recipes, bibliographic references, historical measure tables of the place and period.

Tips
- Use a low temperature (0.0–0.2) where the AI lets you set it.
- Unknown values stay `DATA UNKNOWN`: this is intended, the tool never invents measures.
- The answer is the dossier only, written in your language. The `State` block at the end is the audit record.
- To audit a dossier from any AI (needs Python): `python hrc_engine.py --check dossier.txt`.

## Troubleshooting

| Problem | Fix |
|---|---|
| Reply is only `LINT_ERROR: KNOWLEDGE_MISSING` | The AI could not read the knowledge. ChatGPT/Gemini: re-upload the Knowledge files. Otherwise use the paste bundle (`BUNDLE_NOEXEC.md`). |
| Reply is `LINT_ERROR: <other>` | The recipe input broke a rule (for example an unreadable measure). Add the measure table or a clearer text. |
| AI adds comments before/after the dossier | Start a new chat; instructions were not loaded first. |
| Pasted text cut off | Attach the bundle as a file instead of pasting. |
| Numbers differ between runs (manual mode) | Expected without the engine. Use Claude or ChatGPT + Code Interpreter. |
