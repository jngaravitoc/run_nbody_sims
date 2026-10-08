# CLAUDE.md

Tutorial repo for running galaxy simulations on the **geryon3** cluster:
InkWell (ICs) → Gadget4 (MPI, Slurm) → pynbody (analysis). Current work and next steps are in
`STATUS.md`. Read it first when resuming.

## Hard rules
- **Never modify `~/codes/*`.** Every build uses clones in `$NBODY_RUNS/builds/src`, made by
  `env/fetch_sources.sh` at the commits in `env/versions.env`.
- **Large files stay out of the repo.** ICs, snapshots and builds live in
  `$NBODY_RUNS = ~/nbody_runs/{builds,ics,runs,compat}`.
- **Show test results before production runs.** Run the 100k test first and report its results
  before launching full-resolution runs.
- **Disk budget.** The user wants each production run to produce ~5 GB or less. A 10M-particle
  snapshot is ~0.37 GB (single-precision output), so the full run writes one every 200 Myr.

## Environment
- `source env/modules.sh` sets up everything: modules, paths, `SYSTYPE`, and the venv
  `~/environments/nbody-tutorial`.
- Modules: `openmpi/4.1.5/gnu`, `gsl-1.16`, `hdf5/1.14.3/serial/gnu`, `python-3.11.4`.
  FFTW is not needed (no `PMGRID`).
- Cluster: partitions `batch` (12 nodes) and `debug` (2 nodes); 64 cores and 512 GB per node; no
  time limit. Login and compute nodes have the same CPU (Xeon Gold 6448H), so `-march=native`
  binaries run on both.
- **There is no `git` on the compute nodes.** Clone on the login node first.
- **The scratchpad (`/tmp/...`) is node-local.** Anything a Slurm job must read goes under
  `$NBODY_RUNS` (on `/home`, which is shared).
- `env/modules.sh` sets `OMPI_MCA_btl=^openib`. The nodes have Mellanox IB driven by UCX; the old
  openib BTL only prints init errors.
- **Agama needs `env/patches/agama_static_libpython.patch`.** The python module has only a
  static libpython. `fetch_sources.sh` applies the patch.

## Gadget4
- Build out of tree:
  `cd $NBODY_RUNS/builds/src/gadget4 && make DIR=<dir> PYTHON=python3`, with
  `SYSTYPE=Generic-gcc`. Headers and libraries are found through the module `CPATH` and
  `LIBRARY_PATH`. Script: `examples/mw_gas/build_gadget4.sh`, run via `srun -p debug`.
- **`NTYPES` must be 6** to read InkWell ICs, which always have 6-element `NumPart` arrays.
- Units: kpc, 1e10 Msun, km/s, so the time unit is **0.977792 Gyr**.
- `ISOTHERM_EQS` reads IC `InternalEnergy` as c_s² (P = ρu). Generate ICs for it with
  `inkwell --gadget-eos isothermal` (InkWell ≥ 4ab25f8; header `InkWellInternalEnergy` =
  'cs2 (ISOTHERM_EQS)'). Adiabatic and `COOLING` builds need the default `--gadget-eos adiabatic`.
  The run scripts refuse ICs without the `cs2` attribute. (`fix_isothermal_u.py` is gone; the
  existing 2 Gyr `mw_gas` run used it with InkWell 8c765a6.)
- Run scripts copy the binary, `Config.sh`, `param.txt` and the converted ICs into
  `$NBODY_RUNS/runs/<name>`. They restart automatically if `output/restartfiles` exists; a
  restart needs the same number of MPI ranks.
- **`cpu.txt` `total` line** reads `total <diff> <diff%> <cumulative> <cum%>`, so cumulative
  wall seconds are in `$4`, not `$3`.
- **`energy.txt` columns:** t, E_th, E_pot, E_kin, 3×NTYPES per-type energies, then NTYPES masses.

## InkWell
- Pinned at `1ba0858` (≥ 3e5907e: disc iterations, antithetic spheroids, per-disk μ).
- `examples/mw_gas/make_ics.py cfg.yaml dir` generates once and writes `ic_gadget.hdf5` (Gadget-4)
  and `ic.hdf5` (InkWell format); the `inkwell` CLI writes only one format per run. PartTypes are
  0 gas, 1 DM, 2 stellar disk, 3 bulge. IDs are consecutive by type starting at 1, and Gadget4
  keeps them; this is how `s['comp']` is derived.
