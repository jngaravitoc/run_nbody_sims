"""Helpers for analysing the examples/mw_gas Gadget4 runs with pynbody.

Import this module from the notebooks/ directory (or anywhere with a copy of
notebooks/config.ini in the working directory) so pynbody maps the particle types correctly.
"""
import glob
import os

import h5py
import numpy as np
import pynbody

TIME_UNIT_GYR = 0.977792  # 1 kpc / (1 km/s) in Gyr: Gadget4 time unit for these runs


def run_dir(name="mw_gas"):
    """Output directory of a run under $NBODY_RUNS (default ~/nbody_runs)."""
    base = os.environ.get("NBODY_RUNS", os.path.expanduser("~/nbody_runs"))
    return os.path.join(base, "runs", name, "output")


def snapshots(name="mw_gas"):
    """Sorted list of snapshot files of a run."""
    return sorted(glob.glob(os.path.join(run_dir(name), "snapshot_*.hdf5")))


def load(path, center=True):
    """Load a snapshot in physical units (kpc, Msun, km/s), with the correct time.

    * s.properties['time'] is set from the header Time; pynbody would otherwise
      derive an "age of the universe" from the (meaningless) cosmology of an isolated run.
    * s['comp'] tags the InkWell components: 0 gas, 1 DM halo, 2 stellar disk, 3 bulge.
      InkWell numbers ParticleIDs consecutively by PartType from 1, and Gadget4 keeps them.
    * If center=True, the snapshot is centred on the stars (shrinking sphere) and their bulk
      velocity, and rotated so the stellar disk's angular momentum points along +z (face-on).
    """
    s = pynbody.load(path)
    if len(s.s) == 0:
        raise RuntimeError("No star particles: run from notebooks/ so pynbody picks up config.ini")
    with h5py.File(path, "r") as f:
        t = f["Header"].attrs["Time"]
        n = f["Header"].attrs["NumPart_Total"]
    s.properties["time"] = pynbody.units.Gyr * t * TIME_UNIT_GYR
    s.physical_units()

    edges = np.cumsum(n)                    # IDs 1..edges[0] gas, ..edges[1] DM, ...
    s["comp"] = np.searchsorted(edges, s["iord"] - 1, side="right")
    if center:
        pynbody.analysis.faceon(s, disk_size="5 kpc")  # centres on the stars, then rotates
    return s


def time_myr(s):
    return float(s.properties["time"].in_units("Myr"))
