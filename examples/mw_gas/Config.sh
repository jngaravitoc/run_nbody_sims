# Gadget4 compile-time options for the isolated MW-like galaxy with isothermal gas.
# Changing anything here requires recompiling (bash build_gadget4.sh).

# --- Basic operation
SELFGRAVITY                 # compute self-gravity (tree only: no PMGRID, isolated, non-periodic)
NTYPES=6                    # 0 = gas, 1 = DM halo, 2 = stellar disk, 3 = bulge (InkWell mapping); 4, 5 unused
                            # but must exist: Gadget4 requires NTYPES = length of the IC header arrays (6)
NSOFTCLASSES=3              # 0 = gas, 1 = DM, 2 = stars (disk + bulge)

# --- Hydrodynamics
ISOTHERM_EQS                # P = rho * u with u = c_s^2 fixed per particle (from the ICs)

# --- Diagnostics
EVALPOTENTIAL               # potential energy in energy.txt -> energy conservation check
OUTPUT_POTENTIAL            # write Potential to every snapshot

# --- Numerics
DOUBLEPRECISION=1           # double-precision particle data and snapshot output
