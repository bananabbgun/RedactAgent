"""Analyse observe-mode completion dumps: how often does the loop detector fire, do fired calls escape on their own,
which runaway calls does it miss, and what would alternative detectors do."""
import glob, re, sys, zlib
from collections import Counter

files = sorted(glob.glob(sys.argv[1]))
rows = []
for f in files:
    m = re.search(r"c_[\d.]+_(\w+?)_fired(\w+?)_n(\d+)\.txt$", f)
    fin, fired, n = m.group(1), (None if m.group(2) == "None" else int(m.group(2))), int(m.group(3))
    t = open(f, encoding="utf-8").read()
    reasoning, content = t.split("\n=====CONTENT=====\n", 1)
    rows.append(dict(f=f, fin=fin, fired=fired, n=n, rlen=len(reasoning), clen=len(content), r=reasoning, c=content))


def zratio(s):
    s = s.encode()
    return len(zlib.compress(s, 9)) / max(1, len(s))


def min_zratio(s, w=1500, step=250):
    if len(s) < w:
        return 1.0
    return min(zratio(s[i:i + w]) for i in range(0, len(s) - w + 1, step))


print("calls", len(rows), Counter(r["fin"] for r in rows))
fired = [r for r in rows if r["fired"] is not None]
print("fired", len(fired), "-> finish", Counter(r["fin"] for r in fired))
for r in fired:
    print(f"  fired@{r['fired']:5d} end@{r['n']:5d} fin={r['fin']:6s} rlen={r['rlen']:5d} clen={r['clen']:5d} minz={min_zratio(r['r']):.2f}")
missed = [r for r in rows if r["fired"] is None and r["fin"] == "length"]
print("runaway not fired", len(missed))
for r in missed:
    print(f"  n={r['n']} rlen={r['rlen']} minz={min_zratio(r['r']):.2f} tail={r['r'][-160:]!r}")
ok = [r for r in rows if r["fired"] is None and r["fin"] == "stop"]
ns = sorted(r["n"] for r in ok)
rl = sorted(r["rlen"] for r in ok)
print("normal calls", len(ok), "chunks p50/p90/p99/max", ns[len(ns) // 2], ns[int(len(ns) * .9)], ns[int(len(ns) * .99)], ns[-1])
print("normal reasoning chars p50/p90/p99/max", rl[len(rl) // 2], rl[int(len(rl) * .9)], rl[int(len(rl) * .99)], rl[-1])
zs = sorted(min_zratio(r["r"]) for r in ok if r["rlen"] >= 1500)
if zs:
    print("normal min zlib ratio (rlen>=1500): n", len(zs), "min", round(zs[0], 3), "p10", round(zs[len(zs) // 10], 3))
