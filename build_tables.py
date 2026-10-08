"""Build the cleaned steam tables used by the ThermoCalc app.

Reads the converted textbook tables (FinalTables/SITableA2.csv,
FinalTables/SITableA3.csv and output41.csv ... output4C.csv), applies the
transcription fixes listed in CORRECTIONS, checks the data for internal
consistency and writes three CSV files with header rows into steam/:

    saturated_by_temperature.csv   (Table A-2)
    saturated_by_pressure.csv      (Table A-3)
    superheated.csv                (Table A-4, one row per (p, T) point)

Units: T in degC, p in bar, v in m^3/kg, u and h in kJ/kg, s in kJ/(kg*K).
Note that the source A-2/A-3 tables list vf multiplied by 10^3; the output
stores plain m^3/kg.

Run:  python3 build_tables.py          (exits non-zero if a check fails)
"""

import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "steam")

SAT_COLUMNS = ["vf", "vg", "uf", "ug", "hf", "hfg", "hg", "sf", "sg"]

# Pressures (bar) and saturation temperatures (degC) of each A-4 sub-table,
# in the order the converted files list them (two pressures per file).
# None means the pressure is above the critical point.
SUPERHEATED_FILES = [
    ("output41.csv", (0.06, 36.16), (0.35, 72.69)),
    ("output42.csv", (0.7, 89.95), (1.0, 99.63)),
    ("output43.csv", (1.5, 111.37), (3.0, 133.55)),
    ("output44.csv", (5.0, 151.86), (7.0, 164.97)),
    ("output45.csv", (10.0, 179.91), (15.0, 198.32)),
    ("output46.csv", (20.0, 212.42), (30.0, 233.90)),
    ("output47.csv", (40.0, 250.4), (60.0, 275.64)),
    ("output48.csv", (80.0, 295.06), (100.0, 311.06)),
    ("output49.csv", (120.0, 324.75), (140.0, 336.75)),
    ("output4A.csv", (160.0, 347.44), (180.0, 357.06)),
    ("output4B.csv", (200.0, 365.81), (240.0, None)),
    ("output4C.csv", (280.0, None), (320.0, None)),
]

# Transcription errors found by the consistency checks below.
# (table, row key, column, wrong value, corrected value, reason)
CORRECTIONS = [
    ("A2", 260.0, "hg", 2796.6, 2796.9, "ug + p*vg = 2796.9 and hf + hfg = 2796.9"),
    ("A3", 3.5, "ug", 2546.9, 2548.9, "hg - p*vg = 2548.9"),
    ("A3", 4.5, "uf", 622.25, 622.77, "hf - p*vf = 622.77"),
    ("A3", 20.0, "sg", 6.340, 6.3409, "4th decimal lost; A-4 Sat. row gives 6.3409"),
    ("A3", 30.0, "sg", 6.186, 6.1869, "4th decimal lost; A-4 Sat. row gives 6.1869"),
    ("A3", 40.0, "sg", 6.070, 6.0701, "4th decimal lost; A-4 Sat. row gives 6.0701"),
    ("A3", 60.0, "sg", 5.889, 5.8892, "4th decimal lost; A-4 Sat. row gives 5.8892"),
    ("A3", 80.0, "sg", 5.743, 5.7432, "4th decimal lost; A-4 Sat. row gives 5.7432"),
    ("A3", 100.0, "sg", 5.614, 5.6141, "4th decimal lost; A-4 Sat. row gives 5.6141"),
    ("A4", (180.0, 520.0), "h", 3378.0, 3328.0, "u + p*v = 3328.1"),
]


def read_rows(path):
    with open(path, newline="") as f:
        for row in csv.reader(f):
            cells = [c.strip() for c in row]
            if any(cells):
                yield cells


def read_saturation(path):
    """Return a list of dicts keyed by 'key', 'other' and SAT_COLUMNS."""
    table = []
    for cells in read_rows(path):
        values = [float(c) for c in cells if c != ""]
        if len(values) != 11:
            raise ValueError(f"{path}: expected 11 values, got {cells}")
        row = dict(zip(["key", "other"] + SAT_COLUMNS, values))
        row["vf"] /= 1000.0
        table.append(row)
    return table


def read_superheated():
    """Return a list of dicts with p, Tsat, T (None for the Sat. row), v, u, h, s."""
    points = []
    for name, *pressures in SUPERHEATED_FILES:
        rows = list(read_rows(os.path.join(HERE, name)))
        for half, (p, tsat) in enumerate(pressures):
            for cells in rows:
                vals = cells[1 + 4 * half:5 + 4 * half]
                if not vals or vals[0] == "":
                    continue
                t = None if cells[0].lower().startswith("sat") else float(cells[0])
                v, u, h, s = map(float, vals)
                points.append({"p": p, "Tsat": tsat, "T": t, "v": v, "u": u, "h": h, "s": s})
    return points


