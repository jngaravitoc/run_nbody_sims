# 02 — Initial conditions with InkWell

We build an isolated Milky Way-like galaxy with four live components:

* a dark-matter (DM) halo;
* a stellar disk;
* a bulge;
* an isothermal gas disk.

[InkWell](../../codes/InkWell) samples the collisionless components from equilibrium distribution
functions computed with Agama. It puts the gas disk in vertical hydrostatic equilibrium and writes a
Gadget4 HDF5 file directly.

Prerequisite: [01 — Environment setup](01_environment_setup.md).

## 1. The model

| Component | Mass [Msun] | Profile | Reference |
|---|---|---|---|
| DM halo | M_vir = 1.0e12 | NFW, c = 10, truncated at r_vir = 212 kpc | Dutton & Macciò (2014) c–M relation |
| Stellar disk | 4.5e10 | exponential, R_d = 3.0 kpc; sech², z0 = 0.3 kpc; Toomre Q = 2 at 2R_d | Bland-Hawthorn & Gerhard (2016) |
| Bulge | 1.0e10 | Hernquist, a = 0.63 kpc | InkWell r_e–M relation |
| Gas disk | 5.0e9 (10% of the disk) | exponential, R_g = 6 kpc; isothermal 10⁴ K; hydrostatic | — |

The **DM halo** has an NFW profile, with a Gaussian taper beyond r_vir. The **bulge** uses the
InkWell r_e–M relation, r_e = 4.16 kpc (M/10¹¹)^0.56. The **gas disk**'s vertical structure comes
from hydrostatic equilibrium.

There is no thick disk, hot gas halo, or stellar halo; InkWell supports all three if you want them later.

### Particle numbers

| | Full run | Test run | Particle mass (full) |
|---|---|---|---|
| DM halo | 6,000,000 | 60,000 | 1.35e5 Msun |
| Stellar disk | 3,000,000 | 30,000 | 1.5e4 Msun |
| Bulge | 666,668 | 6,668 | 1.5e4 Msun |
| Gas | 333,333 | 3,333 | 1.5e4 Msun |
| **Total** | **10,000,001** | **100,001** | |

Why this split:

* **All baryonic particles have the same mass.** Unequal masses exchange energy through two-body
  encounters, which spuriously heats the lighter population.
* **DM particles are 9× heavier than baryons.** This is well below the ~10⁶ Msun at which DM
  particles noticeably heat a thin disk over a few Gyr (Ludlow et al. 2019, MNRAS 488, L123).
* **60% of the particles go to the halo.** This keeps the halo's discreteness noise low in the
  region the disk lives in.

### Five InkWell conventions to know

1. **`halo.baryon_fraction`.** `virial_mass` is the total halo mass that sets r_vir and the NFW
   normalisation. By default InkWell removes a cosmic baryon share Ω_b/Ω_m (16% for Planck) from
   the live DM halo and does not add it back. We set `baryon_fraction: 0.0`, so the live halo
   carries the full M_vir; our baryons are the components we specify explicitly.
2. **The halo is tapered at r_vir.** The density is multiplied by exp(−(r/r_vir)²), so the live
   halo contains ~0.81 M_vir = 8.1e11 Msun. The inner profile is the untruncated NFW. InkWell
   prints the result: `Live DM halo mass < rcut = 8.1498e+11 Msun = 0.815 Mvir`.
3. **The halo and bulge are sampled in mirrored pairs** (`assembly.antithetic`, on by default).
   InkWell draws N/2 particles and adds the mirror image (−x, −v) of each. The sample still follows
   the distribution function, but its centre of mass, bulk velocity, and every odd multipole are
   exactly zero. Without this, the halo's dense centre sits ~0.2 kpc off-centre at 100k particles
   and the disk wanders ~0.4 kpc around it. An odd particle count is rounded up, which is why the
   bulge has 6,668 (666,668) particles and the totals are 100,001 (10,000,001).
4. **The disks are recentred** (`assembly.recentre`, on by default). Random sampling leaves each
   disk's centre of mass and bulk velocity slightly off zero (up to 0.16 kpc and 4.6 km/s for the
   100k gas disk); InkWell shifts each to zero.
5. **The stellar disk is iterated into the self-consistent model** (`agama.disc_iterations`,
   default 2). InkWell calibrates the disk's distribution function to the requested profile, then
   rebuilds the potential from the disk it actually samples and recalibrates. Before this
   (`disc_iterations: 0`), the potential held the *analytic* exponential disk while the sampled
   disk had more mass inside 1 kpc and ~8% less at 3–4 kpc. The stars then started with too much
   rotation for the potential they actually felt, and the disk "breathed" radially for its first
   ~200 Myr (see tutorial 04, section 7). The cost is about 1.7× longer generation.

With the default baryon fraction, the halo would hold only 6.8e11 Msun and v_c(8 kpc) would drop
by about 6 km/s (measured with InkWell `4ab25f8`: 210 → 204 km/s).

