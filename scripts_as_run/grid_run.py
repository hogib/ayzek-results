"""Trade-off grids on the three held-out test networks: one parameter per detector
varied around its frozen setting, everything else as frozen.

    python3 -u logs/grid_run.py [--jobs N] [--stages runs,outcomes]

EXPLORATORY, OUTSIDE THE HELD-OUT PROTOCOL: nothing is retuned and no frozen setting
changes; the frozen point of each detector is on its curve and must reproduce the
release-time counts. The grid goes through tools/run_heldout.py itself (stages runs
and outcomes), with a settings file in which each grid point is one detector entry,
so every command is the protocol's own:

  learned (3-seed 6 s detector)   --threshold 0.4 ... 0.9    (8 windows, instant 0.9: frozen)
  STA/LTA rule 1 (stalta_eqfa)    --stalta-on 4 ... 20       (band, STA, LTA, off: frozen)
  causal PhaseNet (eqfa rule)     --threshold 0.3 ... 0.9    (1 window: frozen)
  causal EQTransformer (eqfa)     --threshold 0.3 ... 0.9    (8 windows: frozen)
  FilterPicker (eqfa)             --fp-thresholds S1,10, S1 = 10 ... 40  (windows, S2: frozen)

The learned detector and the published models replay from cached window scores
(--scores-in): the sequence sets' from the release run, the quiet windows' from
data/runs/heldout_quiet_scores (2026-11-14); OUT/<net>/scores/learned links to both.
Output: data/runs/heldout_grid/<net>/{runs,quiet,outcomes}; a provenance record
data/runs/heldout_grid/grid.json; DONE written at the end. One log line per finished
unit with count, elapsed and ETA. Standard library only.
"""
import argparse, hashlib, json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--jobs", type=int, default=20)
ap.add_argument("--stages", default="runs,outcomes")
ap.add_argument("--nets", default="ko_now,nz_now,greece_now")
a = ap.parse_args()
os.chdir(ROOT)
OUT = Path("data/runs/heldout_grid")
OUT.mkdir(parents=True, exist_ok=True)

frozen = {k: v for k, v in json.loads(Path("tools/heldout_settings.json").read_text()).items()}
GRID = {
    "learned": ("learned", "--threshold", ["0.4", "0.5", "0.6", "0.7", "0.75", "0.8", "0.85", "0.9"]),
    "stalta": ("stalta_eqfa", "--stalta-on", ["4", "5", "6", "7", "8", "10", "12", "15", "20"]),
    "phasenet": ("phasenet_causal_eqfa", "--threshold", ["0.3", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9"]),
    "eqt": ("eqt_causal_eqfa", "--threshold", ["0.3", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9"]),
    # added 2026-11-15, appended last so that the earlier settings keep their place in the
    # list (and with it their bootstrap intervals): FilterPicker's first threshold, the
    # second as frozen (10); the label carries the first threshold only
    "fp": ("fp_eqfa", "--fp-thresholds", ["10,10", "12,10", "15,10", "20,10", "25,10", "30,10", "40,10"]),
}
settings = {"_comment": ["Exploratory trade-off grid, outside the protocol; written by logs/grid_run.py"]}
for name, (base, opt, values) in GRID.items():
    for v in values:
        e = json.loads(json.dumps(frozen[base]))
        args = list(e["args"])
        if opt in args:
            args[args.index(opt) + 1] = v
        else:
            args += [opt, v]
        e["args"] = args
        settings[f"g_{name}_{v.split(',')[0].replace('.', 'p')}"] = e
sfile = OUT / "grid_settings.json"
sfile.write_text(json.dumps(settings, indent=1))
n_det = len(settings) - 1

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
prov = {"argv": sys.argv, "exploratory": True, "grid": {k: {"base": b, "option": o, "values": v} for k, (b, o, v) in GRID.items()},
        "code_commit": Path("COMMIT").read_text().strip() if Path("COMMIT").exists() else
        subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
        "python": sys.version.split()[0], "binary_sha256": sha("build-linux/app/ayzek"),
        "frozen_settings_sha256": sha("tools/heldout_settings.json"), "grid_settings_sha256": sha(sfile),
        "started_utc": time.strftime("%FT%TZ", time.gmtime()), "nets": a.nets.split(",")}
(OUT / "grid.json.tmp").write_text(json.dumps(prov, indent=1))

stamp = lambda: time.strftime("%FT%TZ", time.gmtime())
plan = []
for net in a.nets.split(","):
    sel = json.loads(Path(f"../ayzek_heldout/selections/{net}/selection.json").read_text())
    tag = f"{sel['group']}_{sel['name']}"
    seqs = [f"{tag}_seq{q['index']:03d}" for q in sel["sequences"] if q["selected"]]
    quiet = [f"{tag}_quiet{j:02d}" for j in range(1, len(sel["quiet"]["windows"]) + 1)]
    link = OUT / net / "scores" / "learned"
    link.mkdir(parents=True, exist_ok=True)
    for s, src in [(s, f"data/runs/heldout/{net}/scores/learned/{s}") for s in seqs] + \
                  [(s, f"data/runs/heldout_quiet_scores/{net}/scores/learned/{s}") for s in quiet]:
        if not (Path(src) / ".done").exists():
            sys.exit(f"{src}: no complete score cache")
        if not (link / s).exists():
            (link / s).symlink_to(Path(src).resolve())
    units = n_det * (len(seqs) + len(quiet)) * ("runs" in a.stages) + n_det * len(seqs) * ("outcomes" in a.stages)
    plan.append((net, units))
total = sum(u for _, u in plan)
print(f"{stamp()} {n_det} settings, {total} units on {a.nets}, {a.jobs} jobs -> {OUT}", flush=True)

start, done = time.time(), 0
for net, units in plan:
    cmd = [sys.executable, "-u", "tools/run_heldout.py", "--selection", f"../ayzek_heldout/selections/{net}",
           "--data", "../ayzek_heldout/data", "--binary", "build-linux/app/ayzek",
           "--network-subsets", "build-linux/tools/network_subsets", "--settings", str(sfile),
           "--scores", "data/runs/heldout_scores", "--stages", a.stages, "--jobs", str(a.jobs),
           "--out", str(OUT / net)]
    before = done
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in p.stdout:
        line = line.rstrip()
        if line.startswith("[runs]") or line.startswith("[outcomes]"):
            done += 1
            el = time.time() - start
            fresh = done - before
            print(f"{stamp()} {done}/{total} {line} | elapsed {el / 60:.0f} min, ETA {el / max(done, 1) * (total - done) / 60:.0f} min", flush=True)
        else:
            print(f"{stamp()} {line}", flush=True)
    if p.wait() != 0:
        sys.exit(f"{stamp()} {net}: run_heldout exited {p.returncode}; FAILED")
    done = before + units          # units skipped because their outputs existed
    print(f"{stamp()} {net} finished", flush=True)

n_out = sum(1 for _ in OUT.glob("*/outcomes/*.csv")) + sum(1 for _ in OUT.glob("*/runs/*/*.txt"))
if n_out == 0:
    sys.exit(f"{stamp()} nothing produced; FAILED")
prov["finished_utc"] = stamp(); prov["files"] = n_out
(OUT / "grid.json.tmp").write_text(json.dumps(prov, indent=1))
(OUT / "grid.json.tmp").rename(OUT / "grid.json")
(OUT / "DONE").touch()
print(f"{stamp()} DONE {n_out} files", flush=True)
