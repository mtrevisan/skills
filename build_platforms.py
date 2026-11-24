"""Builds platforms/gemini, platforms/aistudio, platforms/deepseek and platforms/chatgpt from the skill in skills/hrc.
The skill is the single source of truth: edit it, never the generated files, then run:  python build_platforms.py
README.md is hand-written and never overwritten."""
import io
import pathlib
import tokenize

here = pathlib.Path(__file__).parent
skill = here / "skills" / "hrc"
plat = here / "skills" / "hrc" / "platforms"

FILES_LINE = next(l for l in (skill / "SKILL.md").read_text(encoding="utf-8").splitlines() if l.startswith("Files (in this skill"))
RULE15 = next(l for l in (skill / "SKILL.md").read_text(encoding="utf-8").splitlines() if l.startswith("15. Self-check."))
KILL = " If K is unreadable: output only `LINT_ERROR: KNOWLEDGE_MISSING`."


def rd(p):
    return p.read_text(encoding="utf-8").replace("\r\n", "\n").strip("\n")


def wr(p, s):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s.strip("\n") + "\n", encoding="utf-8", newline="\n")


body = rd(skill / "SKILL.md").split("\n---\n", 1)[1].strip("\n")      # drop the frontmatter
body = body.split("\n", 1)[1].strip("\n")                               # drop the H1
assert FILES_LINE in body and RULE15 in body
knowledge = rd(skill / "KNOWLEDGE.md").replace("python <skill dir>/scripts/hrc_engine.py", "python hrc_engine.py")
fallback = rd(skill / "FALLBACK.md").replace("python <skill dir>/scripts/hrc_engine.py", "python hrc_engine.py")
engine_src = (skill / "scripts" / "hrc_engine.py").read_text(encoding="utf-8")
toks = [t for t in tokenize.generate_tokens(io.StringIO(engine_src).readline) if t.type != tokenize.COMMENT]
engine_min = "\n".join(x.rstrip() for x in tokenize.untokenize(toks).split("\n") if x.strip()) + "\n"


def prompt(files_line, rule15):
    return "# HRC 4.1 — SYSTEM PROMPT\n" + body.replace(FILES_LINE, files_line).replace(RULE15, rule15)


NOCODE15 = "15. Self-check. No code tool: apply §4 line by line."

# ---- Gemini (Gem: Instructions + Knowledge files, no code execution) -------------------------------------------
g = plat / "gemini"
wr(g / "INSTRUCTIONS.md", prompt(
    "Files (attached as Knowledge): `K` = KNOWLEDGE.md, `F` = FALLBACK.md. There is NO code tool in this setup: always the no-code case (F, `python:false`)." + KILL,
    NOCODE15))
wr(g / "KNOWLEDGE.md", knowledge)
wr(g / "FALLBACK.md", fallback)

# ---- Google AI Studio (system instructions + Code execution tool) ---------------------------------------------
a = plat / "aistudio"
wr(a / "SYSTEM_INSTRUCTIONS.md", prompt(
    "Files: `K` = the KNOWLEDGE section below this prompt. `E` = the Python source in the FIRST user message (header ENGINE). The code tool cannot read files and keeps no state: start EVERY code call with the E source copied verbatim from that message, then call `run(payload)` (compute) or `check(dossier_text)` (self-check)." + KILL,
    "15. Self-check. Run `check(dossier_text)` from E in the code tool on the finished dossier, fix every FAIL, then send."
) + "\n\n---\n\n" + knowledge)
wr(a / "ENGINE_MESSAGE.md",
   "ENGINE (HRC 4.1 engine, Python, standard library only). Do not answer this message. Keep it: every code call starts with this source verbatim.\n\n```python\n" + engine_min + "```")

# ---- DeepSeek (web chat: no code; API harness: code) -----------------------------------------------------------
d = plat / "deepseek"
wr(d / "BUNDLE_NOEXEC.md", prompt(
    "Files: `K` = the KNOWLEDGE section and `F` = the FALLBACK section below this prompt. There is NO code tool in this setup: always the no-code case (F, `python:false`)." + KILL,
    NOCODE15) + "\n\n---\n\n" + knowledge + "\n\n---\n\n" + fallback)
wr(d / "BUNDLE_EXEC.md", prompt(
    "Files: `K` = the KNOWLEDGE section below this prompt, `F` = the FALLBACK section (read only without a code tool), `E` = `hrc_engine.py` in the working directory." + KILL,
    RULE15.replace("python3 scripts/hrc_engine.py", "python3 hrc_engine.py")) + "\n\n---\n\n" + knowledge + "\n\n---\n\n" + fallback)
