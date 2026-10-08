# Status and restart checklist

Last updated: 2026-10-08.

All work so far is merged into `main` (PRs #1–#3 on github.com/jngaravitoc/run_nbody_sims). The
repo is current with InkWell `1ba0858`, Gadget-4 `6fb393b`, Agama `60d8d8b`, pynbody `2c9e0a33`.

## Done
- **Tutorials 01–04, example `examples/mw_gas/`, notebook, and `env/`** are complete and verified
  from scratch (100k pipeline rerun end to end with the documented commands on `1ba0858`).
- **Full 2 Gyr run `mw_gas`** (10M particles, Slurm job 12037) finished cleanly on 2026-10-02.
  It used InkWell `8c765a6`, so its first ~200 Myr contain the old disk breathing.
- **InkWell compatibility work with its developer** (Jason Hunt), in three rounds:
  - `reports/inkwell_gadget4_compatibility.md`: our first test, 7 issues.
  - `reports/inkwell_gadget4_retest.md`: re-test of `4ab25f8`.
  - `reports/inkwell_gadget4_retest2.md`: re-test of `1ba0858`. All requests pass, and the disk
    breathing is fixed (10M, 300 Myr: |⟨v_R⟩| ≤ 0.7 km/s, was 9 km/s).
- `check_inkwell_ic.py` now exits 1 when halo or bulge are not mirrored (review feedback on
  PR #3); `--no-antithetic` skips that requirement for older ICs.

## Results
| | Test (100k, 500 Myr) | Relaxation (10M, 300 Myr) | Full (10M, 2 Gyr) |
|---|---|---|---|
| InkWell | `1ba0858` | `1ba0858` | `8c765a6` |
| ICs | v_c(8) 214.8 km/s, Q(2R_d) 1.85 | v_c(8) 214.6 km/s, Q(2R_d) 1.88 | v_c(8) 212 km/s, Q(2R_d) 1.91 |
| Energy drift | −6.0e-4 | 1.0e-4 | 4.9e-4 |
| Bar (A₂, R < 6 kpc) | transient spiral, 0.105 at ~320 Myr | ≤ 0.004 | ≤ 0.007 |
| Stellar z_rms at 7–9 kpc | 0.536 → 0.606 kpc (+13%, resolution) | 0.540–0.545 kpc | +1.3% over 2 Gyr |
| Gas z_rms | 4–10 kpc: 0.187 → 0.249 kpc | 4–10 kpc: 0.194 → 0.192 kpc | 7–9 kpc: 0.216 → 0.201 kpc |
| Stellar Σ and R_d | inner Σ −5% dip; R_d 2.99 → 2.93 (max 3.34) | inner Σ ≤ 1.4%, R_d ≤ 1.2% | inner Σ −9%, R_d +6% in the first 200 Myr (old breathing), then constant |
| Wall time | 1 min 16 s, 64 cores | 1 h 22 min, 128 cores | 7 h 44 min, 128 cores |
| Disk | 107 MB | 5.1 GB (restart files deleted) | 4.0 GB |

All acceptance criteria are met: codes compile from documented modules; ICs pass sanity checks;
the 2 Gyr run completed; the notebook produces maps, rotation curve, Σ(R) profiles and masses vs
time.

## Open decisions and follow-ups
- **Send the second re-test.** Share `reports/inkwell_gadget4_retest2.md` or its page with
  Jason Hunt: https://claude.ai/artifact/YNrCzZjzyU6T2vJFEGqbQn (private until you share it from
  its Share menu). The earlier pages are
  https://claude.ai/artifact/F3rzjRr65iX3Vkvuema7bS (first report) and
  https://claude.ai/artifact/3MeXSgJanVW5trGAu1T66w (first re-test). Only minor notes remain open:
  the log's live-halo mass is 0.68% high, odd particle counts round up (100,001 / 10,000,001),
  the equilibrium checker's 50 pc softening is too small at 100k, and generation is ~1.7× slower.
- **Production run.** The 2 Gyr `mw_gas` run still uses InkWell `8c765a6` ICs. Rerunning it with
  `1ba0858` (~17 min ICs + ~8 h, ~4 GB) would make the tutorial's flagship run consistent with
  the current code. Until then, discard its first ~200 Myr in analyses of early evolution.
- **Snapshot cadence.** 200 Myr keeps the full run near 4 GB. For finer sampling, set
  `TimeBetSnapshot 0.0511352` (50 Myr, ~15 GB). Mass vs time already has 5 Myr resolution from
  `energy.txt`.
- **Star formation (tutorial 05).** A `COOLING` + `STARFORMATION` example is the natural next
  step. The build reads InkWell ICs: config and params in `~/nbody_runs/compat/sfr/` and
  `~/nbody_runs/retest2/runs/sfr_M/`. Use `--gadget-eos adiabatic` and
  `mean_molecular_weight: 1.22` on the gas disk, which removes the startup temperature drop. A 10M
  cooling run has not been done; the 100k test cannot resolve the gas disk's vertical response.
- **GitHub from the session.** Claude's session has no GitHub credentials, so push and PR
  creation happen from your terminal (`git push`, then open the PR in the browser).
- **Cleanup.** Safe to delete once you no longer need them (sizes from 2026-10-08):

  | Path | Size | What it is |
  |---|---|---|
  | `~/nbody_runs/compat/` | 250 MB | first compatibility tests |
  | `~/nbody_runs/retest/` | 236 MB | `4ab25f8` re-test runs |
  | `~/nbody_runs/retest2/` | 2.0 GB | `1ba0858` re-test (variants P/D0/M, 10M ICs with `ic.hdf5`) |
  | `~/nbody_runs/runs/mw_gas_relax/` | 5.1 GB | 10M relaxation run with `4ab25f8` (breathing) |
  | `~/nbody_runs/runs/mw_gas_test_{8c765a6,4ab25f8}/` | small | superseded 100k runs |
  | `~/nbody_runs/ics/mw_gas_test_{v1,8c765a6,4ab25f8}/` | small | superseded 100k ICs |
  | `~/nbody_runs/ics/mw_gas_iso/` | 0.7 GB | 10M ICs for the `4ab25f8` relaxation run |

  Keep `runs/mw_gas` (the 2 Gyr run) and `runs/mw_gas_relax_1ba0858` (the evidence that the
  breathing is fixed) until the production run is redone.

## Where things are
| What | Where |
|---|---|
| Codes (read-only) | `~/codes/{gadget4,InkWell,Agama,pynbody}` |
| Clones and builds | `~/nbody_runs/builds/` (`src/`, `gadget4_mw_gas/`, `pip-freeze.txt`, build logs) |
| Python venv | `~/environments/nbody-tutorial` |
| ICs | `~/nbody_runs/ics/mw_gas/` (10M, `8c765a6`), `mw_gas_test/` (100k, `1ba0858`), `mw_gas_iso/` (10M, `4ab25f8`) |
| Runs | `~/nbody_runs/runs/`: `mw_gas` (2 Gyr), `mw_gas_test` (100k), `mw_gas_relax*` (300 Myr, 10M) |
| 10M ICs for `1ba0858` | `~/nbody_runs/retest2/ics/P10M/` (also with `agama_potential.ini` and `ic.hdf5`) |
| Executed notebooks | `runs/mw_gas/mw_gas_analysis_full.ipynb`, `runs/mw_gas_test/mw_gas_test_analysis.ipynb`, `runs/mw_gas_relax_1ba0858/mw_gas_relax_analysis.ipynb` |
| Reports and figures | `reports/`, `reports/img/`, `tutorials/img/` |