def apply_corrections(a2, a3, a4):
    for table, key, column, wrong, right, _ in CORRECTIONS:
        if table == "A4":
            rows = [r for r in a4 if (r["p"], r["T"]) == key]
        else:
            rows = [r for r in (a2 if table == "A2" else a3) if r["key"] == key]
        if len(rows) != 1:
            raise ValueError(f"correction target {table} {key} not found")
        row = rows[0]
        if abs(row[column] - wrong) > 1e-9:
            raise ValueError(f"{table} {key} {column}: expected {wrong}, found {row[column]}")
        row[column] = right


def check(a2, a3, a4):
    problems = []

    def expect(cond, msg):
        if not cond:
            problems.append(msg)

    for label, table, by_temp in (("A2", a2, True), ("A3", a3, False)):
        prev = None
        for r in table:
            t, p = (r["key"], r["other"]) if by_temp else (r["other"], r["key"])
            kpa = p * 100.0
            k = r["key"]
            expect(abs(r["hf"] - (r["uf"] + kpa * r["vf"])) < 0.3, f"{label} {k}: hf != uf + p*vf")
            expect(abs(r["hg"] - (r["ug"] + kpa * r["vg"])) < 1.0, f"{label} {k}: hg != ug + p*vg")
            expect(abs(r["hg"] - r["hf"] - r["hfg"]) < 0.15, f"{label} {k}: hfg != hg - hf")
            if r["hfg"] > 0:
                sfg = r["hfg"] / (t + 273.15)
                expect(abs(r["sg"] - r["sf"] - sfg) < 0.003, f"{label} {k}: sg - sf != hfg/T")
            if prev is not None:
                expect(t > prev[0] and p > prev[1], f"{label} {k}: T and p not increasing")
            prev = (t, p)

    by_pressure = {}
    for r in a4:
        by_pressure.setdefault(r["p"], []).append(r)
    for p, rows in by_pressure.items():
        prev = None
        for r in rows:
            where = f"A4 p={p} T={r['T'] or 'Sat'}"
            expect(abs(r["h"] - (r["u"] + p * 100.0 * r["v"])) < 1.0, f"{where}: h != u + p*v")
            vals = (r["v"], r["u"], r["h"], r["s"])
            if prev is not None:
                expect(all(a > b for a, b in zip(vals, prev)), f"{where}: v, u, h, s not increasing in T")
            prev = vals
            if r["T"] is not None and r["Tsat"] is not None:
                expect(r["T"] > r["Tsat"], f"{where}: tabulated below Tsat")
    return problems


def write_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def fmt(x):
    return f"{x:.10g}"


def main():
    a2 = read_saturation(os.path.join(HERE, "FinalTables", "SITableA2.csv"))
    a3 = read_saturation(os.path.join(HERE, "FinalTables", "SITableA3.csv"))
    a4 = read_superheated()
    apply_corrections(a2, a3, a4)
    problems = check(a2, a3, a4)
    if problems:
        print("\n".join(problems))
        sys.exit(1)

    os.makedirs(OUT_DIR, exist_ok=True)
    write_csv(
        os.path.join(OUT_DIR, "saturated_by_temperature.csv"),
        ["T", "p"] + SAT_COLUMNS,
        [[fmt(r["key"]), fmt(r["other"])] + [fmt(r[c]) for c in SAT_COLUMNS] for r in a2],
    )
    write_csv(
        os.path.join(OUT_DIR, "saturated_by_pressure.csv"),
        ["p", "T"] + SAT_COLUMNS,
        [[fmt(r["key"]), fmt(r["other"])] + [fmt(r[c]) for c in SAT_COLUMNS] for r in a3],
    )
    # The Sat. row of each sub-table is written at T = Tsat with saturated = 1.
    rows = []
    for r in a4:
        t = r["Tsat"] if r["T"] is None else r["T"]
        rows.append([fmt(r["p"]), fmt(t), "1" if r["T"] is None else "0"]
                    + [fmt(r[c]) for c in ("v", "u", "h", "s")])
    write_csv(os.path.join(OUT_DIR, "superheated.csv"), ["p", "T", "saturated", "v", "u", "h", "s"], rows)
    print(f"wrote {len(a2)} A-2 rows, {len(a3)} A-3 rows, {len(a4)} A-4 points to {OUT_DIR}")


if __name__ == "__main__":
    main()
