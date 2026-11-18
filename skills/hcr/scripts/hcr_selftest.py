"""HCR 4.1 tests. Run:  py hcr_selftest.py   -> SELFTEST OK"""
import copy, json, re, sys
from fractions import Fraction
from hcr_engine import check, egg_model, frac, fstr, retro, run, track

SAMPLE = {"year": 1390, "zone": 0, "evap_min": 5.0,
          "inferred_targets": [
              {"sub_matrix_name": "crust", "target_type": "Gluten_Network", "critical_chemical_constraints": {"hydration_archetype": "DOUGH_DENSE", "lipid_archetype": "FAT_SHORTENING"}},
              {"sub_matrix_name": "filling", "target_type": "Protein_Coagulation", "critical_chemical_constraints": {"hydration_archetype": "PROTEIN_COAGULUM", "lipid_archetype": "SOLUTE_OTHER"}}],
          "geometry": {"D": 24.0, "merlon": 0.0},
          "hist": [{"name": "farina", "cat": "flour", "qty_native": "1 1/2", "unit": "libbra", "unit_g": 339.5, "unit_src": "selftest table", "src_text": "1 1/2 libbra de farina"},
                   {"name": "strutto", "cat": "fat", "qty_native": "1/2", "unit": "libbra", "unit_g": 339.5, "unit_src": "selftest table", "src_text": "1/2 libbra de strutto"},
                   {"name": "acqua", "cat": "liquid", "qty_native": "1/2", "unit": "bicchiere", "unit_ml": 250, "fluid_rho": 1.0, "unit_src": "selftest table", "src_text": "1/2 bicchiere d'acqua"},
                   {"name": "uova", "cat": "other", "egg": True, "qty_native": "6", "unit": "uova", "src_text": "6 uova"},
                   {"name": "latte", "cat": "liquid", "qty_native": "1", "unit": "boccale", "unit_ml": 1000, "fluid_rho": 1.03, "unit_src": "selftest table", "src_text": "1 boccale de latte"},
                   {"name": "cannella", "cat": "spice", "qty_native": None, "unit": "grano", "unit_g": 0.05, "unit_src": "selftest table", "taxon": "Cinnamomum verum"}],
          "ingredients": [
              {"name": "farina", "sub_matrix": "crust", "cat": "flour", "phase": "solid", "function": "starch_network", "seed": 200, "hist_ref": "farina", "taxon": "Triticum aestivum", "ident": {"status": "KNOWN", "src": "input"}},
              {"name": "strutto", "sub_matrix": "crust", "cat": "fat", "phase": "lipid", "function": "lipid_plasticization", "seed": 80, "hist_ref": "strutto", "perishable": True, "ident": {"status": "KNOWN", "src": "input"}},
              {"name": "acqua", "sub_matrix": "crust", "cat": "liquid", "vol": True, "phase": "fluid", "function": "hydration", "seed": 100, "hist_ref": "acqua", "rho": 1.0, "perishable": False, "ident": {"status": "KNOWN", "src": "modern term"}},
              {"name": "egg", "sub_matrix": "filling", "egg": "albumen", "seed": 71.3, "hist_ref": "uova"},
              {"name": "egg", "sub_matrix": "filling", "egg": "yolk", "seed": 38.9, "hist_ref": "uova"},
              {"name": "latte", "sub_matrix": "filling", "cat": "liquid", "vol": True, "phase": "fluid", "function": "hydration", "seed": 300, "hist_ref": "latte", "rho": 1.03, "perishable": True, "ident": {"status": "KNOWN", "src": "input"}},
              {"name": "cannella", "sub_matrix": "filling", "cat": "spice", "phase": "solid", "function": "volatile_aromatic", "seed": 1, "hist_ref": "cannella", "i_ar": 1.5, "taxon": "Cinnamomum verum", "ident": {"status": "KNOWN", "src": "input"}}]}


