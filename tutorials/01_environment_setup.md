# 01 — Environment setup on geryon3

By the end of this tutorial you will have:

* a module environment that compiles and runs all codes (`env/modules.sh`);
* a Python virtual environment with **Agama**, **InkWell**, **pynbody** and Jupyter;
* a **Gadget4** executable compiled for the `examples/mw_gas` setup.

Everything large lives outside the repository, under `$NBODY_RUNS` (default `~/nbody_runs`):

```
~/nbody_runs/
├── builds/   source clones, compiled Gadget4, build logs
├── ics/      initial conditions (one directory per model)
└── runs/     Gadget4 run directories (snapshots, logs, restart files)
```

## 0. The cluster at a glance

| | |
|---|---|
| Scheduler | Slurm |
| Partitions | `batch` (default; 12 nodes `geryon3-[01-12]`), `debug` (2 nodes `geryon3-[11-12]`); no time limit |
| Nodes | 64 cores (Intel Xeon Gold 6448H), 512 GB RAM each |
| Compilers | system GCC 8.5.0 (+ OpenMPI wrappers from the module) |
| `git` | available on the **login node only**, not on compute nodes |

Check this yourself with:

```bash
sinfo -o "%P %D %c %m %l"     # partitions, nodes, cores, memory (MB), time limit
module avail                 # all modules
```

## 1. Modules

All scripts in this repository start with `source env/modules.sh`, which loads:

| Module | Why |
|---|---|
| `openmpi/4.1.5/gnu` | MPI compiler wrappers (`mpicxx`) and `mpirun` for Gadget4 |
| `gsl-1.16` | GNU Scientific Library: Gadget4 and Agama (there is no system `gsl-devel`) |
| `hdf5/1.14.3/serial/gnu` | HDF5 I/O for Gadget4 ICs and snapshots |
| `python-3.11.4` | base interpreter for the virtual environment |

FFTW is **not** needed: Gadget4 only links it when `PMGRID` or `NGENIC` is enabled, and an isolated
galaxy uses pure tree gravity.

The script also exports `CODES_DIR` (`~/codes`), `NBODY_RUNS` (`~/nbody_runs`),
`NBODY_VENV` (`~/environments/nbody-tutorial`) and `SYSTYPE=Generic-gcc`, and activates the
venv if it exists. You can override the three paths before sourcing:

```bash
export NBODY_RUNS=/scratch/$USER/nbody_runs   # e.g. to use scratch instead
source env/modules.sh
```

## 2. Source code and versions

The codes are taken from the local checkouts in `~/codes` and **cloned** into
`$NBODY_RUNS/builds/src` at fixed commits (`env/versions.env`). Building never touches `~/codes`.

| Code | Commit | Role |
|---|---|---|
| Gadget4 | `6fb393b` | TreePM/SPH simulation code (MPI) |
| InkWell | `8c765a6` | initial-condition generator |
| Agama | `60d8d8b` (+ local patch) | distribution functions used by InkWell |
| pynbody | `2c9e0a33` (v2.8.0 dev) | snapshot analysis |
| Eigen | 3.4.1 (`~/codes/deps/eigen`) | linear-algebra headers for Agama |

Clone them (login node, needs `git`):

```bash
bash env/fetch_sources.sh
```

> **Agama patch.** The `python-3.11.4` module only ships a static `libpython3.11.a`, so
> Agama's `setup.py` cannot link its test programme against `libpython.so`.
> `env/patches/agama_static_libpython.patch` adds a fallback that builds the extension without
> linking libpython (the standard model for Linux extensions). `fetch_sources.sh` applies it.

## 3. Python environment

```bash
bash env/install_python_env.sh      # login node, ~10 min (Agama compilation dominates)
```

This script:

1. runs `fetch_sources.sh`;
2. creates the venv `~/environments/nbody-tutorial` on top of `python-3.11.4`;
3. installs the pinned third-party packages in `env/requirements.txt`
   (numpy 2.4.6, scipy 1.17.1, h5py 3.16.0, pytreegrav 1.4.0, matplotlib, JupyterLab, ...);
4. builds **Agama** with Eigen on `CPATH` (`pip install --no-build-isolation . --build-option=--yes`
   — `--yes` answers Agama's interactive questions);
5. installs **InkWell** (`pip install ".[hdf5]"`) and **pynbody** from the clones;
6. writes `pip freeze` to `$NBODY_RUNS/builds/pip-freeze.txt`.

Check it:

```bash
source env/modules.sh
python -c "import agama, inkwell, pynbody; print(agama.__version__, pynbody.__version__)"
# 1.0.160 compiled on ... 2.8.0
which inkwell
```

## 4. Compile Gadget4

Gadget4 is configured at compile time through `Config.sh`. Each simulation setup has its own
`Config.sh` and therefore its own executable. For the Milky Way example:

```bash
cd examples/mw_gas
srun -p debug -N1 -n1 -c 32 -t 30 bash build_gadget4.sh
```

`build_gadget4.sh` copies `Config.sh` into `$NBODY_RUNS/builds/gadget4_mw_gas/` and runs, from the
Gadget4 source tree,

```bash
make -j 32 DIR=$NBODY_RUNS/builds/gadget4_mw_gas PYTHON=python3
```

`DIR=` is Gadget4's out-of-tree build: it reads `DIR/Config.sh` and writes `DIR/build/` and
`DIR/Gadget4`. `SYSTYPE=Generic-gcc` (set by `modules.sh`) selects `mpicxx -O3 -march=native`;
the GSL and HDF5 headers and libraries are found through the `CPATH`/`LIBRARY_PATH` variables that
the modules set, so no `Makefile.systype` edits are needed.

> Compile on a compute node (`srun`) rather than on the login node. The CPUs are the same
> model, so `-march=native` binaries run everywhere, but a parallel build is heavy for a shared login node.

Check the result:

```bash
ldd $NBODY_RUNS/builds/gadget4_mw_gas/Gadget4 | grep -E 'hdf5|gsl|mpi'
#   libhdf5.so.310 => /usr/local/hdf5/1.14.3/serial/gnu/lib/...
#   libgsl.so.0    => /usr/local/gsl-1.16/lib/...
#   libmpi.so.40   => /usr/local/openmpi/4.1.5/gnu/lib/...
```

If you change `Config.sh`, rerun `build_gadget4.sh`; Gadget4 detects the change and recompiles.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `git: command not found` in a job | run `env/fetch_sources.sh` on the login node first |
| `Could not compile test program which uses libpython3.11` (Agama) | the patch was not applied: rerun `env/fetch_sources.sh` |
| `mpicxx: command not found` | `source env/modules.sh` |
| `fatal error: gsl/gsl_rng.h` / `hdf5.h` | modules not loaded in the shell that runs `make` |

Next: [02 — Initial conditions](02_initial_conditions.md).
