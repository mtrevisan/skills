# HCR — Historical Cooking Recipe (Claude, Gemini, AI Studio, DeepSeek)

Turns **one** historical recipe (any language, any era) into **one** modern technical dossier: historical and modern ingredient list with computed masses, rheological check, HACCP, procedure in STE100.

Models get the arithmetic of ancient measures wrong and invent values they do not know. This skill moves the numbers out of the model: a deterministic Python engine computes them (same recipe, same result) and a check (`--check`) verifies the output before it is delivered.

## What it is for

- Converting native measures (libbra, oncia, pinch, tankard, "1 1/2 glass"...) into grams, using only the tables you provide or cited web sources. What is not known stays `DATA UNKNOWN`, never invented.
- Identifying every ingredient with a protocol (old spellings are deceptive: variants, dialects, false friends) instead of trusting the similar-looking modern word.
- Producing modern masses from physics (density, projection of ratios), not from history, rounded half-up with decimals per category (solids and fluids 1, spices and salt 2).
- Checking a dossier written by another model: `--check` verifies row format, decimals, names, duplicate rows, round masses.

## Installation (30 seconds)

### 1. Get the skill

<details>
<summary><strong>Claude Code</strong> (updates itself)</summary>

```bash
claude plugin marketplace add mtrevisan/skills
claude plugin install hcr@skills
```

From Claude Code 2.1.275 one line is enough: `/plugin install hcr --marketplace mtrevisan/skills`.

</details>

<details>
<summary><strong>Files only</strong> (manual update)</summary>

Clone the repository and copy the skill folder among Claude's skills:

```bash
git clone --depth 1 https://github.com/mtrevisan/skills.git
mkdir -p ~/.claude/skills
cp -r skills/skills/hcr ~/.claude/skills/hcr
```

To have it in a single project only, copy it to `<project>/.claude/skills/hcr`. To update, repeat `git pull` and the copy.

</details>

### 2. Requirements

Python 3 (standard library only) to run the engine. Without code execution the skill still works with manual calculation (`FALLBACK.md`): confidence is capped at MEDIUM and the dossier states so.

### 3. Use it

Type `/hcr` or ask to analyse a recipe; the skill triggers by itself when faced with a historical recipe. The message must contain:

- the recipe to analyse (e.g. "analyse the recipe of 1502");
- similar recipes, if any: they become the concordance (quotations copied from the input, never from memory);
- the bibliography with the measure tables. If missing, the skill looks them up online and cites URL and page; units without a table (price soldi, "mesura", counts) stay `DATA UNKNOWN`.

For repeatable results set the temperature to 0–0.2 where possible.

## Other platforms (Gemini, AI Studio, DeepSeek)

Only Claude reads `SKILL.md`. For the others, `platforms/` holds the same rules and the same engine, generated from the skill by `build_platforms.py` (edit the skill, never the generated files, then run `py build_platforms.py`). Download the files you need from GitHub and paste or upload them as below.

### Gemini

- **Gem (no code execution).** Create a Gem. *Instructions*: paste `platforms/gemini/INSTRUCTIONS.md`. *Knowledge*: upload `platforms/gemini/KNOWLEDGE.md` and `platforms/gemini/FALLBACK.md`. Numbers follow the manual calculation: `python=false`, confidence capped at MEDIUM, and the dossier says so.
- **Gemini CLI (code execution, exact numbers).** It reads the skill as it is:

```bash
gemini skills install https://github.com/mtrevisan/skills.git --path skills
```

### Google AI Studio (Code execution on)

1. Turn on **Code execution**; temperature 0–0.2.
2. *System instructions*: paste `platforms/aistudio/SYSTEM_INSTRUCTIONS.md`.
3. First message: paste `platforms/aistudio/ENGINE_MESSAGE.md` (the engine source). The model must not answer it.
4. Second message: the input.

The code sandbox cannot read files and keeps no state, so every code call starts with the engine source copied from the first message. This costs tokens and depends on an exact copy; if the copy is wrong, the dossier carries `python:false` and follows the manual calculation.

### DeepSeek

- **Web chat (no code).** First message: paste `platforms/deepseek/BUNDLE_NOEXEC.md`. Second message: the input. Manual calculation, as for the Gem.
- **API or agent harness that runs code.** System prompt: `platforms/deepseek/BUNDLE_EXEC.md`; put `platforms/deepseek/hcr_engine.py` in the working directory.

Not verified on the live Gemini app, AI Studio or DeepSeek: limits and sandbox behaviour are taken from the HCR 4.1 notes.

## What is inside

```
.claude-plugin/plugin.json
skills/hcr/SKILL.md                  rules and pipeline (single source)
skills/hcr/KNOWLEDGE.md              metrology, limits, linter, engine schema
skills/hcr/FALLBACK.md               manual calculation, only without code
skills/hcr/scripts/hcr_engine.py     engine + check (stdlib)
skills/hcr/scripts/hcr_selftest.py   tests (development only)
build_platforms.py                   generates platforms/ from the skill
platforms/gemini/                    Gem instructions + knowledge
platforms/aistudio/                  system instructions + engine message
platforms/deepseek/                  bundles + engine
```

## Checking a dossier by hand

```bash
python skills/hcr/scripts/hcr_engine.py --check dossier.md
```

Exits with code 1 if there is a FAIL. It works for any model: paste the answer into a file and run it. AI Studio can also run `check(dossier_text)` itself.

## Tests

```bash
python skills/hcr/scripts/hcr_selftest.py   # -> SELFTEST OK
```
