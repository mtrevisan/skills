# Historical Recipe Converter (HRC)

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.x](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)
[![Claude Code Compatible](https://img.shields.io/badge/Claude%20Code-Compatible-purple.svg)](https://www.anthropic.com/claude-code)
[![Gemini Compatible](https://img.shields.io/badge/Gemini-Compatible-orange.svg)](https://gemini.google.com/)
[![Google AI Studio Compatible](https://img.shields.io/badge/Google%20AI%20Studio-Compatible-red.svg)](https://aistudio.google.com/)
[![DeepSeek Compatible](https://img.shields.io/badge/DeepSeek-Compatible-black.svg)](https://www.deepseek.com/)
[![stdlib only](https://img.shields.io/badge/Dependencies-stdlib%20only-success.svg)](https://docs.python.org/3/library/)

A deterministic framework for reconstructing historical recipes into auditable modern technical dossiers.

HRC combines historical metrology, philological ingredient identification, quantitative reconstruction, rheological validation, and output auditing to transform historical recipes into reproducible modern cooking specifications.

Unlike generic AI prompts, HRC separates numerical reconstruction from language generation. Quantities are computed by a deterministic Python engine and validated before inclusion in the final dossier.

---

## Why HRC Exists

Historical recipes are difficult to interpret because they combine:

- Obsolete terminology.
- Regional dialects.
- Historical spellings.
- Ambiguous ingredient names.
- Incomplete procedures.
- Non-standard units of measure.
- Missing contextual information.

General-purpose AI models frequently:

- Invent values for unknown measures.
- Confuse historical and modern ingredients.
- Perform inconsistent conversions.
- Hide uncertainty behind plausible text.
- Produce different results across runs.

HRC follows a different principle:

> If evidence is missing, uncertainty must be documented rather than invented.

Every value in the final dossier must be:

- Calculated;
- Derived from documented evidence;
- Or explicitly marked as `DATA UNKNOWN`.

---

## Core Capabilities

### Historical Metrology

Reconstructs historical quantities using documented measure systems.

Supported scenarios include:

- Local and regional units.
- Hierarchical measure chains.
- Historical sub-units.
- Container-based measures.
- Count-based measures.
- Price-derived measures.
- Source-specific conversion tables.

When no authoritative evidence exists, the quantity remains `DATA UNKNOWN`.

---

### Philological Ingredient Identification

Ingredient identification is not based on lexical similarity.

HRC evaluates:

1. Internal recipe evidence.
2. Parallel recipes.
3. Historical dictionaries.
4. Dialect dictionaries.
5. Botanical references.
6. Culinary-history literature.

Ambiguous terms remain unresolved when the evidence is insufficient.

HRC never silently chooses the most plausible interpretation.

---

### Deterministic Quantity Reconstruction

Historical quantities are reconstructed through a deterministic engine.

The engine supports:

- Unit conversion.
- Ratio propagation.
- Density-based projection.
- Scale normalization.
- Missing quantity reconstruction.
- Consistency validation.

Identical inputs always produce identical numerical outputs.

---

### Technological and Rheological Validation

Ingredient quantities are validated against technological archetypes rather than copied blindly from historical sources.

Supported archetypes include:

- DOUGH_DENSE
- DOUGH_OPEN
- GEL_SOFT
- GEL_FIRM
- LIQUID_THICK
- LIQUID_THIN
- PROTEIN_COAGULUM

Validation may include:

- Hydration-ratio analysis.
- Lipid constraints.
- Aromatic-load constraints.
- Density checks.
- Water-activity estimation.
- Thermal-window consistency.

---

### Variant-Aware Reconstruction

Historical recipes frequently contain alternative ingredient sets or optional formulations.

HRC reconstructs each variant independently.

Every variant receives:

- Its own ingredient table.
- Its own mass balance.
- Its own rheological validation.
- Its own confidence assessment.

Variants are never merged during optimization.

---

### Concordance Construction

When comparable recipes are available, HRC builds a concordance from source-provided evidence.

The concordance is used to:

- Clarify terminology.
- Validate ingredient identification.
- Support interpretation decisions.
- Document alternative readings.

Only material explicitly supplied by the user may enter the concordance.

---

## Reproducibility and Auditing

HRC is designed to produce auditable outputs.

The deterministic engine generates a verification signature (`sig`) tied to the reconstructed state.

This enables:

- Repeatability checks.
- Change detection.
- Post-processing detection.
- Independent validation.

The same input, evidence set, and rules produce the same reconstructed state.

---

## Output Validation

HRC includes a validation engine capable of auditing dossiers generated by any AI model.

Validation covers:

- Structural conformity.
- Missing mandatory sections.
- Decimal precision rules.
- Ingredient consistency.
- Duplicate entries.
- Mass-balance anomalies.
- Variant consistency.
- Verification signature integrity.

A dossier can therefore be reviewed independently from the model that produced it.

---

## Design Principles

HRC follows five principles:

1. Evidence before assumption.
2. Determinism before plausibility.
3. Explicit uncertainty.
4. Source traceability.
5. Reproducible outputs.

A historically incorrect answer presented with confidence is worse than an incomplete answer with documented uncertainty.

---

## Example

### Historical Input

> Take one libra of flour, half a boccale of milk, three once of sugar and a pinch of cinnamon.

### Output Excerpt

| Historical Ingredient | Modern Identification | Mass (g) | Confidence |
|------------------------|----------------------|----------|------------|
| 1 libra flour | Wheat flour | 339.0 | HIGH |
| 1/2 boccale milk | Whole milk | 540.0 | MEDIUM |
| 3 once sugar | White sugar | 84.8 | HIGH |
| pinch cinnamon | Cinnamon | DATA UNKNOWN | LOW |

### Generated Dossier

The final dossier may include:

- Historical ingredient table.
- Modern ingredient table.
- Identification rationale.
- Metrological evidence.
- Reconstruction assumptions.
- Confidence assessment.
- Rheological analysis.
- HACCP observations.
- STE100 preparation procedure.
- Bibliographic references.
- Validation signature.

---

## Requirements

- **Core Engine (`hrc_engine.py`):** Python 3.10+ (standard library only, zero third-party dependencies).
- **MCP / REST Server (`server.py`):** Optional dependencies listed in `requirements.txt` (`fastapi`, `uvicorn`, `mcp`, `pydantic`, `python-dotenv`).
- **No-Code / Web Interfaces:** Works without Python via `FALLBACK.md` (manual mode, confidence capped at `MEDIUM`).

---

## Installation

### Agensi Marketplace

Install directly from [Agensi](https://agensi.ai) into any compatible agent (Claude Code, Cursor, Codex CLI, Gemini CLI, Windsurf, and more), or download the skill bundle and use the platform adapter for your preferred AI environment.

### Claude Code Marketplace

```bash
claude plugin marketplace add mtrevisan/skills
claude plugin install hrc@skills
```

For Claude Code 2.1.275 or newer:

```bash
/plugin install hrc --marketplace mtrevisan/skills
```

### Manual Installation

```bash
git clone --depth 1 https://github.com/mtrevisan/skills.git
```

```bash
mkdir -p ~/.claude/skills
```

```bash
cp -r skills/skills/hrc ~/.claude/skills/hrc
```

For project-local installation:

```text
<project>/.claude/skills/hrc
```

To update:

```bash
git pull
```

and copy the skill directory again.

---

## Usage

Invoke:

```text
/hrc
```

or ask the model to analyse a historical recipe (e.g., `"HRC: analyze this 14th-century recipe..."`).

Recommended input:

1. Historical recipe text.
2. Comparable recipes (optional).
3. Bibliographic references.
4. Historical measure tables.

If conversion tables are not provided, HRC may search for documented sources and cite them.

Unknown values remain `DATA UNKNOWN`.

For maximum reproducibility, use a model temperature between `0.0` and `0.2`.

---

## Confidence Levels

### HIGH

Directly supported by evidence or documented conversion tables.

### MEDIUM

Supported by indirect evidence with limited ambiguity.

### LOW

Supported by weak, incomplete, or competing evidence.

Confidence reflects evidential strength, not historical certainty.

---

## Fallback Mode

When Python execution is unavailable, HRC can operate in manual mode (`FALLBACK.md`).

In fallback mode:

- Deterministic computation is disabled.
- Quantitative reconstruction follows documented manual procedures.
- `python` is set to `false` in the State block.
- Confidence is capped at `MEDIUM`.
- The dossier explicitly reports the fallback status (`Manual Fallback`).

---

## Supported Platforms

### Claude Code / Codex CLI / Open `SKILL.md` Agents

Native `SKILL.md` support. Agents execute `scripts/hrc_engine.py` directly via shell.

### MCP Server (Claude Desktop, Cursor, Cline, Windsurf)

Run HRC as a local or remote Model Context Protocol server without granting shell access:

1. Install server dependencies:
   ```bash
pip install -r skills/hrc/requirements.txt
   ```
2. Add the server configuration from skills/hrc/configs/claude_desktop.json or `skills/hrc/configs/cursor_mcp.json` to your client settings (updating `/absolute/path/bundle/` to your local path).
3. Load `skills/hrc/SYSTEM_PROMPT_TOOLS.md` as your project/system prompt.
The MCP server exposes get_knowledge, get_fallback, run_engine, and check_dossier as native tools.

Custom API / Tool-Calling Harnesses (ChatGPT, OpenAI API, Agensi Web)

For tool-calling agents connecting over HTTP:
1. Start the server in HTTP mode (HRC_MODE=http, HRC_TOKEN=<your-secret>):
   bash HRC_MODE=http HRC_TOKEN=your-secret python skills/hrc/scripts/server.py    
2. Register the tool definitions from skills/hrc/configs/openai_tools.json.
3. Use skills/hrc/SYSTEM_PROMPT_TOOLS.md as the system prompt.

### Gemini

#### Gemini Gem

Upload:

- `skills/hrc/platforms/gemini/INSTRUCTIONS.md`
- `skills/hrc/platforms/gemini/KNOWLEDGE.md`
- `skills/hrc/platforms/gemini/FALLBACK.md`

#### Gemini CLI

```bash
gemini skills install https://github.com/mtrevisan/skills.git --path skills
```

### Google AI Studio

Enable:

- Code Execution.
- Temperature between 0.0 and 0.2.

Then:

1. Paste skills/hrc/platforms/aistudio/SYSTEM_INSTRUCTIONS.md.
2. Paste skills/hrc/platforms/aistudio/ENGINE_MESSAGE.md.
3. Submit the recipe.

### DeepSeek

#### Web Interface

Use:

```text
skills/hrc/platforms/deepseek/BUNDLE_NOEXEC.md
```

#### API or Agent Harness

Use:

```text
skills/hrc/platforms/deepseek/BUNDLE_EXEC.md
```

and place:

```text
skills/hrc/platforms/deepseek/hrc_engine.py
```

in the working directory.

---

## Repository Structure

```text
.claude-plugin/
└── plugin.json

skills/
└── hrc/
    ├── SKILL.md
    ├── KNOWLEDGE.md
    ├── FALLBACK.md
    ├── SYSTEM_PROMPT_TOOLS.md
    ├── requirements.txt
    ├── .env.example
    ├── configs/
    │   ├── claude_desktop.json
    │   ├── cursor_mcp.json
    │   └── openai_tools.json
    ├── platforms/
    │   ├── gemini/
    │   ├── aistudio/
    │   └── deepseek/
    └── scripts/
        ├── hrc_engine.py
        ├── hrc_selftest.py
        └── server.py
build_platforms.py
```

---

## Validate a Dossier

```bash
python skills/hrc/scripts/hrc_engine.py --check dossier.md
```

Exit status:

```text
0 = PASS
1 = FAIL
```

The validator is model-independent and can verify dossiers produced by any AI system.

---

## Run Tests

```bash
python skills/hrc/scripts/hrc_selftest.py
```

Expected result:

```text
SELFTEST OK
```

---

## Non-Goals

HRC does not:

- Guess unknown ingredients.
- Invent missing measures.
- Invent densities.
- Invent preparation steps.
- Hide uncertainty.
- Replace historical terminology without documentation.

When evidence is absent, the correct result is:

```text
DATA UNKNOWN
```

---

## License

MIT License.

Copyright (c) 2026 Mauro Trevisan.

See the `LICENSE` file for details.