def main():
    o = run(SAMPLE, True); assert not o["errors"], o["errors"]
    e = egg_model(1390, 0); assert abs(e["total_edible_g"] - 37.0055679) < 1e-6
    assert abs(sum(i["Mod_Mass"] for i in o["ingredients"]) - o["FINAL_TOTAL_MASS"]) < 1e-9
    assert track("flour", True) == "DRY_VOLUME" and track("spice", True) == "SOTTILE" and track("liquid", False) == "GROSSO"
    assert fstr(retro(101.0, 28.3)) and frac("1.5") is None and frac("1 1/2") == Fraction(3, 2)
    import copy
    def bad(mut):  # mutate a copy of SAMPLE; the engine must refuse
        q = copy.deepcopy(SAMPLE); mut(q); return run(q).get("errors")
    assert bad(lambda q: q["ingredients"][0].pop("ident"))                                   # identification required
    assert bad(lambda q: q["ingredients"][0]["ident"].pop("src"))                            # source required
    assert bad(lambda q: q["ingredients"][0].update(ident={"status": "UNKNOWN"}))            # unknown must be cat other
    assert bad(lambda q: q["ingredients"][0].update(cat="sugar"))                            # starch network never SOTTILE, any language
    q = copy.deepcopy(SAMPLE); q["hist"][0]["name"] = "farine de froment ancienne"; q["ingredients"][0].update(name="farine de froment ancienne", hist_ref="farine de froment ancienne", cat="other", ident={"status": "UNKNOWN"})
    assert not run(q)["errors"] and "unidentified" in " ".join(run(q)["penalties"])          # odd name accepted, never guessed
    assert "llerg" not in json.dumps(o)
    assert any(x.startswith("6 uova (") and "g albumen +" in x and "g yolk)" in x for x in o["hist_lines"])  # historical albumen and yolk totals
    assert bad(lambda q: q["ingredients"][3].update(egg=True))                                # egg row must be albumen or yolk
    assert len(o["state"]["sig"]) == 8
    assert bad(lambda q: q["hist"][0].pop("unit_src"))                                       # measure needs a source
    assert bad(lambda q: q["hist"][0].pop("src_text"))                                       # quantity needs the recipe text
    assert bad(lambda q: q["hist"][0].update(src_text="1 1/2 di farina"))                    # unit must occur in that text
    assert bad(lambda q: q["ingredients"][0].update(hist_ref="nessuna"))                     # every modern row has a historical row
    def blend(n):
        q = copy.deepcopy(SAMPLE)
        q["hist"].append({"name": "specie", "cat": "spice", "qty_native": "1", "unit": "grano", "unit_g": 0.05, "unit_src": "selftest table", "src_text": "1 grano de specie", "parts": [[2, "a", "A a"], [1, "b", "B b"]]})
        q["ingredients"] += [{"name": x, "sub_matrix": "filling", "cat": "spice", "phase": "solid", "function": "volatile_aromatic", "seed": 1, "hist_ref": "specie", "i_ar": 1.5, "ident": {"status": "KNOWN", "src": "input"}} for x in "ab"[:n]]
        return run(q, True)
    r2 = blend(2); assert not r2["errors"], r2["errors"]
    ma = {i["name"]: i["Mod_Mass"] for i in r2["ingredients"]}; assert abs(ma["a"] / ma["b"] - 2) < 1e-6   # components follow the parts
    assert blend(1)["errors"]                                                                 # one row for two parts = refused
    def dossier(r):
        return ("## Historical List of Ingredients\n" + "\n".join(r["hist_lines"]) + "\n## Modern List of Ingredients\n" + "\n".join(r["modern_lines"]) +
                "\n<details><summary>State</summary>\n" + json.dumps({"hcr_state": r["state"]}) + "\n</details>\n")
    assert not [x for x in check(dossier(o)) if x[0] == "FAIL"], check(dossier(o))           # the engine passes its own linter
    assert any("sig" in x[1] for x in check(dossier(o).replace(o["state"]["sig"], "00000000")))  # edited lines / no engine run are caught
    # variants, count nouns, unknown rows
    q = copy.deepcopy(SAMPLE)
    q["hist"] += [{"name": "latte", "variant": "senza carne", "cat": "liquid", "qty_native": "1", "unit": "boccale", "unit_ml": 1000, "fluid_rho": 1.03, "unit_src": "selftest table", "src_text": "1 boccale de latte"},
                  {"name": "mele", "cat": "other", "qty_native": None, "unit": "mele", "unit_g": 120, "unit_src": "selftest table"},
                  {"name": "specie fine", "cat": "spice", "qty_native": None, "blend": True, "units": [{"unit": "oncia", "unit_g": 28.3, "unit_src": "t"}, {"unit": "dramma", "unit_g": 3.54, "unit_src": "t"}, {"unit": "grano", "unit_g": 0.05, "unit_src": "t"}]}]
    q["inferred_targets"] += [{"sub_matrix_name": "senza carne", "target_type": "Emulsion", "critical_chemical_constraints": {"hydration_archetype": "LIQUID_THIN"}},
                              {"sub_matrix_name": "mele", "target_type": "Gelatinization", "critical_chemical_constraints": {"hydration_archetype": "MATRIC_UNSPECIFIED"}}]
    q["ingredients"] += [{"name": "latte", "variant": "senza carne", "sub_matrix": "senza carne", "cat": "liquid", "vol": True, "phase": "fluid", "function": "hydration", "seed": 250.3, "hist_ref": "latte", "rho": 1.03, "perishable": True, "ident": {"status": "KNOWN", "src": "input"}},
                         {"name": "mele", "sub_matrix": "mele", "cat": "other", "phase": "solid", "function": "other", "seed": 61.7, "hist_ref": "mele", "perishable": True, "ident": {"status": "KNOWN", "src": "input"}, "just": "integer count: one whole piece weighs the table value"},
                         {"name": "specie fine", "sub_matrix": "filling", "cat": "spice", "phase": "solid", "function": "volatile_aromatic", "seed": .7, "hist_ref": "specie fine", "ident": {"status": "RESEARCHED", "src": "selftest"}}]
    q["matrix_mass_g"] = {"mele": 120.0}
    r3 = run(q); assert not r3["errors"], r3["errors"]
    sf = [x for x in r3["hist_lines"] if x.endswith("specie fine")]; assert sf and sf[0].startswith("[Inferred: ") and " grano (" in sf[0], sf  # finest unit that fits (mass < 1 dramma)
    assert "blend composition unknown specie fine" in r3["penalties"] and not [x for x in r3["modern_lines"] if "DATA UNKNOWN" in x]
    u = copy.deepcopy(q); u["ingredients"][-1]["unknown"] = True; assert any("DATA UNKNOWN modern row" in x for x in run(u)["errors"])   # no unweighed rows
    u = copy.deepcopy(q); del u["inferred_targets"][-1]; assert any("L9" in x for x in run(u)["errors"])                                # every matrix has a target
    u = copy.deepcopy(q); u["hist"][2].update(qty_native=None, unit="libbra", unit_g=339.5, unit_ml=None); assert any("volumetric" in x for x in run(u)["errors"])  # inferred fluid: volume unit
    u = copy.deepcopy(q); u["hist"].append({"name": "sale", "cat": "salt", "qty_native": None, "unit": "oncia", "unit_g": 28.3, "unit_src": "t"}); assert any("without modern row" in x for x in run(u)["errors"])
    assert any(x.endswith("(variant: senza carne)") for x in r3["hist_lines"]) and any(x.endswith("(variant: senza carne)") for x in r3["modern_lines"])
    assert [x for x in r3["hist_lines"] if "mele" in x and x.count("mele") == 1 and x.startswith("[Inferred: ") and x.endswith(")]")]  # a count noun is written once
    assert sum(x.startswith("Total Mass Balance") for x in r3["render"]["telemetry"]) == 2        # one balance per variant
    assert not [x for x in check(dossier(r3)) if x[0] == "FAIL"], check(dossier(r3))
    assert bad(lambda q: q["ingredients"][0].update(name="flour"))                              # modern name = historical name
    assert bad(lambda q: q["hist"].append(dict(q["hist"][0])))                                  # one historical line per name and variant
    w = copy.deepcopy(q); w["ingredients"][-3]["sub_matrix"] = "filling"                         # a matrix never mixes variants
    assert any("mixes variants" in x for x in run(w)["errors"])
    two0 = "## Historical List of Ingredients\n{}\n## Modern List of Ingredients\n{}\n"
    # the linter rejects the shapes seen in real model output
    for ln in ("4 pome (600 g)", "2 ovo (100 g)", "[Inferred: 16 3/4 once (679.1 g) pome]", "2 boccale", "1 pizzico zaffarano (0.1 g) extra (", "[Inferred: DATA UNKNOWN]"):
        assert [x for x in check("## Historical List of Ingredients\n" + ln + "\n## Modern List of Ingredients\n1.1 g pome\n") if x[0] == "FAIL" and "historical line" in x[1]], ln
    assert any("bracket" in x[1] for x in check(two0.format("2 ovo (49.5 g albumen + 27.4 g yolk) [Inferred: count absent]", "49.5 g albumen\n27.4 g yolk")))
    assert not [x for x in check(two0.format("4 libbra sottile (1355.5 g) pome", "450.3 g pome")) if x[0] == "FAIL"]                    # multi-word unit
    assert any("measure table is in use" in x[1] for x in check(two0.format("4 libbra (1355.5 g) pome\n[Inferred: DATA UNKNOWN] zucharo", "450.3 g pome\n20.7 g zucharo")))
    assert any("modern line DATA UNKNOWN" in x[1] for x in check(two0.format("[Inferred: DATA UNKNOWN] uve", "DATA UNKNOWN uve")))
    assert any("source language" in x[1] for x in check("## Historical List of Ingredients\n4 pome (60.3 g)\n## Modern List of Ingredients\n296.4 g apples\n"))
    assert any("> 0" in x[1] for x in check("## Historical List of Ingredients\n4 pome (60.3 g)\n## Modern List of Ingredients\n0.0 g pome\n"))
    q = copy.deepcopy(SAMPLE); q["hist"].append({"name": "zucharo", "cat": "sugar", "qty_native": "2", "unit": "once", "unit_g": 28.3, "unit_src": "selftest table", "src_text": "2 once de zucharo"})
    q["ingredients"].append({"name": "zucharo", "sub_matrix": "filling", "cat": "sugar", "phase": "solid", "function": "osmotic_solute", "seed": 17.3, "hist_ref": "zucharo", "ident": {"status": "KNOWN", "src": "input"}})
    r4 = run(q); assert not r4["errors"], r4["errors"]
    assert any(re.fullmatch(r"\d+\.\d g zucharo", x) for x in r4["modern_lines"]), r4["modern_lines"]   # sugar: 1 decimal
    assert any(re.fullmatch(r"\d+\.\d g(?: = \d+\.\d ml)? (farina|latte|acqua)", x) for x in r4["modern_lines"])  # solids, fluids: 1 decimal
    assert not [x for x in check(dossier(r4)) if x[0] == "FAIL"], check(dossier(r4))
    two = "## Historical List of Ingredients\n{}\n## Modern List of Ingredients\n{}\n"
    assert any("decimal" in x[1] for x in check(two.format("2 once (56.6 g) zucharo", "17.35 g zucharo")))
    assert any("decimal" in x[1] for x in check(two.format("4 pome (60.3 g)", "296.45 g pome")))
    print("SELFTEST OK")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
