#!/usr/bin/env python
"""Generate an InkWell model once and write it in two formats.

    python make_ics.py CONFIG.yaml OUTDIR [--gadget-eos isothermal|adiabatic] [--seed 42]

* OUTDIR/ic_gadget.hdf5  Gadget-4 initial conditions
* OUTDIR/ic.hdf5         InkWell's own HDF5 format, needed by InkWell's
                         scripts/check_disc_equilibrium.py (with OUTDIR/agama_potential.ini)

The inkwell command line writes one format per run, and Agama-based generation takes
~16 min at 100k particles, so writing both from the same particles saves a second run and
guarantees that the equilibrium check sees exactly the particles Gadget-4 will run.
"""
import argparse
from pathlib import Path

from inkwell import generate
from inkwell.io import write_gadget4
from inkwell.parameters import read_input

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("config")
ap.add_argument("outdir")
ap.add_argument("--gadget-eos", choices=["adiabatic", "isothermal"], default="isothermal")
ap.add_argument("--seed", type=int, default=42)
args = ap.parse_args()

out = Path(args.outdir)
particles = generate(args.config, output_dir=str(out), fmt="hdf5", seed=args.seed, gadget_eos=args.gadget_eos)
write_gadget4(out / "ic_gadget.hdf5", particles, read_input(args.config),
              isothermal_u=(args.gadget_eos == "isothermal"))
print(f"Wrote {out / 'ic.hdf5'} (InkWell) and {out / 'ic_gadget.hdf5'} (Gadget-4, --gadget-eos {args.gadget_eos})")