These conventions need InkWell ≥ `3e5907e`; `env/versions.env` pins `1ba0858`.

## 2. The configuration files

* `examples/mw_gas/inkwell_mw_gas.yaml` — full resolution (10M particles).
* `examples/mw_gas/inkwell_mw_gas_test.yaml` — test (100k particles), identical otherwise.

Key parts, annotated:

```yaml
dynamics: agama            # DF-based equilibrium; 'jeans' is the legacy (less stable) method
cosmology:
  omega_b: 0.0493          # Planck; only used for the default baryon fraction
halo:
  type: nfw
  baryon_fraction: 0.0     # live halo = full M_vir (before the r_vir taper)
  virial_mass: 1.0e+12
  concentration: 10.0
  truncation: 1.0          # taper radius r_t = 1 x r_vir
disks:
  - type: stellar
    mass: 4.5e+10
    scale_length: 3.0      # kpc
    scale_height: 0.3      # kpc
    toomre_q: 2.0          # sets sigma_R; Q ~ 2 keeps the disk bar-stable for Gyrs
  - type: isothermal       # gas disk with fixed temperature
    mass: 5.0e+9
    scale_length: 6.0
    temperature: 1.0e+4    # K
assembly:
  rotation: none           # disk spins counter-clockwise seen from +z
  correct_halo_momentum: true
```

All keys are documented in the InkWell README (`~/codes/InkWell/README.md`, "Configuration reference").

## 3. Generate the ICs

InkWell is serial Python, but Agama uses OpenMP threads, so run it on a full compute node:

```bash
cd examples/mw_gas
# test ICs (100k): ~16 min on the debug partition
sbatch --partition=debug run_ics.sbatch inkwell_mw_gas_test.yaml mw_gas_test
# full ICs (10M): ~17 min
sbatch run_ics.sbatch inkwell_mw_gas.yaml mw_gas
```

`run_ics.sbatch` runs three steps:

```bash
OUT=$NBODY_RUNS/ics/mw_gas
python make_ics.py inkwell_mw_gas.yaml $OUT --gadget-eos isothermal --seed 42      # generate
python check_ics.py $OUT/ic_gadget.hdf5 --plot $OUT/ics_check.png                   # our checks
python $NBODY_RUNS/builds/src/InkWell/scripts/check_disc_equilibrium.py $OUT --softening 0.05
```

