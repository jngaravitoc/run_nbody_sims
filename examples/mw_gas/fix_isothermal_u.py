#!/usr/bin/env python
"""Convert InkWell gas internal energies for Gadget4's ISOTHERM_EQS.

    python fix_isothermal_u.py ic_gadget.hdf5 ics.hdf5

InkWell writes u = P / ((gamma - 1) rho) = 1.5 c_s^2, with gamma = 5/3.
With ISOTHERM_EQS, Gadget4 reads the InternalEnergy field as c_s^2 and
uses P = rho * u (documentation/04_config-options.md; src/data/simparticles.h).
Using InkWell's u directly would give 1.5x the hydrostatic pressure and the gas disk
would puff up.  This script copies the IC file and rescales PartType0/InternalEnergy
by (gamma - 1) = 2/3, so u = c_s^2 = kT / (mu m_p).  It refuses to run twice on the same file.
"""
import shutil
import sys

import h5py

GAMMA = 5.0 / 3.0

if len(sys.argv) != 3:
    sys.exit(__doc__)
src, dst = sys.argv[1:]
if src != dst:
    shutil.copyfile(src, dst)
with h5py.File(dst, "r+") as f:
    if f["Header"].attrs.get("IsothermalUFixed", 0):
        sys.exit(f"{dst}: InternalEnergy already converted, nothing done")
    u = f["PartType0/InternalEnergy"]
    u_old = u[...]
    u[...] = u_old * (GAMMA - 1.0)
    f["Header"].attrs["IsothermalUFixed"] = 1
    print(f"{dst}: gas u {u_old.mean():.2f} -> {u[...].mean():.2f} (km/s)^2 "
          f"(c_s = {u[...].mean() ** 0.5:.2f} km/s)")
