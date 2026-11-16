"""Summary of the exploratory trade-off grid (logs/instant_run.py), outside the protocol.

    python3 logs/instant_summary.py            (from ayzek_code/)

Per network and grid setting, from the grid's reports: detected and scorable events and
unmatched alarms over the sequence sets, alarms and scored hours over the quiet windows.
Then tools/significance.py, unchanged, compares the frozen learned detector (release
outcome tables, linked beside the grid's) with every grid setting: chance-corrected
counts and the paired bootstrap interval of the difference.
Writes data/runs/heldout_instant/summary.csv and <net>/analysis/significance.{txt,json}.
"""
import csv, json, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

G, R = Path("data/runs/heldout_instant"), Path("data/runs/heldout")
settings = [k for k in json.loads((G / "grid_settings.json").read_text()) if not k.startswith("_")]
num = lambda pat, t: int(m.group(1)) if (m := re.search(pat, t, re.M)) else 0

def one(net):
    hours = sum(float(r["scored_hours"]) for r in csv.DictReader(open(R / net / "quiet/quiet_index.csv")))
    link = G / net / "analysis" / "outcomes"
    link.mkdir(parents=True, exist_ok=True)
    for f in list((G / net / "outcomes").glob("*.csv")) + list((R / net / "outcomes").glob("learned_*.csv")):
        if not (link / f.name).exists():
            (link / f.name).symlink_to(f.resolve())
    seqs = sorted(f.stem[len("learned_"):] for f in (R / net / "outcomes").glob("learned_*.csv"))
    out = G / net / "analysis" / "significance"
    p = subprocess.run([sys.executable, "tools/significance.py", "--outcomes", str(link),
                        "--groups", f"{net}={','.join(seqs)}", "--against", ",".join(settings),
                        "--json", str(out) + ".json"], capture_output=True, text=True)
    if p.returncode:
        sys.exit(p.stderr[-2000:])
    Path(str(out) + ".txt").write_text(p.stdout)
    sig = {}
    for m in re.finditer(r"^learned vs (\S+): (\d+) events\n  detected\s+(\d+) vs (\d+).*\n  chance-corrected\s+([\d.]+) vs ([\d.]+), "
                         r"difference ([+-][\d.]+) \(95% bootstrap ([+-][\d.]+) to ([+-][\d.]+)", p.stdout, re.M):
        sig[m.group(1)] = m.groups()
    rows = []
    for s in settings:
        seq = [(f.read_text()) for f in sorted((G / net / "runs" / s).glob("*.txt"))]
        qt = [(f.read_text()) for f in sorted((G / net / "quiet" / s).glob("*.txt"))]
        g = sig[s]
        rows.append({"network": net, "setting": s, "sequence_sets": len(seq), "events": g[1], "detected": g[3],
                     "corrected": g[5], "alarms": sum(num(r"^  Alarms raised\s+(\d+)", t) for t in seq),
                     "unmatched_alarms": sum(num(r"^    false\s+\(no \w+ event\)\s+(\d+)", t) for t in seq),
                     "quiet_windows": len(qt), "quiet_alarms": sum(num(r"^  Alarms raised\s+(\d+)", t) for t in qt),
                     "quiet_hours": f"{hours:.1f}", "frozen_learned_corrected": g[4],
                     "difference": g[6], "ci_low": g[7], "ci_high": g[8]})
    print(net, "done", flush=True)
    return rows

with ThreadPoolExecutor(3) as pool:
    rows = [r for rs in pool.map(one, ("greece_now", "nz_now", "ko_now")) for r in rs]
if not rows:
    sys.exit("nothing produced")
tmp = G / "summary.csv.tmp"
with open(tmp, "w", newline="") as fh:
    w = csv.DictWriter(fh, list(rows[0])); w.writeheader(); w.writerows(rows)
tmp.rename(G / "summary.csv")
print("wrote", G / "summary.csv", len(rows), "rows")
