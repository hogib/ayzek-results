# ayzek: request records and outputs of the held-out tests

This record accompanies the manuscript that describes the ayzek pipeline
(<https://github.com/hogib/ayzek>, release v1.0.0, commit 3e43064,
doi:[10.5281/zenodo.23806743](https://doi.org/10.5281/zenodo.23806743)).
It holds what the tests requested from the data centers, what the pipeline wrote
when it replayed those data, and the files attached to the pipeline's releases.

No test waveform is in this record. The waveforms are open at their data centers
(NOA EIDA node, GeoNet, KOERI) and are fetched with the tool at
<https://github.com/hogib/ayzek-heldout>. Each `dataset.json` here lists the
SHA-256 of every file that tool wrote, so a later fetch can be checked against the
data used in the study.

## Layout

| Folder | Contents | Size |
|---|---|---|
| `requests/selections/` | The selection records (`selection.json`) and set files (`.toml`) written by `heldout select`: sequences, quiet windows, station tables and catalog requests | 0.4 MB |
| `requests/sets/` | Per fetched set: `dataset.json` (services, stations, channels, windows, the canary check, what arrived, SHA-256 of each file), `stations.json`, `stations.csv`, `catalog.csv`, `pd_gain.csv` | 8 MB |
| `protocol_runs/` | Outputs of `tools/run_heldout.py` for the three tests of the protocol (`greece_now`, `nz_now`, `ko_now`) | 151 MB |
| `exploratory/` | Outputs of the analyses made after the tests, outside the protocol | 215 MB |
| `release/` | Files attached to the pipeline's GitHub releases | 109 MB |

### `requests/sets/`

| Sets | Number | What they are |
|---|---|---|
| `greece_now_*`, `nz_now_*`, `ko_now_*` | 35, 37, 16 | The sequences (`seqNNN`) and quiet windows (`quietNN`) of the three tests |
| `greece_strat_*`, `nz_strat_*` | 22, 18 | Quiet windows drawn after the tests, two per station set (exploratory) |
| `tune_greece_*`, `tune_nz_*`, `tune_ko_*` | 4 each | The windows on which the baselines were tuned before the freeze |

### `protocol_runs/<test>/`

- `manifest.json`: the selection, binary, settings and their SHA-256.
- `commands.log`: every command the run executed.
- `runs/<detector>/` and `quiet/<detector>/`: the pipeline's report for each
  sequence and each quiet window. The detector labels are those of
  `tools/heldout_settings.json` in the pipeline's repository (protocol:
  `docs/protocol-heldout.md`, section 6).
- `scores/learned/`: the learned detector's window scores, cached by the run.
- `outcomes/`, `neighbours/`: per-event outcome tables and the neighbouring
  settings of the learned detector.
- `analysis/`: the summaries from which the manuscript's test results are read
  (`significance*.txt/json`, `quiet*.txt/json`, `neighbours*.txt/json`,
  `magnitude_*.{csv,txt}`, `warning_leads.csv`).

### `exploratory/`

Every file here comes from an analysis made after the tests were scored. None is
part of the protocol. Most folders carry a `provenance.json`, `grid.json` or `manifest.json` with
the command and, where recorded, the commit and input hashes.

| Folder | Tool in the pipeline's repository |
|---|---|
| `heldout_grid/`, `heldout_instant/` | `tools/heldout_grid.py`, `tools/heldout_grid_matched.py`, `tools/heldout_grid_summary.py` |
| `plateau_seeds/` | `tools/plateau_seeds.py` (development replays only; with the model files of the three seeds) |
| `heldout_min3/` | `tools/heldout_min3.py` |
| `heldout_iasp91/` | `tools/heldout_iasp91.py` |
| `heldout_globalcat/` | `tools/heldout_globalcat.py` |
| `heldout_explore5/` | `tools/heldout_exploratory.py` |
| `heldout_quietscan/` | `tools/quiet_scan.py` of the fetch tool |
| `heldout_quietstrat/` | `tools/quiet_draw.py` of the fetch tool, `tools/run_heldout.py`, `tools/heldout_quietstrat.py` |

### `release/`

| File | From release | SHA-256 |
|---|---|---|
| `ayzek-v1.0.0-linux-x86_64` | v1.0.0 | `a40e7d23a1dfca7a4a2baf38b4b93c11056241d34d61aa046d703279a1da6899` |
| `ayzek-heldout-440a2d9.tar.gz` | v1.0.0 | `20e8c523e42465ba8014147c2a77c5ecee38392b16a1b4637b73d35a19f9222b` |
| `freeze-checks-2026-10-30.tar.gz` | v1.0.0 | `e670f788dfdf0a7c7a28b6d2af0f25e98994cd5d8484a09df6d4e27443592170` |
| `ayzek-demo_ko.tar.gz` | v0.1.0-beta.6 | `383760b90e56442384439d74da2c9b16d5eedd658c0bd7c57611b58a8898e5bd` |
| `ayzek-marmara_ko.tar.gz` | v0.1.0-beta.6 | `8764d9815ac4e9289d973f21a7a79e55fb056dd6eaea5e836d68a7204c0a9703` |
| `ayzek-quiet_ko.tar.gz` | v0.1.0-beta.6 | `65914aa55b8432a658c92ddf9c2d4f5f3f4937b45d92f867648e56f0c1296842` |

The binary is the static x86-64 build that ran the tests. Its SHA-256 is the one in
each `protocol_runs/<test>/manifest.json`. The three `*_ko.tar.gz` files are the
public KOERI datasets of the development replays.

## What is left out

- **Event recordings (`.rec`).** The pipeline's own recordings of each replay are
  derived from the waveforms and are not included.
- **Score files of the published models.** The PhaseNet and EQTransformer window
  scores that their replays read (about 3.5 GB, and 1.7 GB for the windows drawn
  afterwards) are not included. `tools/seisbench_scores.py` regenerates them from
  the waveforms and the SeisBench weights.
- **Temporary files** (`.tmp`).

`SHA256SUMS` lists the SHA-256 of every file in this record
(`sha256sum -c SHA256SUMS`).

Paths inside the logs and manifests are those of the machines the runs were made on.

## Licences

- The records and outputs (`requests/`, `protocol_runs/`, `exploratory/`) are
  under CC BY 4.0 (`LICENSE`).
- `release/ayzek-v1.0.0-linux-x86_64` and `release/ayzek-heldout-440a2d9.tar.gz`
  are under the GNU General Public License, version 3 or later, as their
  repositories.
- The KOERI waveforms in `release/*_ko.tar.gz` are data of the Kandilli
  Observatory and Earthquake Research Institute network (KO,
  doi:10.7914/SN/KO), open under citation of the network.
- Catalog and station data in `requests/` come from NOA (EIDA node), GeoNet
  (CC BY 3.0 NZ) and KOERI, as named in each `dataset.json`.
