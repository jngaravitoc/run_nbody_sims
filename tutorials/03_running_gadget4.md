# 03 — Running Gadget4 under Slurm

Prerequisites:

* [01 — Environment setup](01_environment_setup.md): Gadget4 compiled.
* [02 — Initial conditions](02_initial_conditions.md): ICs in `$NBODY_RUNS/ics/<name>/`.

All files are in `examples/mw_gas/`:

| File | Purpose |
|---|---|
| `Config.sh` | compile-time options, which require recompiling to change |
| `param_test.txt`, `param.txt` | runtime parameters for the test and full runs |
| `run_gadget4_test.sbatch`, `run_gadget4.sbatch` | Slurm job scripts |
| `param_relax.txt`, `run_gadget4_relax.sbatch` | 300 Myr relaxation test with a snapshot every 25 Myr |

## 1. Compile-time options (`Config.sh`)

```
SELFGRAVITY          # self-gravity via the tree (no PMGRID: isolated, non-periodic, no FFTW)
NTYPES=6             # must equal the length of the IC header arrays (InkWell writes 6)
NSOFTCLASSES=3       # three softening lengths: gas, DM, stars
ISOTHERM_EQS         # isothermal gas: P = rho c_s^2, c_s^2 = u from the ICs, fixed per particle
EVALPOTENTIAL        # potential energy -> total energy in energy.txt (conservation check)
OUTPUT_POTENTIAL     # gravitational potential in every snapshot
DOUBLEPRECISION=1    # double-precision internal particle data
```

Notes:

* **`NTYPES`.** Gadget4 aborts with `Length of NumPart_ThisFile attribute (6) does not match
  NTYPES(ICS) (4)` if this does not match the ICs. Empty types cost nothing.
* **No cooling and no star formation**, by design. The gas stays at 10⁴ K, the effective
  temperature of a turbulent, photo-heated warm ISM.
* **Adding star formation.** That would need `COOLING` and `STARFORMATION` (see
  `~/codes/gadget4/examples/CollidingGalaxiesSFR`), a `TREECOOL` file, and the star-formation
  parameters. Drop `ISOTHERM_EQS` and generate the ICs with `--gadget-eos adiabatic` (the default) in that case.
* All options are documented in `~/codes/gadget4/documentation/04_config-options.md`.

## 2. Runtime parameters (`param.txt`)

**Units: kpc, 1e10 Msun, km/s.** The time unit is then 1 kpc/(km/s) = 0.9778 Gyr, the same unit
system InkWell writes.

| Parameter | Full | Test | Comment |
|---|---|---|---|
| `TimeMax` | 2.045408 | 0.511352 | 2 Gyr / 0.5 Gyr |
| `TimeBetSnapshot` | 0.2045408 | 0.0255676 | 200 Myr → 11 snapshots (~0.37 GB each, ~4 GB) / 25 Myr → 21 snapshots |
| `TimeBetStatistics` | 0.0051135 | same | `energy.txt` every 5 Myr |
| `ICFormat` / `SnapFormat` | 3 / 3 | | HDF5; `InitCondFile ./ics` means `./ics.hdf5` |
| `ComovingIntegrationOn` | 0 | | Newtonian, non-cosmological; `BoxSize 0` = non-periodic |
| `ErrTolIntAccuracy` | 0.012 | | timestep dt = sqrt(2 η ε / \|a\|) |
| `MaxSizeTimestep` | 0.005 | | ≈ 5 Myr |
| `CourantFac` | 0.15 | | SPH Courant factor |
| `ErrTolForceAcc` | 0.005 | | relative tree opening criterion |
| `DesNumNgb` | 64 | | SPH neighbours (cubic spline kernel) |
| `InitGasTemp` | 0 | | 0 = use the u from the ICs |
| `MaxMemSize` | 6000 | 4000 | MB per MPI rank (512 GB / 64 cores ≈ 8 GB available) |
| `TimeLimitCPU` | 597600 | 42000 | seconds; slightly less than the Slurm `--time` |
| `CpuTimeBetRestartFile` | 7200 | | restart files every 2 h |

### Gravitational softening

| Class | Particles | Full | Test |
|---|---|---|---|
| 0 | gas | 0.05 kpc | 0.23 kpc |
| 1 | DM halo | 0.15 kpc | 0.70 kpc |
| 2 | stellar disk + bulge | 0.05 kpc | 0.23 kpc |

The lengths are Plummer-equivalent; the spline kernel goes exactly Newtonian at 2.8 ε. They were
chosen as follows:

* **Stars and gas** need ε well below the disk scale height (z0 = 300 pc) to resolve its vertical
  structure. With ε = 50 pc ≈ z0/6, the 1.5e4 Msun particles are not dominated by two-body
  scattering.
* **The DM halo** follows the usual ε ∝ N^(−1/3) scaling for an NFW halo (Power et al. 2003,
  Dehnen 2001). At 6M particles that gives ~0.1–0.2 kpc. Larger values would soften the inner
  halo; smaller ones only add noise.
* **The test run** scales all softenings by (N_full/N_test)^(1/3) = 100^(1/3) ≈ 4.6.

The full list of parameters is in `~/codes/gadget4/documentation/05_parameterfile.md`.

## 3. The Slurm script

`run_gadget4.sbatch` (full run):

