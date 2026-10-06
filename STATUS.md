# Status and restart checklist

Last updated: 2026-10-06.

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

## InkWell 4ab25f8 re-test (2026-10-06)
The developer fixed the issues from our first report; their response is the source of the
current re-test. Summary in `reports/inkwell_gadget4_retest.md`, published privately at
https://claude.ai/artifact/3MeXSgJanVW5trGAu1T66w (not yet shared with Jason Hunt).
- Six of seven fixes verified. `forceDeriv` still fires on Agama 1.0.160. Fix:
  `pot.eval(xyz, acc=True, der=True)`.
- 10M relaxation run `~/nbody_runs/runs/mw_gas_relax` (300 Myr, every 25 Myr, 5.1 GB). The gas
  does not collapse at full resolution. The stellar disk breathes radially for ~200 Myr (inner Σ
  −13% then settles −8%, R_d +6%). This is reported to the developer as a likely DF-vs-potential
  mismatch.
- The tutorials now use InkWell 4ab25f8: `halo.baryon_fraction: 0`, `--gadget-eos isothermal`;
  `fix_isothermal_u.py` was removed.
- Old 100k data is kept as `~/nbody_runs/{ics,runs}/mw_gas_test_8c765a6`. The 2 Gyr `mw_gas` run
  is still from 8c765a6; that is noted in the README.
- Test data: `~/nbody_runs/retest/` (3 IC variants, 100k runs, merge test, diagnostics).

## Open decisions and follow-ups
- **Send the re-test.** Share `reports/inkwell_gadget4_retest.md` or its page with Jason Hunt.
  Open items for him: the `forceDeriv` call, antithetic spheroid sampling, a per-disk μ for
  `COOLING` runs (we prefer option a), and the two tests for the stellar breathing.
- **Snapshot cadence.** 200 Myr was chosen to stay under ~5 GB. If finer time sampling of the
  maps or profiles is needed, rerun with `TimeBetSnapshot 0.0511352` (50 Myr, ~15 GB). Mass vs
  time already has 5 Myr resolution from `energy.txt`.
- **Initial relaxation.** Resolved by the 10M relaxation run: a damped ~125 Myr radial breathing
  of the stellar disk, settled by 200 Myr. Until InkWell addresses it, discard the first ~200 Myr
  in analyses of early evolution.
- **Push / PR.** Everything is committed on branch `tutorials/mw-gas` (not pushed). Push it and
  open a PR to `main` on github.com/jngaravitoc/run_nbody_sims when ready.
- **Star formation.** A `COOLING` + `STARFORMATION` example is a natural tutorial 05. The build
  has been tested to read InkWell ICs: config and params in `~/nbody_runs/compat/sfr/`.
  It needs the unconverted IC u, and a decision on μ (see report issue 5).
- **Cleanup.** Once the re-test is settled, these can be deleted: `~/nbody_runs/compat/`
  (250 MB), `~/nbody_runs/retest/` (test runs), `~/nbody_runs/ics/mw_gas_test_v1/` and
  `mw_gas_test_8c765a6` (superseded ICs), and `~/nbody_runs/ics/mw_gas_iso` (0.7 GB, 10M ICs for
  the relaxation run).

## Where things are
| What | Where |
|---|---|
| Codes (read-only) | `~/codes/{gadget4,InkWell,Agama,pynbody}` |
| Clones and builds | `~/nbody_runs/builds/` (`src/`, `gadget4_mw_gas/`, `pip-freeze.txt`, build logs) |
| Python venv | `~/environments/nbody-tutorial` |
| ICs | `~/nbody_runs/ics/{mw_gas,mw_gas_test}/` (each has `ics_check.png`) |
| Runs | `~/nbody_runs/runs/{mw_gas,mw_gas_test}/` |
| Compatibility tests | `~/nbody_runs/compat/{adiabatic,sfr,iso_nofix,unitsfix,units}/` |
