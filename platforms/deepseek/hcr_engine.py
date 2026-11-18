"""HCR 4.1 engine: calculation routines and output linter, no tests. One file to load into the AI. Stdlib only.
Run:  py hcr_engine.py payload.json   |   py hcr_engine.py < payload.json     (add --full for raw floats per ingredient)
      py hcr_engine.py --check dossier.md   (output linter; a whole dossier or only the two ingredient lists; exit 1 on FAIL)
Input/Output schema: see '../KNOWLEDGE.md' section E.  Tests: hcr_selftest.py (development only)."""
import hashlib, json, math, re, sys
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
KEVAP = 0.0142
DENS = {"starch": 1.55, "protein": 1.35, "lipid": 0.92, "fluid": 1.025, "osmotic": 1.59, "ionic": 2.16, "other": 1.20}
POR = {"DOUGH_OPEN": .425, "DOUGH_DENSE": .165, "GEL_SOFT": .02, "GEL_FIRM": .045, "SOLID_DRY": .55,
       "LIQUID_THICK": .05, "LIQUID_THIN": .01, "PROTEIN_COAGULUM": .03}
AWF = {"SOLID_DRY": (.3, .6), "DOUGH_DENSE": (.85, .92), "DOUGH_OPEN": (.92, .95), "GEL_FIRM": (.94, .965),
       "GEL_SOFT": (.96, .985), "LIQUID_THICK": (.97, .99), "LIQUID_THIN": (.98, .999),
       "PROTEIN_COAGULUM": (.95, .985), "MATRIC_UNSPECIFIED": (.75, .95)}
BND = {"GEL_SOFT": (1.7, 2.7), "GEL_FIRM": (.8, 1.7), "DOUGH_DENSE": (.45, .62), "DOUGH_OPEN": (.62, .85),
       "LIQUID_THICK": (4., 10.), "LIQUID_THIN": (10., math.inf), "SOLID_DRY": (0., .3), "PROTEIN_COAGULUM": (1.2, 3.5)}
LIPMOD = {"EMULSION_O_W": 1.1, "FAT_SHORTENING": .9}
ALLOWED_DEN = (1, 2, 3, 4, 6, 8, 12)
SOTT = ("salt", "drug", "hydrolat")
FLOOR = {"SOTTILE": .01, "GROSSO": .1, "DRY_VOLUME": .1, "LIQUID_VOLUME": .1}
KEYS = ("integer count", "saturation", "boundary", "constraint", "clamp")
IDENT = ("KNOWN", "RESEARCHED", "UNKNOWN")
ALWAYS_STABLE = ("flour", "spice", "sugar", "salt", "drug", "hydrolat")
ALWAYS_PERISHABLE = ("meat", "cheese")
EGG = [(.080, 1962, 1348, 120, 39.5, 1.85, 54.5, 2.38, -2.8, -.12), (.055, 1978, 1258, 150, 33.5, 1.80, 46.5, 2.25, -3.2, -.15),
       (.075, 1965, 1350, 140, 37.5, 1.90, 52.5, 2.35, -2.5, -.10), (.070, 1968, 1385, 130, 38.0, 1.85, 52.0, 2.34, -2.2, -.10),
       (.085, 1956, 1349, 110, 39.0, 1.88, 53.5, 2.36, -2.5, -.10), (.075, 1958, 1350, 140, 38.5, 1.90, 53.5, 2.36, -2.8, -.12),
       (.080, 1958, 1349, 120, 39.5, 1.88, 54.5, 2.38, -2.6, -.11), (.090, 1950, 1349, 110, 40.0, 1.92, 55.5, 2.40, -3.0, -.14),
       (.075, 1966, 1348, 130, 38.5, 1.84, 54.0, 2.36, -2.6, -.12), (.065, 1970, 1150, 180, 39.5, 1.82, 53.0, 2.34, 2.2, .08),
       (.085, 1958, 1348, 120, 40.0, 1.88, 55.0, 2.38, -2.8, -.12), (.085, 1956, 1349, 120, 39.8, 1.90, 55.0, 2.39, -2.7, -.12),
       (.080, 1960, 1349, 120, 39.5, 1.88, 54.5, 2.38, -2.6, -.11), (.090, 1954, 1349, 110, 40.2, 1.92, 55.5, 2.40, -2.8, -.12),
       (.095, 1950, 1349, 110, 40.5, 1.93, 56.5, 2.42, -2.5, -.11), (.095, 1945, 0, 0, 41.0, 1.95, 56.0, 2.41, 0., 0.)]
def egg_model(year, n):
    k, fx, lp, lw, e0, r0, e1, r1, le, lr = EGG[n] if n is not None and 0 <= n < 16 else (.075, 1960, 1350, 120, 39.5, 1.88, 54.0, 2.36, -2.5, -.10)
    sig = 1 / (1 + math.exp(max(-60., min(60., -k * (year - fx)))))
    lor = 0. if lw == 0 else 1 / (1 + ((year - lp) / lw) ** 2)
    ew = e0 + (e1 - e0) * sig + le * lor
    r = r0 + (r1 - r0) * sig + lr * lor
    t = 1 / (1 + r)
    return {"total_edible_g": ew, "yolk_g": ew * t, "albumen_g": ew - ew * t, "ratio_alb_yolk": r, "sig": sig, "lor": lor,
            "albumen_w_pct": .855 + .026 * sig - .008 * lor, "albumen_p_pct": .115 - .012 * sig + .004 * lor,
            "yolk_w_pct": .49 + .025 * sig - .01 * lor, "yolk_p_pct": .162 - .006 * sig + .003 * lor,
            "yolk_f_pct": .325 - .02 * sig + .008 * lor}
def tr(x, d):
    return str(Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP))
def track(cat, vol):
    if cat == "flour": return "DRY_VOLUME" if vol else "GROSSO"
    if cat == "hydrolat" and vol: return "LIQUID_VOLUME"
    if cat in ("spice", "sugar", "salt", "drug", "hydrolat"): return "SOTTILE"
    if cat == "liquid": return "LIQUID_VOLUME" if vol else "GROSSO"
    return "GROSSO"
def frac(s):
    try:
        if s is None or isinstance(s, bool): return None
        if isinstance(s, Fraction): return s
        if isinstance(s, int): return Fraction(s)
        if isinstance(s, float):
            return Fraction(int(s)) if s == int(s) else None
        ss = str(s).strip()
        if not ss: return None
        if any(c in ss for c in ".,"): return None
        return sum((Fraction(p) for p in ss.split()), Fraction(0))
    except (ValueError, ZeroDivisionError):
        return None