wr(d / "hrc_engine.py", engine_min)


# ---- ChatGPT (Custom GPT: Instructions <= 8000 chars; Knowledge files; Code Interpreter optional) -------------------
c = plat / "chatgpt"
_rest = body.split("\n## 2. HARD RULES", 1)
sec1 = _rest[0].strip("\n")
_s24 = "## 2. HARD RULES" + _rest[1]
rules = _s24.split("\n## 3. OUTPUT TEMPLATE", 1)[0].strip("\n")
_s34 = "## 3. OUTPUT TEMPLATE" + _s24.split("\n## 3. OUTPUT TEMPLATE", 1)[1]
template, final = _s34.split("\n## 4. FINAL CHECK", 1)
final = "## 4. FINAL CHECK" + final
CG_FILES = ("Files (Knowledge, search them before EVERY answer): `K` = KNOWLEDGE.md, `F` = FALLBACK.md, `R` = RULES.md "
            "(the full HARD RULES 1-15 and the OUTPUT TEMPLATE: apply them exactly). `E` = `hrc_engine.py` in /mnt/data, usable only if "
            "Code Interpreter is on; otherwise always the no-code case (F, `python:false`)." + KILL)
CG_RULE15 = ("15. Self-check. With Code Interpreter: write the dossier to a file, run `python /mnt/data/hrc_engine.py --check <file>`, "
             "fix every FAIL, then send. Without it: apply §4 line by line.")
instr = ("# HRC 4.1 — SYSTEM PROMPT\n" + sec1.replace(FILES_LINE, CG_FILES) + "\n\n"
         "## 2. HARD RULES (full text in R: read it first; the key ones)\n"
         "- No invention: missing data -> `DATA UNKNOWN`; no fake citations, quotes, measures. Concordance with nothing verifiable -> `NONE VERIFIED`.\n"
         "- Numbers come from E (or F), never by hand when E exists. Paste E `hist_lines`, `modern_lines`, `render` lines verbatim (the State `sig` hashes them).\n"
         "- Every ingredient named anywhere has one row in BOTH lists; native unit + mass on every historical line; decimals: spices, salt, drugs 2, all others 1; fluids `X.X g = Y.Y ml`.\n"
         "- Eggs: one albumen row and one yolk row. Spice blends: search the composition first, then expand.\n"
         "- Confidence = E `confidence`, never raised. Write in the user's language (default English).\n"
         "- Same input, same output: ingredients in input order, no optional additions.\n"
         + CG_RULE15 + "\n\n"
         "## 3. OUTPUT\nFollow the OUTPUT TEMPLATE in R exactly (16 headers, State block last, no prose outside it).\n")
assert len(instr) <= 8000, "ChatGPT instructions too long: %d" % len(instr)
wr(c / "INSTRUCTIONS.md", instr)
wr(c / "RULES.md", "# HRC 4.1 — RULES (R)\n\n" + rules.replace(RULE15, CG_RULE15) + "\n\n" + template + "\n" + final)
wr(c / "KNOWLEDGE.md", knowledge)
wr(c / "FALLBACK.md", fallback)
wr(c / "hrc_engine.py", engine_min)

# ---- Agensi (upload ZIP: only what the skill needs; servers, Docker, configs and platform bundles stay out) -----------
import zipfile
dist = here / "dist"
dist.mkdir(exist_ok=True)
AGENSI = ["SKILL.md", "INSTALL.md", "KNOWLEDGE.md", "FALLBACK.md", "scripts/hrc_engine.py",
          "platforms/chatgpt/INSTRUCTIONS.md", "platforms/chatgpt/RULES.md", "platforms/chatgpt/KNOWLEDGE.md",
          "platforms/chatgpt/FALLBACK.md", "platforms/chatgpt/hrc_engine.py",
          "platforms/gemini/INSTRUCTIONS.md", "platforms/gemini/KNOWLEDGE.md", "platforms/gemini/FALLBACK.md",
          "platforms/deepseek/BUNDLE_NOEXEC.md", "platforms/deepseek/BUNDLE_EXEC.md", "platforms/deepseek/hrc_engine.py"]
with zipfile.ZipFile(dist / "hrc-agensi.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for rel in AGENSI:
        z.writestr("hrc/" + rel, rd(skill / rel) + chr(10))
print("platform packages rebuilt; Agensi ZIP: dist/hrc-agensi.zip")
