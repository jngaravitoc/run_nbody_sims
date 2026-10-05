# Status and restart checklist

Last updated: 2026-10-05.

## Done
- **Full run `mw_gas` is complete.** Slurm job 12037 ran 2026-10-02 from 13:50 to 21:34
  (7 h 44 min on 2 × 64 ranks) and reached 2 Gyr with all 11 snapshots, exit code 0.
- The notebook was executed on it; output in
  `~/nbody_runs/runs/mw_gas/mw_gas_analysis_full.ipynb`, figures in `tutorials/img/full_*.png`.
- The results are in the README ("Full run"), tutorial 04 §4, and the InkWell report (the gas
  equilibrium question is answered). The published report page was updated (version 2).

## Results
| | Test (100k, 500 Myr) | Full (10M, 2 Gyr) |
|---|---|---|
| ICs | v_c(8) 214 km/s, Q(2R_d) 1.88 | v_c(8) 212 km/s, Q(2R_d) 1.91 |
| Energy drift | 1.8e-4 | 4.9e-4 |
| Bar (A₂, R < 6 kpc) | ≤ 0.05 | ≤ 0.007 |
| Stellar z_rms at 7–9 kpc | +12% (resolution) | +1.3% |
| Gas z_rms at 7–9 kpc | 0.21 → 0.28 kpc | 0.216 → 0.201 kpc (settles in < 0.4 Gyr, then constant) |
| Stellar Σ / R_d | ~stable | inner Σ −9%, R_d +6% in first 200 Myr, then constant |
| Wall time | 1 min 24 s on 64 cores | 7 h 44 min on 128 cores |
| Disk | 107 MB | 4.0 GB snapshots (+0.6 GB IC copy); restart files deleted 2026-10-05 |

All acceptance criteria are met: codes compile from documented modules; ICs pass sanity checks;
the test disk is stable; the 2 Gyr run completed; the notebook produces maps, rotation curve,
Σ(R) profiles and masses vs time.

## Open decisions and follow-ups
- **InkWell report.** `reports/inkwell_gadget4_compatibility.md` is also published, privately, at
  https://claude.ai/artifact/F3rzjRr65iX3Vkvuema7bS. It has not been sent to Jason Hunt (InkWell
  developer) yet, and there are no GitHub issues on JASHunt/InkWell yet. Decide whether to share
  the page or open issues.
- **Snapshot cadence.** 200 Myr was chosen to stay under ~5 GB. If finer time sampling of the
  maps or profiles is needed, rerun with `TimeBetSnapshot 0.0511352` (50 Myr, ~15 GB). Mass vs
  time already has 5 Myr resolution from `energy.txt`.
- **Initial relaxation.** The full run adjusts once in the first 200 Myr (inner stellar Σ −9%,
  gas z_rms −7%), then stays steady. It is reported to InkWell as a possible CylSpline effect.
  A short rerun with frequent snapshots (e.g. 10 Myr for 300 Myr, ~11 GB at 10M; less at 1M)
  would resolve when it happens.
- **Push / PR.** Everything is committed on branch `tutorials/mw-gas` (not pushed). Push it and
  open a PR to `main` on github.com/jngaravitoc/run_nbody_sims when ready.
- **Star formation.** A `COOLING` + `STARFORMATION` example is a natural tutorial 05. The build
  has been tested to read InkWell ICs: config and params in `~/nbody_runs/compat/sfr/`.
  It needs the unconverted IC u, and a decision on μ (see report issue 5).
- **Cleanup.** `~/nbody_runs/compat/` (250 MB, compatibility tests) and
  `~/nbody_runs/ics/mw_gas_test_v1/` (superseded Ω_b ≠ 0 ICs) can be deleted once the report
  is settled.

## Where things are
| What | Where |
|---|---|
| Codes (read-only) | `~/codes/{gadget4,InkWell,Agama,pynbody}` |
| Clones and builds | `~/nbody_runs/builds/` (`src/`, `gadget4_mw_gas/`, `pip-freeze.txt`, build logs) |
| Python venv | `~/environments/nbody-tutorial` |
| ICs | `~/nbody_runs/ics/{mw_gas,mw_gas_test}/` (each has `ics_check.png`) |
| Runs | `~/nbody_runs/runs/{mw_gas,mw_gas_test}/` |
| Compatibility tests | `~/nbody_runs/compat/{adiabatic,sfr,iso_nofix,unitsfix,units}/` |
