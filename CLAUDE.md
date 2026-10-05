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
- `ISOTHERM_EQS` reads IC `InternalEnergy` as c_s² (P = ρu). InkWell writes 1.5 c_s², so ICs
  go through `examples/mw_gas/fix_isothermal_u.py` (×2/3). Never use this with adiabatic or
  cooling builds.
- Run scripts copy the binary, `Config.sh`, `param.txt` and the converted ICs into
  `$NBODY_RUNS/runs/<name>`. They restart automatically if `output/restartfiles` exists; a
  restart needs the same number of MPI ranks.
- **`cpu.txt` `total` line** reads `total <diff> <diff%> <cumulative> <cum%>`, so cumulative
  wall seconds are in `$4`, not `$3`.
- **`energy.txt` columns:** t, E_th, E_pot, E_kin, 3×NTYPES per-type energies, then NTYPES masses.

## InkWell
- `inkwell cfg.yaml --format gadget4 -o dir` writes `ic_gadget.hdf5`. PartTypes are
  0 gas, 1 DM, 2 stellar disk, 3 bulge. IDs are consecutive by type starting at 1, and Gadget4
  keeps them; this is how `s['comp']` is derived.
- **`omega_b` must be 0.** Otherwise the NFW halo is normalised to (1 − Ω_b/Ω_m) M_vir. The
  halo is also tapered at r_vir, so the live halo is ~0.81 M_vir (8.1e11 for M_vir = 1e12).
- 100k ICs take ~9 min and 10M ICs ~9.5 min on 64 cores, dominated by the Agama grids.
- **Compatibility issues are documented in `reports/inkwell_gadget4_compatibility.md`.** Check
  there before assuming new behaviour is a bug.

## pynbody (2.8.0)
- **Run analysis from `notebooks/`.** Its `config.ini` maps PartType2/3 to `star`; the default
  maps them to `dm`.
- **Use `notebooks/mwtools.load()`.** It sets the correct time from the header (pynbody would
  report ~9.8 Gyr for t = 0), adds `comp`, and centres the snapshot face-on.
- pynbody 2.x API names: `faceon(s, disk_size=...)` and `sph.image(..., axes=ax)`. The profile
  key is `vphi`, not `v_phi`.
- **Raw InkWell ICs are misread by pynbody** (mass ×1/h, length ×1000/h) because the file has no
  units. Use h5py or `check_ics.py` for ICs.
- The warning "Unable to infer units from HDF attributes" on Gadget4 snapshots is harmless.

## Checks
- `examples/mw_gas/check_ics.py <file.hdf5> [--softening ε]` works on ICs and snapshots: masses,
  COM, v_c by component (pytreegrav), σ_R, σ_z, Toomre Q.
- Run the notebook headless:
  `cd notebooks && MW_RUN=<run> jupyter nbconvert --to notebook --execute mw_gas_analysis.ipynb --output <out>.ipynb`.