def fstr(f):
    w, r = divmod(f.numerator, f.denominator)
    return (f"{w} " if w else "") + (f"{r}/{f.denominator}" if r else "") if r or not w else str(w)
def retro(mass, unit_g, dens=ALLOWED_DEN):
    best = None
    for d in dens:
        f = Fraction(round(mass / unit_g * d), d)
        if f > 0 and (best is None or abs(float(f) - mass / unit_g) < abs(float(best) - mass / unit_g) - 1e-12): best = f
    return best
def pick_unit(h, mm, isfl, fl):
    """Quantity missing: coarsest table unit with Q >= 1 and error <= 1.5 % (else the finest that fits).
    Fluids take a volumetric unit, solids a weight unit (flour may be volumetric). Returns ((q, unit row, g per unit), None) or (None, reason)."""
    us = h.get("units") or [{k: h.get(k) for k in ("unit", "unit_g", "unit_ml")}]
    ok, why = [], "no table unit within 1.5 % (add a finer unit of the same table)"
    for x in us:
        if (isfl and not x.get("unit_ml")) or (not isfl and not x.get("unit_g") and h.get("cat") != "flour"):
            why = "a fluid takes a volumetric unit, a solid a weight unit"; continue
        g = x.get("unit_g") if not isfl and x.get("unit_g") else (x["unit_ml"] * fl if x.get("unit_ml") and fl else None)
        if not g: why = "volumetric unit without fluid_rho"; continue
        q = retro(mm, g)
        if q is not None and abs(float(q) * g - mm) / mm <= .015: ok.append(((q >= 1, g if q >= 1 else -g), q, x, g))
    if not ok: return None, why
    b = max(ok, key=lambda c: c[0])
    return b[1:], None
def _grp(it):
    f, p = it.get("function", ""), it.get("phase", "")
    if "starch" in f or "gluten" in f: return "starch"
    if f == "osmotic_solute": return "osmotic"
    if f == "ionic_solute": return "ionic"
    if p == "lipid" or "lipid" in f: return "lipid"
    if "protein" in f: return "protein"
    if p == "fluid": return "fluid"
    return "other"
def density(items, tgt):
    m = sum(i["m"] for i in items)
    v = sum(i["m"] / DENS[_grp(i)] for i in items if i["m"] > 0)
    if m <= 0 or v <= 0: return DENS["fluid"], 0.
    cc = tgt.get("critical_chemical_constraints", {})
    por = POR.get(cc.get("hydration_archetype"), .1) * LIPMOD.get(cc.get("lipid_archetype"), 1.)
    por = min(.85, por)
    return (m / v) * (1 - por), (m / v) * .01
def calc_aw(items, arch):
    fl = sum(i["m"] for i in items if i.get("phase") == "fluid")
    sol = 0.
    for i in items:
        f = i.get("function")
        if f == "osmotic_solute": sol += i["m"] / float(i.get("mw", 342.3))
        elif f == "ionic_solute": sol += i["m"] / 58.44 * 2
    if fl <= 0: return 1., 1., False
    w = fl / 18.015
    raw = w / (w + sol)
    lo, hi = AWF.get(arch, (.5, .999))
    c = max(lo, min(hi, raw))
    return c, raw, c != raw
def scale_floors(items, M):
    """items carry weight w; returns masses summing to M with floors; flags clamped."""
    fixed = {}
    for _ in range(len(items) + 1):
        free = [i for i in items if id(i) not in fixed]
        if not free: break
        rest = M - sum(fixed.values())
        sw = sum(i["w"] for i in free)
        if sw <= 0:
            for i in free: i["m"] = 0.
            return False
        k = rest / sw
        new = [i for i in free if k * i["w"] < FLOOR[i["track"]]]
        if not new:
            for i in free: i["m"] = k * i["w"]
            break
        for i in new: fixed[id(i)] = FLOOR[i["track"]]; i["m"] = fixed[id(i)]; i["clamp"] = "floor clamp"
    for i in items: i.setdefault("m", 0.)
    return sum(fixed.values()) <= M + 1e-9
def inset(lo, hi):
    return (lo * 1.1, hi) if math.isinf(hi) else (lo + .1 * (hi - lo), hi - .1 * (hi - lo))