**`make_ics.py`** generates the model once and writes it in two formats: `ic_gadget.hdf5` for
Gadget-4 and `ic.hdf5` (InkWell's own format) for the equilibrium check. It is equivalent to
`inkwell inkwell_mw_gas.yaml --format gadget4 --gadget-eos isothermal --seed 42`, which can
only write one format per run.

The script picks the checker's softening from the particle number: 0.05 kpc at 10M, 0.2 kpc at
100k. It then deletes `ic.hdf5` (1.1 GB at 10M) unless you set `KEEP_INKWELL_HDF5=1`. The output:

```
$NBODY_RUNS/ics/mw_gas/
├── ic_gadget.hdf5        Gadget4 SnapFormat-3 ICs
├── agama_potential.ini   the potential the distribution functions were built in
├── used_params.yaml      the full parameter set InkWell used (provenance)
├── ics_check.png         diagnostic figure from check_ics.py
├── disc_equilibrium.txt  output of InkWell's disk-equilibrium check
└── inkwell_mw_gas.yaml   copy of the input
```

What to look for in the InkWell log:

* `Live DM halo mass < rcut = 8.1498e+11 Msun = 0.815 Mvir`. The halo particles actually carry
  8.09e11 Msun; the logged value comes from a slightly different profile integration.
* `disc DF calibration 3: Rd(DF)=2.999 vs 3.000 kpc, z_half(R=hd)=330 vs 330 pc`. The disk DF
  reproduces the requested scale length and thickness.
* `Agama: disc self-consistency iteration 2/2` with `sigma_r0` changing by < 1% from the first
  pass. The disk and the potential agree.
* `sampling 60000 dm_halo particles (30000 antithetic pairs)`, and in the recentring block
  `bulge` and `dm_halo shifted by 0.000 kpc`.
* `Done. Total particles: 100001`.

`agama_potential.ini` is what InkWell's `check_disc_equilibrium.py` compares the particles
against (see section 5).

### The file

InkWell's units in this file are kpc, km/s, and 1e10 Msun. Gas carries `InternalEnergy` in (km/s)².

| Group | Component | Datasets |
|---|---|---|
| `PartType0` | gas | Coordinates, Velocities, Masses, ParticleIDs, InternalEnergy, Metallicity |
| `PartType1` | DM halo | Coordinates, Velocities, Masses, ParticleIDs |
| `PartType2` | stellar disk | ... + Metallicity, StellarFormationTime (ignored by our Gadget4 build) |
| `PartType3` | bulge | same as PartType2 |

```python
import h5py
f = h5py.File("ic_gadget.hdf5")
print(dict(f["Header"].attrs))           # NumPart_Total = [333333, 6000000, 3000000, 666667, 0, 0]
print(f["PartType0/InternalEnergy"][:5])  # 137.6 (km/s)^2 = c_s^2 for 1e4 K (isothermal convention)
print(f["Header"].attrs["InkWellInternalEnergy"])  # 'cs2 (ISOTHERM_EQS)'
```

> **Match `--gadget-eos` to your Gadget4 build.** Our build uses `ISOTHERM_EQS`, which reads
> `InternalEnergy` as c_s² and uses P = ρu. `--gadget-eos isothermal` writes exactly that
> (u = c_s²) and records it in the header attribute `InkWellInternalEnergy`. The default,
> `--gadget-eos adiabatic`, writes u = P/((γ−1)ρ) = 1.5 c_s², which is right for standard SPH and
> for `COOLING` builds but would give an `ISOTHERM_EQS` run 1.5× too much gas pressure. The run
> scripts refuse ICs whose header does not say `cs2`.

## 4. Sanity checks (`check_ics.py`)

`check_ics.py` loads any Gadget4 HDF5 file (ICs or snapshot) and performs four checks:

* **Masses and particle numbers** per type.
* **Centre of mass and bulk velocity** of the system.
* **Circular velocity** v_c(R) in the midplane. It is computed from the actual particle
  distribution with a tree code (`pytreegrav`), split by component.
* **Stellar-disk kinematics:** ⟨v_φ⟩, σ_R, σ_z, Toomre Q(R) = σ_R κ / (3.36 G Σ), and the disk
  thickness.

```bash
python check_ics.py $NBODY_RUNS/ics/mw_gas_test/ic_gadget.hdf5 --softening 0.2
```

Results for the test ICs:

```
v_c(R = 8 kpc) = 214.8 km/s;  v_c in 5-20 kpc: 200-217 km/s
PASS: MW-like, roughly flat rotation curve
Stellar disk:  R [kpc]  v_phi  sigma_R  sigma_z   Q
                 3.5   152.0    82.1    47.5   1.96
                 5.5   172.2    62.3    35.4   1.85
                 7.5   186.2    47.4    27.8   1.95
                11.5   199.8    25.9    15.3   2.55
PASS: Toomre Q(2 R_d) = 1.85 (target ~2)
```

![IC diagnostics](img/ics_check_test.png)

How to read the figure:

* **Rotation curve (top left).** The disk dominates inside ~8 kpc and the halo outside. The stars
  lag v_c by ~30 km/s because of asymmetric drift. The gas follows v_c closely because its
  pressure support is small.
* **Surface density (top right).** Both profiles should be straight lines in log-linear: the
  stars with R_d = 3 kpc, the gas with 6 kpc.
* **Dispersions and Q (bottom).** σ_R > σ_z everywhere, and Q stays above 1.5 in the disk
  region. Q ≈ 2 suppresses bar and spiral instabilities over the 2 Gyr we simulate.

If v_c is too low, increase `virial_mass` or `concentration`. If Q < 1.5, increase `toomre_q` or
use `sigma_r0`.

## 5. Disk equilibrium (`check_disc_equilibrium.py`)

InkWell's checker answers a question `check_ics.py` cannot: is the stellar disk in equilibrium in
the potential the particles actually produce? If it is not, the disk "breathes" radially at the
start of the simulation (tutorial 04, section 7). It runs two tests and writes
`disc_equilibrium.txt`.

**Test 1** compares the circular velocity of the Agama potential with that of the particles,
separately for the spheroids (`Multipole`) and the disks (`CylSpline`). The disk ratio column
should be 1.00 ± 0.02 at every radius. Our 10M model:

```
   CylSpline (discs) vs particles ['gas_disk_1', 'stellar_disk_0']:
   R[kpc]   v_c(Agama)  v_c(part)  ratio
      0.5         58.9       58.4  0.992
      1.0         80.3       79.8  0.994
      2.0        106.9      106.9  1.000
      3.0        125.4      125.9  1.004
      4.0        138.8      139.0  1.001
      6.0        153.3      153.7  1.002
      8.0        155.5      155.6  1.001
     12.0        142.6      142.4  0.998
     20.0        110.2      110.1  1.000
```

With the old static disk (`agama.disc_iterations: 0`) the same model gives 1.61 at 0.5 kpc and
0.93 at 3–4 kpc.

**Test 2** integrates 20,000 disk stars for 300 Myr in the Agama potential, with no N-body. The
mean radial velocity ⟨v_R⟩ in every ring should stay within a few km/s of zero, without a
coherent pattern. Our 10M model stays within ±3 km/s at 2–14 kpc.

At 100k particles Test 1 is noisier: use 0.2 kpc softening and expect ratios within about ±0.04
inside 1 kpc.

Next: [03 — Running Gadget4](03_running_gadget4.md).