- **Set `halo.baryon_fraction: 0.0`.** Its default, Ω_b/Ω_m, removes 16% of M_vir from the live
  halo. The halo is also tapered at r_vir, so the live halo is ~0.815 M_vir (8.15e11 for
  M_vir = 1e12); the log prints it. Keep Planck `omega_b` in the YAML.
- **Antithetic spheroids** (`assembly.antithetic`, default on): the halo and bulge are N/2
  particles plus mirrors (−x, −v); odd N rounds up (bulge 6,668; totals 100,001 / 10,000,001).
  The disk then stays within 0.004 kpc of the halo centre at 10M (was 0.06; 0.44 at 100k).
  The disks are recentred (`assembly.recentre`).
- **Disc iterations** (`agama.disc_iterations`, default 2) remove the stellar-disk radial
  breathing of older versions (≤ 0.7 km/s ⟨v_R⟩ at 10M, was 9 km/s). Never set it to 0.
- `mean_molecular_weight` on an isothermal gas disk: use ~1.22 for 10⁴ K gas in `COOLING` runs
  (removes the thermal transient); irrelevant for `ISOTHERM_EQS` and adiabatic runs.
- The `Live DM halo mass` log line is 0.68% above what the halo particles carry (8.09e11).
- 100k ICs take ~16 min and 10M ICs ~17 min on 64 cores (Agama grids and disc iterations).
- `$NBODY_RUNS/builds/src/InkWell/scripts/check_disc_equilibrium.py <dir> --softening ε` needs
  `ic.hdf5` + `agama_potential.ini`; the disk ratio should be 1.00 ± 0.02. Use ε = 0.05 kpc at 10M
  and 0.2 at 100k (at 100k with 0.05, single gas particles dominate). `run_ics.sbatch` runs it.
- **Compatibility history is in `reports/`**: `inkwell_gadget4_compatibility.md` (first test),
  `inkwell_gadget4_retest.md` (4ab25f8), `inkwell_gadget4_retest2.md` (1ba0858). Check there
  before assuming new behaviour is a bug.

## pynbody (2.8.0)
- **Run analysis from `notebooks/`.** Its `config.ini` maps PartType2/3 to `star`; the default
  maps them to `dm`.
- **Use `notebooks/mwtools.load()`.** It sets the correct time from the header (pynbody would
  report ~9.8 Gyr for t = 0), adds `comp`, and centres the snapshot face-on.
- pynbody 2.x API names: `faceon(s, disk_size=...)` and `sph.image(..., axes=ax)`. The profile
  key is `vphi`, not `v_phi`.
- InkWell ≥ 4ab25f8 ICs carry units (`Parameters` group, h = 1) and pynbody reads them exactly.
  Older InkWell ICs are misread (mass ×1/h, length ×1000/h); use h5py for those.
- `examples/mw_gas/check_inkwell_ic.py` checks an InkWell IC's metadata, pynbody unit factors,
  u convention, recentring and mirrored halo/bulge pairs; it exits 1 on any failure. Pass
  `--no-antithetic` for ICs made with `assembly.antithetic: false` or InkWell < 3e5907e.
- The warning "Unable to infer units from HDF attributes" on Gadget4 snapshots is harmless.

## Checks
- `examples/mw_gas/check_ics.py <file.hdf5> [--softening ε]` works on ICs and snapshots: masses,
  COM, v_c by component (pytreegrav, averaged over 64 azimuths; 8 gave ±4% noise at 100k), σ_R,
  σ_z, Toomre Q.
- `examples/mw_gas/relax_diag.py <run/output> ...` gives per-snapshot z_rms about each
  component's own centre, centre separations, Σ, fitted R_d and A₂.
- Equilibrium test for new ICs: `sbatch run_gadget4_relax.sbatch <ics_dir> <run_name>` (10M,
  300 Myr, every 25 Myr, ~1.4 h, 5.1 GB after deleting restart files), then notebook section 7.
- Delete `output/restartfiles` once a run is final (1.4 GB for the relaxation run, 2.7 GB for 2 Gyr).
- Run the notebook headless:
  `cd notebooks && MW_RUN=<run> jupyter nbconvert --to notebook --execute mw_gas_analysis.ipynb --output <out>.ipynb`.
