"""Builds platforms/gemini, platforms/aistudio and platforms/deepseek from the skill in skills/hcr.
The skill is the single source of truth: edit it, never the generated files, then run:  py build_platforms.py
README.md is hand-written and never overwritten."""
import io
import pathlib
import tokenize

here = pathlib.Path(__file__).parent
skill = here / "skills" / "hcr"
plat = here / "platforms"

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
knowledge = rd(skill / "KNOWLEDGE.md").replace("py <skill dir>/scripts/hcr_engine.py", "py hcr_engine.py")
fallback = rd(skill / "FALLBACK.md").replace("py <skill dir>/scripts/hcr_engine.py", "py hcr_engine.py")
engine_src = (skill / "scripts" / "hcr_engine.py").read_text(encoding="utf-8")
toks = [t for t in tokenize.generate_tokens(io.StringIO(engine_src).readline) if t.type != tokenize.COMMENT]
engine_min = "\n".join(x.rstrip() for x in tokenize.untokenize(toks).split("\n") if x.strip()) + "\n"


def prompt(files_line, rule15):
    return "# HCR 4.1 — SYSTEM PROMPT\n" + body.replace(FILES_LINE, files_line).replace(RULE15, rule15)


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
   "ENGINE (HCR 4.1 engine, Python, standard library only). Do not answer this message. Keep it: every code call starts with this source verbatim.\n\n```python\n" + engine_min + "```")

# ---- DeepSeek (web chat: no code; API harness: code) -----------------------------------------------------------
d = plat / "deepseek"
wr(d / "BUNDLE_NOEXEC.md", prompt(
    "Files: `K` = the KNOWLEDGE section and `F` = the FALLBACK section below this prompt. There is NO code tool in this setup: always the no-code case (F, `python:false`)." + KILL,
    NOCODE15) + "\n\n---\n\n" + knowledge + "\n\n---\n\n" + fallback)
wr(d / "BUNDLE_EXEC.md", prompt(
    "Files: `K` = the KNOWLEDGE section below this prompt, `F` = the FALLBACK section (read only without a code tool), `E` = `hcr_engine.py` in the working directory." + KILL,
    RULE15.replace("${CLAUDE_SKILL_DIR}/scripts/", "")) + "\n\n---\n\n" + knowledge + "\n\n---\n\n" + fallback)
wr(d / "hcr_engine.py", engine_min)
print("platform packages rebuilt")