def run(p, full=False):
    err, notes, pen = [], [], []
    ev = math.exp(-KEVAP * p.get("evap_min", 5.0))
    egg = egg_model(p["year"], p.get("zone", 0))
    tg = {t["sub_matrix_name"]: t for t in p.get("inferred_targets", [])}
    items, surf, bound = [], [], False
    vt = lambda x: f" (variant: {x['variant']})" if x.get("variant") else ""
    for n_, r in enumerate(p["ingredients"]):
        r = dict(r); r["_i"] = n_; r["track"] = track(r.get("cat"), r.get("vol"))
        if r.get("type") == "pure_surface_density": surf.append(r); continue
        if r.get("unknown"):
            return {"errors": [f"LINT_ERROR: DATA UNKNOWN modern row refused - {r['name']}: weigh it (unidentified: ident UNKNOWN + cat other; blend without composition: one spice row, hist blend:true)"]}
        if not r.get("egg"):
            idt = r.get("ident") or {}
            st = idt.get("status")
            if st not in IDENT: return {"errors": [f"LINT_ERROR: Identification missing or invalid - {r['name']}"]}
            if st != "UNKNOWN" and not str(idt.get("src", "")).strip():
                return {"errors": [f"LINT_ERROR: Identification without source - {r['name']}"]}
            if st == "UNKNOWN":
                if r.get("cat") != "other": return {"errors": [f"LINT_ERROR: Unidentified ingredient must use cat other - {r['name']}"]}
                pen.append("unidentified ingredient " + r["name"])
            if r["track"] == "SOTTILE" and "starch" in r.get("function", ""):
                return {"errors": [f"LINT_ERROR: Critical metrology routing violation - starch network ingredient in SOTTILE track - {r['name']}"]}
        if r.get("egg"):
            if r["egg"] not in ("albumen", "yolk"): return {"errors": [f"LINT_ERROR: Egg row must be albumen or yolk, in grams - {r['name']}"]}
            items.append({"name": r["egg"], "sub_matrix": r["sub_matrix"], "phase": "solid", "function": "protein_coagulation",
                          "cat": "other", "track": "GROSSO", "perishable": True, "w": float(r["seed"]), "egg_of": r["name"], "hist_ref": r.get("hist_ref"), "taxon": r.get("taxon"),
                          "just": r.get("just", ""), "_i": n_, "variant": r.get("variant")})
            continue
        r["w"] = float(r["seed"]); items.append(r)
    for i in items:
        if i.get("inferred"): pen.append("inferred ingredient " + i["name"])
    sv = {}
    for i in items: sv.setdefault(i["sub_matrix"], set()).add(i.get("variant"))
    for m_, vs_ in sv.items():
        if len(vs_) > 1: err.append(f"LINT_ERROR: Sub-matrix mixes variants - {m_}")
    for h in p.get("hist", []):
        pts = h.get("parts") or []
        comp = {i["name"]: i for i in items if i.get("hist_ref") == h["name"] and i.get("variant") == h.get("variant")}
        if pts and sorted(comp) == sorted(x[1] for x in pts) and sum(x[0] for x in pts) > 0:
            tot, ps = sum(i["w"] for i in comp.values()), sum(x[0] for x in pts)
            for x in pts: comp[x[1]]["w"] = tot * x[0] / ps
    mats = list(dict.fromkeys(i["sub_matrix"] for i in items))
    for m in mats:
        if m not in tg: err.append(f"LINT_ERROR: L9 sub-matrix without inferred target - {m}")
    for mname in mats:
        its = [i for i in items if i["sub_matrix"] == mname]
        cc = tg.get(mname, {}).get("critical_chemical_constraints", {})
        arch, lip = cc.get("hydration_archetype", "MATRIC_UNSPECIFIED"), cc.get("lipid_archetype")
        F = [i for i in its if i.get("phase") == "fluid"]; S = [i for i in its if "starch" in i.get("function", "")]
        E = [i for i in its if i.get("egg_of")]; L = [i for i in its if i.get("phase") == "lipid"]
        fw, sw, ew_, lw_ = (sum(i["w"] for i in g) for g in (F, S, E, L))
        den = ew_ if arch == "PROTEIN_COAGULUM" else sw
        if arch in BND and den > 0 and fw > 0:
            lo, hi = BND[arch]; r = fw * ev / den
            if not lo <= r <= hi:
                ilo, ihi = inset(lo, hi); k = (min(max(r, ilo), ihi) / r)
                for i in F: i["w"] *= k
                bound = True; notes.append(f"[{mname}] fluid ratio {r:.4f}->bound {arch}")
                fw *= k
        elif arch in BND and (den <= 0 or fw <= 0):
            notes.append(f"[{mname}] ratio check skipped (no {'starch/egg' if den <= 0 else 'fluid'})")
        if lw_ > 0:
            fe = fw * ev
            if lip == "EMULSION_O_W" and lw_ / max(fe, 1e-12) <= .82: f = .82 * fe * 1.05 / lw_
            elif lip == "FAT_SHORTENING" and sw > 0 and lw_ / sw < .35: f = .35 * sw * 1.05 / lw_
            elif lip == "LOW_FAT" and lw_ / max(fe + sw, 1e-12) > .05: f = .05 * (fe + sw) * .95 / lw_
            else: f = 1.
            if f != 1.:
                for i in L: i["w"] *= f
                bound = True; notes.append(f"[{mname}] lipid -> {lip} bound")
    g = p.get("geometry"); M, geo = dict(p.get("matrix_mass_g", {})), None
    dens = {m: density([dict(i, m=i["w"]) for i in items if i["sub_matrix"] == m], tg.get(m, {})) for m in mats}
    if g:
        D, mer = g.get("D", 20.), g.get("merlon", 0.)
        cf, ff = list(g.get("crust", [0] * 5)), list(g.get("filling", [0] * 5))
        if not any(cf) and not any(ff): cf, ff = [.5, .001, 1, .001, 0], [2., .001, 1, .001, 0]; notes.append("GEOMETRY_DEFAULT"); pen.append("geometry default")
        def sg(c):
            a, b, c_, d, e = c
            if not b or not d: notes.append("GEOMETRY_SIMPLIFICATION"); pen.append("geometry simplification"); return a
            return a + b / (c_ + math.exp(d * (D - e)))
        t, h = sg(cf), sg(ff)
        cm, fm = g.get("crust_matrix", "crust"), g.get("filling_matrix", "filling")
        if cm in dens: M[cm] = math.pi * dens[cm][0] * (D ** 2 / 4 + (D - t) * (h + mer)) * t
        else: t = 0.
        if fm in dens: M[fm] = math.pi / 4 * dens[fm][0] * (D - 2 * t) ** 2 * h
        geo = {"crust_thickness_cm": t, "filling_height_cm": h, "D": D, "merlon": mer, "crust_coef": cf, "filling_coef": ff,
               "dough_g": M.get(cm), "filling_g": M.get(fm), "crust_matrix": cm, "filling_matrix": fm}
    for m in mats:
        its = [i for i in items if i["sub_matrix"] == m]
        if m not in M and m in p.get("matrix_volume_ml", {}): M[m] = dens[m][0] * p["matrix_volume_ml"][m]
        tot = M.setdefault(m, sum(i["w"] for i in its))
        if not scale_floors(its, tot): err.append(f"LINT_ERROR: floors exceed mass [{m}]")
        if any(i.get("clamp") for i in its): bound = True
    tot_all = sum(i["m"] for i in items)
    ar = [i for i in items if i.get("function") == "volatile_aromatic" and i.get("cat") == "spice"]
    L6 = "OK"
    if ar and tot_all > 0:
        denom_ar = sum(i["m"] for i in ar)
        iar = (sum(i["m"] * i.get("i_ar", 1.5) for i in ar) / denom_ar) if denom_ar > 0 else 1.5
        cap = .005 / iar * tot_all if iar > 0 else float("inf")
        ar_ids = {id(i) for i in ar}
        for _ in range(5):
            fx = sum(i["m"] for i in ar if i.get("clamp")); fr = sum(i["m"] for i in ar if not i.get("clamp"))
            if fx + fr <= cap + 1e-12: break
            if fr <= 0: break
            f = max(0., (cap - fx) / fr)
            for m in mats:
                its = [i for i in items if i["sub_matrix"] == m]
                a = [i for i in its if id(i) in ar_ids and not i.get("clamp")]
                if not a: continue
                fs = [i for i in its if "starch" in i.get("function", "") or i.get("phase") == "fluid"]
                if not fs: fs = [i for i in its if id(i) not in ar_ids]
                if not fs: continue
                sfs = sum(i["m"] for i in fs)
                if sfs <= 0: continue
                freed = 0.
                for i in a:
                    nm_ = max(i["m"] * f, FLOOR["SOTTILE"]); freed += i["m"] - nm_
                    if nm_ == FLOOR["SOTTILE"]: i["clamp"] = "floor clamp"
                    i["m"] = nm_
                for i in fs: i["m"] += freed * i["m"] / sfs
            bound = True
        L6 = "OK" if sum(i["m"] for i in ar) <= cap + 1e-9 else "FAIL"
        if L6 == "FAIL": pen.append("aromatic cap unreachable (floors)")
    checks, rh = {}, []
    for m in mats:
        its = [i for i in items if i["sub_matrix"] == m]; cc = tg.get(m, {}).get("critical_chemical_constraints", {})
        arch, lip = cc.get("hydration_archetype", "MATRIC_UNSPECIFIED"), cc.get("lipid_archetype")
        fl = sum(i["m"] for i in its if i.get("phase") == "fluid") * ev
        st = sum(i["m"] for i in its if "starch" in i.get("function", ""))
        li = sum(i["m"] for i in its if i.get("phase") == "lipid"); eg = sum(i["m"] for i in its if i.get("egg_of"))
        if arch in BND:
            d = max(.1, eg) if arch == "PROTEIN_COAGULUM" else st
            if d > 0:
                r = fl / d; lo, hi = BND[arch]
                if not lo - 1e-9 <= r <= hi + 1e-9: rh.append(f"RHEO_ERROR: [{m}] {arch} ratio {r:.4f} out of [{lo},{hi}]")
        if lip == "EMULSION_O_W" and not (fl > 0 and li / fl > .82): rh.append(f"RHEO_ERROR: [{m}] Emulsion inversion risk")
        if lip == "FAT_SHORTENING" and not (st > 0 and li / st >= .35): rh.append(f"RHEO_ERROR: [{m}] Insufficient shortening lipid")
        if lip == "LOW_FAT" and fl + st > 0 and li / (fl + st) > .05: rh.append(f"RHEO_ERROR: [{m}] LOW_FAT boundary violation")
        if "HYDROLAT_" in str(cc.get("hydrolat_archetype")) and not any(i.get("cat") == "hydrolat" for i in its): rh.append(f"RHEO_ERROR: [{m}] Missing aromatic distillates")
    final = sum(i["m"] for i in items)
    for m in mats:
        s = sum(i["m"] for i in items if i["sub_matrix"] == m)
        if not math.isclose(s, M[m], rel_tol=1e-3): err.append(f"LINT_ERROR: Mass Mismatch ({m})")
    for i in items:
        x = i["m"]
        if abs(x - round(x)) < 1e-4 or abs(x % 1 - .5) < 1e-4:
            j = i.get("just", "") or i.get("clamp", "")
            if i.get("clamp"): j = "clamp: " + i["clamp"] + " constraint"
            if len(j) < 20 or not any(k in j.lower() for k in KEYS): err.append(f"LINT_ERROR: Unjustified termination {i['name']}")
    hl_rows = p.get("hist", [])
    hmap = {(h["name"], h.get("variant")): h for h in hl_rows}
    if len(hmap) != len(hl_rows): err.append("LINT_ERROR: Duplicate historical line (same name and variant)")
    hg = {}
    for k, h in hmap.items():
        q = frac(h.get("qty_native"))
        if q is not None and h.get("unit_g") and not h.get("egg"): hg[k] = float(q) * h["unit_g"]
    mod_by_ref = {}
    for i in items:
        ref = i.get("hist_ref") or i.get("egg_of")
        if ref: k = (ref, i.get("variant")); mod_by_ref[k] = mod_by_ref.get(k, 0.) + i["m"]
    for ref, m in mod_by_ref.items():
        if ref in hg and hg[ref] > 0:
            if abs(m - hg[ref]) < .01: err.append(f"LINT_ERROR: Ingredient mirroring {ref[0]}")
            elif abs(m - hg[ref]) < .1 and abs(m - hg[ref]) / hg[ref] < .01: notes.append(f"Historical Alignment Achieved: {ref[0]}")
    ht = sum(hg[r] for r in mod_by_ref if r in hg)
    if ht > 0 and abs(sum(mod_by_ref[r] for r in mod_by_ref if r in hg) - ht) < .01: err.append("LINT_ERROR: Total mirroring")
    hl, L8, L7 = [], "OK", "OK"
    for n_ in sorted({i.get("egg_of") or i["name"] for i in items if (i.get("hist_ref"), i.get("variant")) not in hmap}):
        err.append(f"LINT_ERROR: Ingredient without historical line - {n_}")
    for i in items:
        h = hmap.get((i.get("hist_ref"), i.get("variant")))
        if h and not i.get("egg_of") and not h.get("parts") and i["name"] != h["name"]:
            err.append(f"LINT_ERROR: Modern name differs from historical name - {i['name']} / {h['name']}")
    for h in hl_rows:
        egk, v, key = h.get("egg"), vt(h), (h["name"], h.get("variant"))
        refs = [i for i in items if (i.get("hist_ref") or i.get("egg_of"), i.get("variant")) == key]
        if not refs: err.append(f"LINT_ERROR: Historical line without modern row - {h['name']}{v}")
        isfl = any(i.get("phase") == "fluid" for i in refs)
        fl = h.get("fluid_rho") or next((i["rho"] for i in refs if i.get("rho")), None)
        q, u, ug, uml = frac(h.get("qty_native")), h.get("unit", ""), h.get("unit_g"), h.get("unit_ml")
        if egk: ug, uml = {"albumen": egg["albumen_g"], "yolk": egg["yolk_g"]}.get(egk, egg["total_edible_g"]), None
        elif not h.get("proxy") and any((x.get("unit_g") or x.get("unit_ml")) and not str(x.get("unit_src", "")).strip() for x in [h] + list(h.get("units") or [])):
            err.append(f"LINT_ERROR: Measure without source - {h['name']}")
        if h.get("qty_native") is not None and (not u or str(u).lower() not in str(h.get("src_text", "")).lower()):
            err.append(f"LINT_ERROR: Quantity without source text - {h['name']}")
        pts = h.get("parts") or []
        if pts and sorted(i["name"] for i in refs) != sorted(x[1] for x in pts): err.append(f"LINT_ERROR: Spice blend not decoupled (one modern row per part, same names) - {h['name']}")
        if h.get("blend") and not pts: pen.append("blend composition unknown " + h["name"])
        if ug is None and uml:
            if fl: ug = uml * fl
            elif h.get("qty_native") is not None: err.append(f"LINT_ERROR: Volumetric measure without fluid_rho - {h['name']}")
        if h.get("qty_native") is not None and (q is None or q.denominator not in ALLOWED_DEN): L8 = "FAIL"; err.append(f"LINT_ERROR: L8 {h['name']}")
        tax = f" (*{h['taxon']}*)" if h.get("taxon") else ""; inf = False
        if h.get("qty_native") is None:
            mm = mod_by_ref.get((h.get("modern_ref", h["name"]), h.get("variant")))
            if mm and egk:
                q = retro(mm, ug, (1, 2)) or Fraction(1, 2); inf = True
            elif mm and (h.get("units") or ug or uml):
                b, why = pick_unit(h, mm, isfl, fl)
                if b is None:
                    L7 = "FAIL"; err.append(f"LINT_ERROR: L7 {h['name']} - {why}"); hl.append(f"[Inferred: DATA UNKNOWN] {h['name']}{v}"); continue
                q, u, ug, uml = b[0], b[1].get("unit", ""), b[2], b[1].get("unit_ml"); inf = True
            else: hl.append(f"[Inferred: DATA UNKNOWN] {h['name']}{v}"); pen.append("DATA UNKNOWN " + h["name"]); continue
        gm = float(q) * ug if q is not None and ug else None
        vm = float(q) * uml if q is not None and uml else (gm / fl if gm is not None and fl and isfl else None)
        d = 2 if h.get("cat") in ("spice", "salt", "drug", "hydrolat") else 1
        core = f"{tr(gm, d)} g" if gm is not None else ""
        if vm is not None: core += (" = " if core else "") + f"{tr(vm, 1)} ml"
        if egk is True and gm is not None:
            core = f"{tr(float(q) * egg['albumen_g'], 1)} g albumen + {tr(float(q) * egg['yolk_g'], 1)} g yolk"
        elif egk in ("albumen", "yolk") and gm is not None:
            core = f"{tr(gm, 1)} g {egk}"
        if not core and q is not None: core = " [DATA UNKNOWN: no table for unit]"; pen.append("no mass data " + h["name"])
        else: core = core and f" ({core})"
        s0 = f"{fstr(q) if q is not None else ''} {u}{core}".strip()
        tail = ("" if h["name"] == u else " " + h["name"]) + tax + v
        if h.get("proxy"): tail += f" [PROXY: {h['proxy']}]"; pen.append("proxy-derived mass " + h["name"])
        hl.append((f"[Inferred: {s0}]" if inf else s0) + tail)
        for part in h.get("parts", []):
            if not part or len(part) < 2: continue
            tx = f" (*{part[2]}*)" if len(part) > 2 and part[2] else ""
            hl.append(f"  - {part[0]} parts {part[1]}{tx}")
    ml = []
    for i in items:
        v = vt(i)
        if i.get("egg_of"): ml.append((i["_i"], f"{tr(i['m'], 1)} g {i['name']}{v}")); continue
        tax = f" (*{i['taxon']}*)" if i.get("taxon") else ""
        if i.get("cat") == "spice": ml.append((i["_i"], f"{tr(i['m'], 2)} g {i['name']}, {i.get('state', 'ground')}{tax}{v}"))
        elif i.get("phase") == "fluid" and i.get("rho"):
            eo = f" [{tr(i['eo_pct'], 4)}% EO]" if i.get("eo_pct") is not None else ""
            ml.append((i["_i"], f"{tr(i['m'], 1)} g = {tr(i['m'] / i['rho'], 1)} ml {i['name']}{eo}{tax}{v}"))
        elif i.get("cat") in SOTT: ml.append((i["_i"], f"{tr(i['m'], 2)} g {i['name']}{tax}{v}"))
        else: ml.append((i["_i"], f"{tr(i['m'], 1)} g {i['name']}{tax}{v}"))
    ml = [x[1] for x in sorted(ml, key=lambda x: x[0])]
    for s in surf: ml.append(f"{tr(s['density_g_cm2'], 3)} g/cm² {s['name']}" + (f" (*{s['taxon']}*)" if s.get("taxon") else ""))
    aw = {}
    for m in mats:
        arch = tg.get(m, {}).get("critical_chemical_constraints", {}).get("hydration_archetype", "MATRIC_UNSPECIFIED")
        c, r, cl = calc_aw([i for i in items if i["sub_matrix"] == m], arch)
        aw[m] = {"aw": c, "raw": r, "clamped": cl}
        if cl:
            notes.append(f"aw [{m}] clamped {r:.4f}->{c:.4f}")
            if r < AWF.get(arch, (.5, .999))[0]: pen.append("aw below archetype floor")
    mx = max((v["aw"] for v in aw.values()), default=1.)
    def perishable(i):
        if i.get("cat") in ALWAYS_PERISHABLE or i.get("perishable") is True: return True
        if i.get("cat") in ALWAYS_STABLE or i.get("perishable") is False: return False
        notes.append(f"perishable undeclared for {i['name']}: treated as perishable"); return True
    per = any([perishable(i) for i in items])
    if mx >= .95 or (per and mx > .85): stor, sh = "Refrigerated +4 °C", 48 if mx >= .95 else 96
    elif mx >= .6: stor, sh = "Ambient", 48
    else: stor, sh = "Ambient", 168
    tw = {}
    for m, t in tg.items():
        tt, ha = t.get("target_type"), t.get("critical_chemical_constraints", {}).get("hydration_archetype")
        tw[m] = "DATA UNKNOWN" if ha in (None, "MATRIC_UNSPECIFIED") else [65, 75] if tt == "Gelatinization" else ([78, 82] if ha == "PROTEIN_COAGULUM" else [80, 85]) if tt == "Protein_Coagulation" else "DATA UNKNOWN"
    ok = not rh
    pen += (["rheology failed"] if rh else []) + (["boundary reached"] if bound else [])
    out = {"errors": err, "rheology_passed": ok, "rheology_errors": rh, "notes": notes,
           "FINAL_TOTAL_MASS": final, "matrix_mass_g": M, "geometry": geo,
           "density": {m: {"rho": v[0], "err": v[1]} for m, v in dens.items()}, "aw": aw, "evap_factor": ev,
           "checks": {"V1-V5": "FAIL" if err else "OK", "L6": L6, "L7": L7, "L8": L8, "rheology": "OK" if ok else "FAIL"},
           "convergence": "BOUNDARY_REACHED" if bound else "SUCCESS", "residual_loss": max((abs(sum(i["m"] for i in items if i["sub_matrix"] == m) - M[m]) for m in mats), default=0.),
           "thermal_window_C": tw, "haccp": {"storage": stor, "shelf_life_h": sh},
           "confidence": "HIGH" if not pen else "MEDIUM" if len(set(pen)) == 1 else "LOW", "penalties": sorted(set(pen)),
           "hist_lines": hl, "modern_lines": ml,
           "starch_sat": {m: sum(i["m"] for i in items if i["sub_matrix"] == m and "starch" in i.get("function", "")) / M[m] for m in mats if M[m]},
           "state": {"python": True, "sig": hashlib.sha1("\n".join(x.strip() for x in hl + ml).encode("utf-8")).hexdigest()[:8], "arch": ",".join(sorted({t.get("critical_chemical_constraints", {}).get("hydration_archetype", "?") for t in tg.values()})),
                     "m_bal_dev": max((abs(sum(i["m"] for i in items if i["sub_matrix"] == m) - M[m]) / M[m] for m in mats if M[m]), default=0.)}}
    loop = p.get("loop", 1)
    vs = list(dict.fromkeys(i.get("variant") for i in items)) or [None]
    def tline(g):
        its = [i for i in items if i.get("variant") == g]; t = sum(i["m"] for i in its)
        f = t - sum(i["m"] for i in its if i.get("phase") == "fluid") * (1 - ev)
        lab = "" if len(vs) <= 1 else " (base)" if g is None else f" (variant: {g})"
        return f"Total Mass Balance{lab}: FINAL_TOTAL_MASS {tr(t, 1)} g -> Target Finished Output {tr(f, 1)} g"
    bad = [k for k in ("L6", "L7", "L8") if out["checks"][k] == "FAIL"] + (["V1-V5"] if err else [])
    conv = "CONVERGENCE_PARTIAL" if not ok and loop >= 3 else out["convergence"]
    if not ok and loop >= 3: out["confidence"] = "LOW"
    awl = "; ".join(f"{m} {tr(v['aw'], 3)}" + (f" (raw {tr(v['raw'], 3)}, clamped)" if v["clamped"] else "") for m, v in aw.items())
    arch = out["state"]["arch"]
    r = {"telemetry": [f"System Confidence Score: {out['confidence']} (Reason: {', '.join(out['penalties']) or 'no penalties'})",
                       f"Solver Convergence: {conv} in {loop} run(s). Residual Loss: {out['residual_loss']:.3e}",
                       *[tline(g) for g in vs],
                       f"Validation Telemetry: Mass Balance {'FAIL' if err else 'OK'} | Water Activity (aw): {awl} | Rheological Match: {arch} | Drift Shield: ACTIVE",
                       "Linter Map: " + ("L1-L17 OK" if not bad else "engine FAIL " + ",".join(bad))],
         "density": [f"Pre-bake {m} Density: {tr(v[0], 3)} ± {tr(v[1], 3)} g/cm³" for m, v in dens.items()],
         "windows": "Processing Temperature Window: " + "; ".join(f"{m}: " + (f"{w[0]}–{w[1]} °C" if isinstance(w, list) else w) for m, w in tw.items()),
         "haccp": [f"Storage Temperature Control: {stor}", f"Target Shelf Life: {sh} h"]}
    if geo:
        def fm(n, c, D):
            a_, b_, c_, d_, e_ = c
            return f"{n} = {a_}" if not b_ or not d_ else f"{n} = {a_} + ({b_} / ({c_} + e^({d_} * ({D} - {e_}))))"
        D = geo["D"]
        r["geometry"] = [fm("crust_thickness", geo["crust_coef"], D), fm("filling_height", geo["filling_coef"], D),
                         "dough = π * crustDensity * (D^2/4 + (D - crust_thickness) * (filling_height + merlon)) * crust_thickness; filling = (π/4) * fillingDensity * (D - 2*crust_thickness)^2 * filling_height",
                         f"Final Crust Thickness {tr(geo['crust_thickness_cm'] * 10, 2)} mm | Filling Height {tr(geo['filling_height_cm'], 3)} cm | Scaled Dough Mass {tr(geo['dough_g'] or 0, 1)} g | Scaled Filling Mass {tr(geo['filling_g'] or 0, 1)} g (D={D} cm, merlon={geo['merlon']} cm)"]
    out["render"] = r
    out["state"].update({"loop": loop, "conf": out["confidence"]})
    if not full:
        out = {k: out[k] for k in ("errors", "rheology_passed", "rheology_errors", "notes", "confidence", "penalties", "hist_lines", "modern_lines", "render", "state")}
    if full: out["egg"] = egg
    if full: out["ingredients"] = [{"name": i["name"], "sub_matrix": i["sub_matrix"], "Mod_Mass": i["m"], "track": i["track"], "clamp": i.get("clamp")} for i in items]
    return out
