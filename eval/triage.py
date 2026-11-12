"""Review triage: can the system tell which pages still leak, so reviewers spend their attention there?

    python eval/triage.py eval/triage/v1 eval/triage/v2 [--rule "risk>=50|warn|pending"]

Per page signals (stored by eval/evaluate.py): the agentic check's re-identification risk score, ink the OCR did
not read (warnings), unconfirmed suggestions, findings added by the agent, retried LLM calls. A page "leaks" if the
full system (ablation D) missed at least one ground-truth item. For each candidate rule the script reports the
share of pages flagged for full review and the share of leaking pages / missed items that fall in that set.
"""

from __future__ import annotations

import argparse
import json
from itertools import product
from pathlib import Path


def pages(run: Path) -> list[dict]:
    missed: dict[str, int] = {}
    for m in json.loads((run / "errors.json").read_text())["D_agentic"]["missed"]:
        missed[m["doc"]] = missed.get(m["doc"], 0) + 1
    out = []
    for f in sorted((run / "raw").glob("*.json")):
        r = json.loads(f.read_text())
        fs = r.get("findings", [])
        out.append({
            "doc": f.stem, "missed": missed.get(f.stem, 0),
            # residual risk (second attack round, RA_AGENT_ROUNDS=2) when available, else the first-round score
            "risk": (r.get("risk") or {}).get("residual", (r.get("risk") or {}).get("score", 0)) or 0,
            "warn": len(r.get("warnings") or []),
            "pending": sum(1 for x in fs if not x.get("accepted", True)),
            "agent": sum(1 for x in fs if "agent" in (x.get("sources") or [])),
            "retries": (r.get("tokens") or {}).get("llm_retries", 0) + (r.get("tokens") or {}).get("agent_retries", 0),
        })
    return out


def flag(p: dict, risk: int, warn: bool, pending: bool, agent: bool) -> bool:
    return (p["risk"] >= risk) or (warn and p["warn"] > 0) or (pending and p["pending"] > 0) or (agent and p["agent"] > 0) \
        or p["retries"] > 0


def evaluate(ps: list[dict], rule) -> dict:
    fl = [p for p in ps if flag(p, *rule)]
    leaky = [p for p in ps if p["missed"]]
    return {"flagged": len(fl), "pages": len(ps), "leaky": len(leaky),
            "leaky_flagged": sum(1 for p in fl if p["missed"]),
            "missed_items": sum(p["missed"] for p in ps), "missed_in_flagged": sum(p["missed"] for p in fl)}


def describe(rule) -> str:
    risk, warn, pending, agent = rule
    parts = [f"risk>={risk}"] + [n for n, on in (("unread ink", warn), ("unconfirmed suggestion", pending),
                                                 ("agent added a finding", agent)) if on] + ["retried call"]
    return " or ".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--json", help="write the table here")
    a = ap.parse_args()
    ps = [p for r in a.runs for p in pages(Path(r))]
    print(f"{len(ps)} pages, {sum(1 for p in ps if p['missed'])} leaking, {sum(p['missed'] for p in ps)} missed items")
    print("risk scores of leaking pages:", sorted(p["risk"] for p in ps if p["missed"]))
    print("risk scores of clean pages:  ", sorted(p["risk"] for p in ps if not p["missed"]))
    rows = []
    for rule in product((101, 70, 50, 40, 30, 20, 10), (False, True), (False, True), (False, True)):
        e = evaluate(ps, rule)
        rows.append({"rule": describe(rule), "params": rule, **e})
    rows.sort(key=lambda r: (r["flagged"], -r["leaky_flagged"]))
    print(f"{'flagged':>8} {'leaky caught':>13} {'items caught':>13}  rule")
    seen = set()
    for r in rows:
        key = (r["flagged"], r["leaky_flagged"], r["missed_in_flagged"])
        if key in seen:
            continue
        seen.add(key)
        print(f"{r['flagged']:>3}/{r['pages']:<4} {r['leaky_flagged']:>5}/{r['leaky']:<7} {r['missed_in_flagged']:>5}/{r['missed_items']:<7}  {r['rule']}")
    if a.json:
        Path(a.json).write_text(json.dumps({"pages": ps, "rules": rows}, indent=1))


if __name__ == "__main__":
    main()
