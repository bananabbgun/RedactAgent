"""Summarise the robustness runs (degraded copies of v2) into eval/robustness/summary.json for the deck.

    python eval/robustness_summary.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LABELS = {"lowres": ("Low resolution", "{} DPI"), "blur": ("Blur", "radius {} px"), "jpeg": ("JPEG compression", "quality {}"),
          "rotate": ("Skewed scan", "{}°"), "fax": ("Fax / 1-bit", "{}")}
FAX = {"1": "clean threshold", "2": "threshold + speckle"}


def main():
    base = json.loads((ROOT / "results_b70" / "v2" / "metrics.json").read_text())
    rows = [{"kind": "clean", "label": "Clean (v2)", "level": "", "A": base["A_deterministic"]["recall"],
             "D": base["D_agentic"]["recall"], "P": base["D_agentic"]["precision"]}]
    for d in sorted((ROOT / "robustness").iterdir()):
        m = d / "metrics.json"
        if not m.exists():
            continue
        kind, level = d.name.split("_", 1)
        x = json.loads(m.read_text())
        name, fmt = LABELS[kind]
        rows.append({"kind": kind, "label": name, "level": FAX.get(level, fmt.format(level)) if kind == "fax" else fmt.format(level),
                     "A": x["A_deterministic"]["recall"], "D": x["D_agentic"]["recall"], "P": x["D_agentic"]["precision"]})
    (ROOT / "robustness" / "summary.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    for r in rows:
        print(f"{r['label']:18s} {r['level']:22s} rules {r['A']*100:5.1f}  full {r['D']*100:5.1f} / {r['P']*100:5.1f}")


if __name__ == "__main__":
    main()