_Q = r"(?P<q>\d+ \d+/\d+|\d+/\d+|\d+)"
_N = r"\d+\.\d+"
_M = rf"(?P<m>{_N} g(?: = {_N} ml)?|{_N} g albumen \+ {_N} g yolk|{_N} g (?:albumen|yolk))"
H_PLAIN = re.compile(rf"^{_Q} (?P<u>[^()\[\]]+?) \({_M}\)(?P<t>.*)$")
H_INF = re.compile(rf"^\[Inferred: {_Q} (?P<u>[^()\[\]]+?) \({_M}\)\](?P<t>.*)$")
H_NOTBL = re.compile(rf"^{_Q} (?P<u>[^()\[\]]+?) \[DATA UNKNOWN: no table for unit\](?P<t>.*)$")
H_UNK = re.compile(r"^\[Inferred: DATA UNKNOWN\](?P<t>.*)$")
H_PART = re.compile(r"^\s*- (?P<n>\d+(?:\.\d+)?(?:\s*/\s*\d+)?) parts (?P<t>.+)$")
M_MAIN = re.compile(rf"^(?P<g>{_N}) g (?:= {_N} ml )?(?P<t>.+)$")
M_UNK = re.compile(r"^DATA UNKNOWN (?P<t>.+)$")
M_SURF = re.compile(rf"^{_N} g/cm² (?P<t>.+)$")
T_PROXY, T_VAR, T_TAX, T_EO = (re.compile(x) for x in (r"\s*\[PROXY: [^\]]*\]$", r"\s*\(variant: (?P<v>[^)]+)\)$", r"\s*\(\*?(?P<x>[A-Z][^*)]*)\*?\)$", r"\s*\[\d+\.\d+% EO\]$"))
HEADERS = ["## Technical Analysis (TA)", "### Inferred Technological Targets", "### Mathematical & Optimizer Telemetry", "### Pre-Bake Density Analytics",
           "### Rheological & Environmental Windows", "## Historical Concordance & Verification", "## Historical List of Ingredients", "## Modern List of Ingredients",
           "## Modern Procedure", "## Operational Mise en Place & Service Logistics", "## Food Safety & Preservation (HACCP Track)", "## Rheological Contingency Protocols",
           "## Modern Palatability & Sensorial Adaptation", "## Substitutions", "## Batch Comparative Analysis"]