```bash
#SBATCH --partition=batch
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=64        # one MPI rank per core: 128 ranks
#SBATCH --exclusive
#SBATCH --time=7-00:00:00
...
source ../../env/modules.sh                     # same modules as for compiling
RUN=$NBODY_RUNS/runs/mw_gas
cp param.txt Config.sh $NBODY_RUNS/builds/gadget4_mw_gas/Gadget4 $RUN/   # run dir is self-documenting
# (a check that the ICs were made with --gadget-eos isothermal: header InkWellInternalEnergy = 'cs2 ...')
[ -f $RUN/ics.hdf5 ] || cp $NBODY_RUNS/ics/mw_gas/ic_gadget.hdf5 $RUN/ics.hdf5
cd $RUN
FLAG=""; [ -d output/restartfiles ] && FLAG=1    # continue from restart files if they exist
mpirun -np $SLURM_NTASKS ./Gadget4 param.txt $FLAG
```

Things to know:

* **Submit from `examples/mw_gas/`.** Slurm runs a copy of the script, so it finds the repo
  through `$SLURM_SUBMIT_DIR`.
* **InfiniBand.** `env/modules.sh` sets `OMPI_MCA_btl=^openib`: the nodes' Mellanox InfiniBand is
  driven by UCX, and the legacy `openib` component only prints device-initialisation warnings.
* **One rank per node does no computation.** By default Gadget4 dedicates one MPI rank per node to
  shared-memory communication, so 128 ranks give 126 workers.
* **Each run directory is self-contained.** It holds the executable, `Config.sh`, `param.txt`, and
  the ICs that produced it.

## 4. Submit: test first, then the full run

```bash
cd examples/mw_gas
sbatch run_gadget4_test.sbatch                 # debug partition, 1 node; 1.5 min
# ...check the test (section 6), then:
sbatch run_gadget4.sbatch                      # batch partition, 2 nodes
```

ICs and the run can be chained so that the run starts only if IC generation succeeded:

```bash
ICJ=$(sbatch --parsable run_ics.sbatch inkwell_mw_gas.yaml mw_gas)
sbatch --dependency=afterok:$ICJ run_gadget4.sbatch
```

## 5. Monitoring

```bash
squeue -u $USER                                 # queue state
sacct -j <jobid> --format=JobID,Elapsed,State,MaxRSS
tail -f examples/mw_gas/mw_gas_<jobid>.out      # stdout: one "Sync-Point" line per step
cd $NBODY_RUNS/runs/mw_gas/output
```

Gadget4 writes these files to `output/`:

| File | What it tells you |
|---|---|
| `cpu.txt` | wall-clock per step and cumulative, split into tree gravity, SPH, domain, I/O |
| `timebins.txt` | particle count per timestep bin; the smallest occupied bin sets the cost |
| `energy.txt` | time, thermal, potential, kinetic energy (total, then per type), mass per type |
| `info.txt` | one line per step: time and number of active particles |
| `memory.txt` | memory use per rank (compare with `MaxMemSize`) |
| `snapshot_NNN.hdf5` | the snapshots |
| `restartfiles/` | binary restart files (one per rank) |

**Progress.** Simulation time versus wall time:

```bash
awk '/^Step/{t=$4} /^total /{w=$4} END{printf "t = %.0f Myr after %.1f h\n", t*977.8, w/3600}' cpu.txt
```

**Energy conservation.** Column 1 of `energy.txt` is time; columns 2–4 are total thermal,
potential, and kinetic energy:

```python
import numpy as np
e = np.loadtxt("energy.txt")
E = e[:, 1] + e[:, 2] + e[:, 3]
print("relative drift:", (E[-1] - E[0]) / abs(E[0]))
```

The test run gives 1.8×10⁻⁴ over 500 Myr. Anything above ~1% means the time integration or force
accuracy is too loose.

## 6. What the test run should show

Results from the 100k-particle test, 500 Myr on 64 cores (wall time 1 min 24 s):

| Check | Result |
|---|---|
| Energy drift | 1.8×10⁻⁴ |
| Bar strength A₂ (R < 6 kpc) | 0.004 → 0.012 (max 0.05): no bar |
| Stellar Σ(R) | changes ≲ 8%, consistent with particle noise |
| Stellar z_rms at 7–9 kpc | 0.54 → 0.61 kpc (+12%) |
| Gas z_rms at 7–9 kpc | 0.21 → 0.28 kpc |
| Face-on maps | axisymmetric, no rings or gaps |

The thickening of both disks is expected at test resolution:

* **Stars.** Two-body heating by the 1.1e7 Msun test DM particles thickens the stellar disk. The
  full run's DM particles are 80× lighter, and the heating rate scales with the DM particle mass.
* **Gas.** The gas disk thickens because the test softening (0.23 kpc) exceeds the gas scale height.

## 7. Restarts

Gadget4 writes restart files every `CpuTimeBetRestartFile` (2 h) and when it approaches
`TimeLimitCPU`. To continue a stopped or timed-out job, resubmit the same script:

```bash
sbatch run_gadget4.sbatch      # detects output/restartfiles and runs ./Gadget4 param.txt 1
```

Rules for restarts:

* **Restart with the same number of MPI ranks.** Restart files are per rank.
* **A few parameters may change on restart:** `TimeMax`, `TimeLimitCPU`, `CpuTimeBetRestartFile`,
  `MaxMemSize`, output cadence.
* **Starting from a snapshot instead:** use `./Gadget4 param.txt 2 <snapnum>`, with any
  rank count.
* **Start from scratch:** delete `$NBODY_RUNS/runs/<name>`.

## 8. Cost of the full run

See the "Full run" section in the [README](../README.md) for measured wall time and disk usage.

Next: [04 — Analysis with pynbody](04_analysis_pynbody.md).
