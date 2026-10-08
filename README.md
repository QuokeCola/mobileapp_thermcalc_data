# ThermoCalc data

Steam tables for the [Thermo Calculator](https://github.com/QuokeCola/ThermoCalculator) app,
transcribed from Moran & Shapiro, *Fundamentals of Engineering Thermodynamics*, SI Tables A-2, A-3 and A-4.

| Path | What it is |
| --- | --- |
| `TableA*.csv`, `Convert*.py`, `output*.csv` | Raw transcriptions and the scripts that split them into columns. `output41.csv` … `output4C.csv` each hold two pressures of Table A-4. |
| `FinalTables/` | Cleaned Tables A-2 and A-3 as used by the 2020 app (no header; vf is ×10³). |
| `build_tables.py` | Combines everything, fixes known transcription errors, checks consistency and writes `steam/`. |
| `steam/` | Generated tables with headers, in bar, °C, m³/kg, kJ/kg, kJ/(kg·K). This is what the app bundles. |

Run `python3 build_tables.py` after editing any source table. It fails if a check does not pass:

- h = u + pv for saturated liquid, saturated vapor and every superheated point
- hfg = hg − hf and sg − sf = hfg / T on the saturation tables
- T and p increase down the saturation tables; v, u, h and s increase with T along each isobar

The corrections it applies are listed with their reasons in `CORRECTIONS` at the top of the script.
