# InkWell → Gadget-4: compatibility test report

**Tested:** 2026-10-02 on the geryon3 cluster
**InkWell:** `8c765a6`
**Gadget-4:** `6fb393b`
**Agama:** 1.0.160 (`60d8d8b`)
**pynbody:** 2.8.0 (`2c9e0a33`)
**Prepared for:** the InkWell developer (github.com/JASHunt/InkWell)

This is, as far as we know, the first test of InkWell's `--format gadget4` output with Gadget-4
itself. The ICs are an isolated Milky Way-like galaxy:

| Component | Mass [Msun] | Details |
|---|---|---|
| NFW halo | M_vir = 1e12 | c = 10 |
| Exponential stellar disk | 4.5e10 | R_d = 3 kpc, z0 = 0.3 kpc, `toomre_q: 2` |
| Hernquist bulge | 1e10 | |
| `isothermal` gas disk | 5e9 | 10⁴ K |

The configs are `examples/mw_gas/inkwell_mw_gas{,_test}.yaml` in this repository. They were
generated at 100k and 10M particles and run with four Gadget-4 builds:

| Build | Config.sh options (plus SELFGRAVITY, NTYPES=6, DOUBLEPRECISION=1) | Run |
|---|---|---|
| Isothermal | `ISOTHERM_EQS` | 100k for 500 Myr; 10M for 2 Gyr |
| Adiabatic (Gadget-4 default SPH) | — | 100k for 200 Myr |
| Cooling + star formation | `COOLING`, `STARFORMATION` | 100k for 200 Myr |
| Isothermal, IC u unconverted | `ISOTHERM_EQS` | 100k for 200 Myr |

**Bottom line.** The format is compatible: Gadget-4 reads the files in every configuration, the
galaxy is in equilibrium, and the optional fields are ingested correctly. There is one real
interoperability bug (missing unit metadata, issue 1). There are also two conventions that
silently give the wrong physics in common Gadget-4 setups (issues 2 and 3), and a few smaller
items.

---

## What works (verified)

| Check | Result |
|---|---|
| Gadget-4 reads `ic_gadget.hdf5` | Yes, with `ICFormat 3` in every build. Header types are accepted (`NumPart_ThisFile` uint32, `NumPart_Total` uint64, zero `MassTable`). The uint64 `ParticleIDs` read correctly into Gadget-4's default 32-bit IDs. |
| PartType mapping and IDs | Gas → 0, DM → 1, disk → 2, bulge → 3, as documented. IDs are unique, consecutive by type, and preserved by Gadget-4, which makes them handy for tagging components later. |
| Units | The parameter-file lines in the README (kpc, 1e10 Msun, km/s) are correct. In the evolved run the gas ⟨v_φ⟩ tracks v_c from the mass distribution. |
| Equilibrium (100k, isothermal, 500 Myr) | Energy drift 1.8×10⁻⁴. No bar (A₂ ≤ 0.05). Σ(R) stable to ≲ 8%. No rings or gaps. Rotation curve unchanged. |
| Disc DF calibration | `Rd(DF)=3.005 vs 3.000 kpc, z_half=330 vs 330 pc`. Q(2R_d) = 1.9 measured from the particles. |
| `STARFORMATION` build | Gadget-4 reads `StellarFormationTime` on PartType2/3 and `Metallicity` on PartType0/2/3. Snapshot 0 matches the IC values exactly, particle by particle. Star formation proceeds (170 of 3333 gas particles converted in 200 Myr), and new PartType4 stars inherit the gas Z. The README statement "Gadget-4 only reads the last two when compiled with STARFORMATION" is confirmed: `src/io/snap_io.cc`, and `src/io/io.cc` (`AGE_BLOCK` = types 2–4, `Z_BLOCK` = types 0, 2–4 for HDF5). |
| Adiabatic default build | Runs. `InternalEnergy` in (km/s)² with u = P/((γ−1)ρ) is the right convention here. |
| Cost | 10M-particle ICs in 9.5 min on one 64-core node. |

---

## Issues, most important first

### 1. [Bug] The Gadget-4 file has no unit metadata, so pynbody misreads it by factors of 1/h and 1000/h