def _tail(t, proxy=False):
    t = t.strip()
    if proxy: t = T_PROXY.sub("", t)
    v = T_VAR.search(t); t = T_VAR.sub("", t) if v else t
    x = T_TAX.search(t); t = T_TAX.sub("", t) if x else t
    t = T_EO.sub("", t)
    return t.strip(), x.group("x") if x else None, v.group("v") if v else None
def _section(lines, title):
    out, on = [], False
    for ln in lines:
        h = ln.strip().lstrip("#").strip().lower()
        if on and (ln.lstrip().startswith("#") or ln.lstrip().startswith("<details") or h in ("historical list of ingredients", "modern list of ingredients")): break
        if h == title: on = True; continue
        if on and ln.strip(): out.append(ln.rstrip())
    return out, on
def check(text):
    """Lint a dossier (or only its two ingredient lists). Returns [(level, message)], level FAIL|WARN."""
    R = []
    F = lambda m: R.append(("FAIL", m))
    W = lambda m: R.append(("WARN", m))
    lines = text.replace("\r\n", "\n").split("\n")
    hs, hs_on = _section(lines, "historical list of ingredients")
    ms, ms_on = _section(lines, "modern list of ingredients")
    if not hs_on: F("section 'Historical List of Ingredients' not found")
    if not ms_on: F("section 'Modern List of Ingredients' not found")
    full = any(l.startswith("## Technical Analysis") for l in lines)
    notes = " ".join(l for l in lines if l.lstrip().startswith("- Notes:")).lower()
    sig = re.search(r'"sig"\s*:\s*"([0-9a-f]{8})"', text)
    py = re.search(r'"python"\s*:\s*(true|false)', text)
    if full:
        if not lines[0].startswith("## ") or " — " not in lines[0]: F("first line must be '## [ID] — [Title]'")
        pos = -1
        for h in HEADERS:
            at = next((n for n, l in enumerate(lines) if l.strip() == h), -1)
            if at < 0: F(f"missing header: {h}")
            elif at < pos: F(f"header out of order: {h}")
            else: pos = at
        if not py: F("State block missing (the last block must hold the hcr_state JSON)")
        elif py.group(1) == "true" and not sig: F("State has python:true but no sig")
        if "<details>" in text and text.rstrip().rfind("</details>") < text.rfind("<details>"): F("State block not closed")
    heads, parts_of, hkeys, taxa = [], {}, set(), {}
    cur, inf_unknown, unk_keys, wunits, vunits = None, 0, [], set(), set()
    hdec = {}
    for ln in hs:
        pm = H_PART.match(ln)
        if pm:
            n, x, v = _tail(pm.group("t"))
            if cur is None: F(f"blend component without a blend line: {ln.strip()}"); continue
            parts_of[cur].append(n.lower())
            if x: taxa.setdefault((cur[1], x.lower()), []).append(n)
            continue
        m = H_INF.match(ln) or H_PLAIN.match(ln) or H_NOTBL.match(ln) or H_UNK.match(ln)
        if not m:
            why = "unrecognised shape"
            if re.search(r"\(\d+ (?:g|ml)[ )]", ln): why = "mass without decimals (masses are rounded to 1-3 decimals, never integers)"
            elif re.match(rf"^\[Inferred: {_Q} \S+ \([^)]*\) [^\]]*\]$", ln): why = "name inside the [Inferred: ...] bracket (the name follows the bracket)"
            elif re.match(rf"^{_Q} \S+ [^(\[]+\(\d", ln): why = "mass must directly follow the unit: 'Q unit (X.X g) name'"
            elif re.match(rf"^{_Q} \S+ [^(\[]", ln) or re.match(rf"^{_Q} \S+$", ln): why = "quantity without its mass: write 'Q unit (X.X g)' or [DATA UNKNOWN: no table for unit]"
            elif re.search(r"albumen|yolk", ln): why = "egg line must read 'N unit (A.A g albumen + Y.Y g yolk)'"
            elif "DATA UNKNOWN" in ln: why = "DATA UNKNOWN shape: '[Inferred: DATA UNKNOWN] name'"
            F(f"historical line: {why} <- {ln.strip()}")
            cur = None
            continue
        gd = m.groupdict()
        is_unk = m.re is H_UNK
        name, x, v = _tail(gd["t"], True)
        if "u" in gd and not name: name = gd["u"]
        if not name: F(f"historical line without a name <- {ln.strip()}"); cur = None; continue
        if re.search(r"[\[\]()]", name): F(f"historical line: comment or bracket after the name (comments go to Notes) <- {ln.strip()}"); cur = None; continue
        if "q" in gd:
            q = frac(gd["q"])
            if q is None or q.denominator not in ALLOWED_DEN: F(f"quantity denominator must be 1,2,3,4,6,8,12 <- {ln.strip()}")
        k = (name.lower(), v)
        if is_unk: inf_unknown += 1; unk_keys.append(k)
        if gd.get("m") and "albumen" not in gd["m"] and "yolk" not in gd["m"] and gd["u"].lower() != name.lower():
            (vunits if " ml" in gd["m"] else wunits).add(gd["u"])
        if gd.get("m"):
            hdec[k] = len(gd["m"].split(" ")[0].split(".")[1])
            if hdec[k] >= 2 and float(gd["m"].split(" ")[0]) >= 10: W(f"historical mass with 2 decimals is >= 10 g: 2 decimals are for spices/salt/drugs only, solids and fluids take 1 <- {ln.strip()}")
        if k in hkeys: F(f"historical line repeated (same name and variant): {name}")
        hkeys.add(k)
        egg_types = []
        if gd.get("m"):
            if "albumen" in gd["m"]: egg_types.append("albumen")
            if "yolk" in gd["m"]: egg_types.append("yolk")
        cur = k; parts_of[k] = []
        heads.append((k, egg_types))
        if x: taxa.setdefault((v, x.lower()), []).append(name)
    for (v, x), names in taxa.items():
        if len(set(n.lower() for n in names)) > 1: W(f"one taxon (*{x}*) under several terms {sorted(set(names))}: one term per concept")
    if inf_unknown: W(f"{inf_unknown} line(s) '[Inferred: DATA UNKNOWN]': allowed only when no measure table (input or fetched source) covers the ingredient")
    known = set()
    for (n, v), ps in parts_of.items():
        known.add((n, v)); known.update((p, v) for p in ps)
    comps = {p for ps in parts_of.values() for p in ps}
    known_names = {n for n, _ in known} | {"albumen", "yolk"}
    mrows, seen, masses, round_rows, mfluid = [], {}, {}, [], {}
    for ln in ms:
        um = M_UNK.match(ln)
        if um: F(f"modern line DATA UNKNOWN: every ingredient has a modern mass from physics (seed) <- {ln.strip()}"); n, x, v = _tail(um.group("t")); mrows.append((n.lower(), v)); continue
        if M_SURF.match(ln): continue
        m = M_MAIN.match(ln)
        if not m:
            F(f"modern line: unrecognised shape (expected 'X.X g name', 'X.X g = Y.Y ml name', 'X.XX g name, ground', 'DATA UNKNOWN name') <- {ln.strip()}")
            continue
        n, x, v = _tail(m.group("t"))
        g = m.group("g"); val = float(g)
        cands = [n.lower()] + ([n.rsplit(", ", 1)[0].lower()] if ", " in n else [])
        name = next((c for c in cands if c in known_names), None)
        if name is None:
            F(f"modern name not in the historical list (names stay in the source language, preparation words go to the Procedure) <- {ln.strip()}"); name = cands[0]
        want = 1 if " ml " in ln else 2 if (name in comps or hdec.get((name, v), 1) >= 2) and name not in ("albumen", "yolk") else 1
        mfluid[(name, v)] = " ml " in ln
        if len(g.split(".")[1]) != want and not ((name, v) not in hdec and name not in comps and " ml " not in ln and len(g.split(".")[1]) in (1, 2)): F(f"modern mass needs {want} decimal(s) (solids and fluids 1; spices, salt 2) <- {ln.strip()}")
        if val <= 0: F(f"modern mass must be > 0 (a floor applies) <- {ln.strip()}")
        if v is not None and not any(hv == v for _, hv in hkeys): F(f"variant '{v}' has no historical line <- {ln.strip()}")
        mrows.append((name, v)); seen[(name, v)] = seen.get((name, v), 0) + 1
        if abs(val - round(val)) < 1e-9 or abs(val % 1 - .5) < 1e-9: round_rows.append(ln.strip())
        masses.setdefault((g, v), []).append(name)
    for (n, v), c in seen.items():
        if c > 1 and n not in ("albumen", "yolk"): F(f"modern term repeated (one row per ingredient and variant): {n}")
        if c > 1 and n in ("albumen", "yolk"): F(f"egg: one {n} row per variant")
    for (g, v), names in masses.items():
        if len(set(names)) > 1 and float(g) >= 1: W(f"different ingredients with the same mass {g} g: {sorted(set(names))} (copied value?)")
    for k in unk_keys:
        us = vunits if mfluid.get(k) else wunits
        if us: F(f"'{k[0]}': [Inferred: DATA UNKNOWN] although a measure table is in use ({', '.join(sorted(us))}): retro-convert the modern mass (K-A cascade step 2)")
    have = set(mrows)
    for (n, v), egg_types in heads:
        ps = parts_of[(n, v)]
        if egg_types:
            need = [(t, v) for t in egg_types]
        elif ps:
            need = [(p, v) for p in ps]
        else:
            need = [(n, v)]
        for nd in need:
            if nd not in have: F(f"no modern row for historical ingredient '{nd[0]}'" + (f" (variant: {v})" if v else ""))
    ok_sig = False
    if sig and py and py.group(1) == "true":
        calc = hashlib.sha1("\n".join(x.strip() for x in hs + ms).encode("utf-8")).hexdigest()[:8]
        if calc != sig.group(1): F(f"State sig {sig.group(1)} does not match the printed lists ({calc}): lines were edited or the engine did not run")
        else: ok_sig = True
    if round_rows and not ok_sig:
        just = any(k in notes for k in KEYS)
        for r_ in round_rows: W(f"mass ends in .0/.5 (arithmetic skipped?) <- {r_}")
        if len(round_rows) >= max(2, -(-len(mrows) // 3)) and not just:
            F(f"{len(round_rows)} of {len(mrows)} modern masses end in .0/.5: the projection was skipped (L1)")
    return R
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if "--check" in sys.argv:
        res = check(open(a[0], encoding="utf-8").read() if a else sys.stdin.read())
        for lv, msg in res: print(f"{lv}: {msg}")
        nf = sum(lv == "FAIL" for lv, _ in res)
        print("CHECK OK" + (f" ({len(res)} warning(s))" if res else "") if not nf else f"CHECK FAIL: {nf} failure(s)")
        sys.exit(1 if nf else 0)
    p = json.load(open(a[0], encoding="utf-8") if a else sys.stdin)
    print(json.dumps(run(p, "--full" in sys.argv), ensure_ascii=False, separators=(",", ":")))