`write_gadget4` (`inkwell/io.py`) writes no unit attributes. It also writes the input cosmology into
the header (`HubbleParam = 0.674`, `Omega0`, `OmegaLambda`) of a file meant for a non-cosmological
run.

Gadget-4 itself does not care. Analysis tools do. pynbody looks for `UnitLength_in_cm`,
`UnitMass_in_g`, and `UnitVelocity_in_cm_per_s` in a `Units` group or in Gadget-4's `Parameters`
group. When it finds neither, it falls back to Gadget-2 cosmological defaults (`Mpc a h^-1`,
`1e10 Msol h^-1`) and applies `h = HubbleParam`.

Measured on the 100k IC, comparing pynbody's values with the raw values:

| File | Mass | Length | Velocity |
|---|---|---|---|
| InkWell output as-is | ×1.4837 (= 1/h) | ×1483.7 (= 1000/h) | ×1.000 |
| + `Parameters` group with units | ×1.0003 | ×1.0000 | ×1.000 |
| + units and `HubbleParam = 1` | ×1.0003 | ×1.0000 | ×1.000 |

The 0.03% residual is only the Msun constant (1.989e33 vs pynbody's 1.98847e33 g).

**Suggested fix.** Write a `Parameters` group the way Gadget-4 snapshots do. We verified that
Gadget-4 runs normally from a file with this group, and pynbody then reads it exactly:

```python
# in write_gadget4(), after creating the Header
par = f.create_group('Parameters')
par.attrs['UnitLength_in_cm'] = 3.085678e21
par.attrs['UnitMass_in_g'] = 1.989e43
par.attrs['UnitVelocity_in_cm_per_s'] = 1e5
par.attrs['ComovingIntegrationOn'] = 0
par.attrs['HubbleParam'] = 1.0
```

Also consider writing header `HubbleParam = 1.0`, `Omega0 = OmegaLambda = 0`. Keep the input
cosmology under `InkWell*` attributes, as is already done for `InkWellFormationRedshift`.

### 2. [Pitfall] `InternalEnergy` is 1.5× too large for Gadget-4's isothermal mode (`ISOTHERM_EQS`)

InkWell writes u = P/((γ−1)ρ) = 1.5 c_s², with γ = 5/3 and μ = 0.6 (`gas_disk.py` and `io.py`).
That is right for adiabatic SPH. Gadget-4's `ISOTHERM_EQS` instead documents and implements
P = ρu, with u read from the ICs as c_s²:

* `documentation/04_config-options.md`;
* `src/data/simparticles.h` (`get_utherm_from_entropy` returns `Entropy` directly);
* `GAMMA = 1`.

InkWell's `type: isothermal` gas disk is the natural partner for `ISOTHERM_EQS`, so a user
combining them silently starts the gas with 1.5× its hydrostatic pressure.

Measured with 100k particles (gas z_rms at R = 4–10 kpc):

| | t = 0 | 100 Myr | 200 Myr |
|---|---|---|---|
| u converted to c_s² (×2/3) | 0.189 kpc | 0.175 | 0.185 |
| InkWell u as-is | 0.189 kpc | 0.192 | 0.203 |

The effect is modest at this resolution but systematic.

**Suggestion.** Either:

* a note in the README's Gadget-4 section, or
* an option such as `--gadget-eos isothermal` that writes u = c_s² = (γ−1) u_adiabatic, and
  ideally records the convention in a header attribute.

Our workaround is `examples/mw_gas/fix_isothermal_u.py`.

### 3. [Semantics/docs] `virial_mass` is not the halo mass you get, and the reason isn't in the README

`agama_model.halo_density` normalises the NFW to (1 − Ω_b/Ω_m) M_vir. It then applies an
exp(−(r/r_t)²) taper at r_t = r_vir, which removes about another 19% (the docstring says
"M(<rcut) ~0.81 (1-fb) Mvir"). Both effects are documented only in that docstring. The README
table describes `virial_mass` as "Virial mass" and `omega_b` as "Baryon density parameter".

Consequence with Planck parameters as in `examples/mw_present.yaml` (Ω_b = 0.0493) and
`virial_mass: 1e12`:

| | Live DM halo | v_c(8 kpc) |
|---|---|---|
| `omega_b: 0.0493` | 6.83e11 Msun (= 0.843 × 0.81 × 1e12) | 206 km/s |
| `omega_b: 0` | 8.09e11 Msun | 214 km/s |

The removed "baryon share" (1.56e11 Msun) is not added back anywhere unless the user also
configures enough hot gas. For a disk galaxy specified with explicit baryonic components, the
total mass inside r_vir is therefore well below the requested M_vir. The run log prints
`Halo: Mvir = 1.0000e+12 Msun`, which reinforces the misunderstanding.

**Suggestions.**

* Document both factors in the README's `halo` and `cosmology` tables.
* Print the live halo mass in the run summary.
* Consider an explicit `baryon_fraction` key on the halo instead of tying it to cosmology.

### 4. [Docs] Gadget-4 must be compiled with `NTYPES=6`

InkWell always writes 6-element `NumPart_*` arrays. Gadget-4 aborts unless `NTYPES` equals that
length:

```
TERMINATE: ... read_header_fields(), file src/io/snap_io.cc, line 947:
Length of NumPart_ThisFile attribute (6) does not match NTYPES(ICS) (4)
```

The Gadget-4 default is 6, but users who trim types hit this. Gadget-4's own `G2-galaxy` example
uses `NTYPES=3`. A one-line README note would help, as would writing arrays of the actual
number of types used.

### 5. [Minor] The T → u conversion assumes fully ionised gas (μ = 0.6)

`constants.MYU = 0.6` is used for all gas. A Gadget-4 `COOLING` run computes the ionisation state
itself and treats 10⁴ K primordial gas as largely neutral (μ ≈ 1.2). It therefore interprets the
IC u as roughly twice the intended temperature and cools it back within the first ~100 Myr:
median u goes 206 → 108 (km/s)². The gas starts slightly out of the equilibrium InkWell built.

This is internally consistent for adiabatic runs, so it is low priority. Users with cooling may
want a μ option, or a note.

### 6. [Minor, future breakage] Deprecated Agama API

`inkwell/agama_model.py:211` calls `pot.forceDeriv(xyz)`. Agama 1.0.160 warns
`FutureWarning: forceDeriv is deprecated, use Potential.eval(..., der=True) instead`.

### 7. [Docs] Gadget-4 is not listed as a target code

The README introduction lists ChaNGa, Gasoline, and GCD+. Gadget-4 works and could be listed,
with the recommended `Config.sh` (`NTYPES=6`) and parameter-file lines.

---

## Gas vertical equilibrium: answered by the full run

In all three 100k builds the gas disk first contracted vertically (z_rms 0.19 → ~0.13 kpc at
50 Myr) and then rebounded to 0.18–0.20 kpc. At that resolution the gas softening (0.23 kpc) and
SPH smoothing lengths exceed the gas scale height, so we suspected a numerical cause.

The full-resolution run (10M particles, 50 pc softening, `ISOTHERM_EQS` with u converted) supports
that. The gas z_rms at R = 7–9 kpc goes 0.216 → 0.210 kpc at 200 Myr and settles at 0.201 kpc,
constant to ±0.002 kpc from 0.4 to 2 Gyr. So the InkWell hydrostatic profile is close to
equilibrium for Gadget-4's SPH: a ~7% one-time settling, with no collapse or rebound.

The snapshots are 200 Myr apart, so oscillations shorter than that cannot be excluded.

The stellar components also show a one-time adjustment in the first 200 Myr, then stay steady to
2 Gyr:

* inner stellar Σ (2–4 kpc) drops ~9%;
* Σ at 7–9 kpc rises ~7%;
* the fitted disk scale length grows ~6%.

It may be worth checking whether this comes from the CylSpline representation of the disk
potential used for the DF calibration.

## Reproducing

Everything is in this repository:

* `env/` for the environment;
* `examples/mw_gas/` for the configs, Gadget-4 `Config.sh` and parameters, and Slurm scripts;
* `examples/mw_gas/check_ics.py` for the IC diagnostics.

The compatibility-test builds (adiabatic and cooling + SF) differ from `examples/mw_gas/Config.sh`
only as listed in the table at the top. The star-formation parameters were taken from Gadget-4's
`examples/CollidingGalaxiesSFR`.
