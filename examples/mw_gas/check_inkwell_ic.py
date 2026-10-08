#!/usr/bin/env python
"""File-level checks of an InkWell Gadget-4 IC (InkWell >= 4ab25f8).

    python check_inkwell_ic.py ic_gadget.hdf5 [--compare-u other_ic.hdf5]

Checks:
  * unit metadata: the Parameters group, header HubbleParam/Omega0, InkWell* provenance and
    per-dataset *_scaling / to_cgs attributes
  * pynbody reads the file with unit factors of 1: once with pynbody's default family mapping
    (working directory outside the repo) and once with notebooks/config.ini
  * the InternalEnergy convention attribute, and the u ratio against another IC (--compare-u)
  * each component's mass-weighted centre of mass and mean velocity (InkWell now recentres them)
  * antithetic (mirrored) sampling of the DM halo and bulge; this fails unless --no-antithetic is
    given, for ICs made with assembly.antithetic: false or InkWell older than 3e5907e
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

import h5py
import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TOL = 1e-3


def status(ok):
    return "PASS" if ok else "FAIL"


def pynbody_ratios(path):
    """Unit factors pynbody applies, per PartType (run in a subprocess with a chosen cwd)."""
    import warnings

    import pynbody
    warnings.filterwarnings("ignore")
    s = pynbody.load(path)
    s.physical_units()
    out = {"families": {f.name: len(s[f]) for f in s.families()}, "h": s.properties.get("h")}
    with h5py.File(path, "r") as f:
        ids, m, x, v, u = [], [], [], [], []
        for k in sorted(f):
            if k.startswith("PartType"):
                g = f[k]
                ids.append(g["ParticleIDs"][:]); m.append(g["Masses"][:]); x.append(g["Coordinates"][:])
                v.append(g["Velocities"][:])
        ids = np.concatenate(ids); m = np.concatenate(m); x = np.concatenate(x); v = np.concatenate(v)
        u_raw = f["PartType0/InternalEnergy"][:] if "PartType0" in f else None
        g_ids = f["PartType0/ParticleIDs"][:] if "PartType0" in f else None
    order = np.argsort(ids)
    po = np.argsort(np.asarray(s["iord"]))
    out["mass"] = float(np.asarray(s["mass"].in_units("Msol"))[po].sum() / (m[order].sum() * 1e10))
    out["length"] = float(np.sqrt((np.asarray(s["pos"].in_units("kpc"))[po] ** 2).sum(1).mean())
                          / np.sqrt((x[order] ** 2).sum(1).mean()))
    out["velocity"] = float(np.sqrt((np.asarray(s["vel"].in_units("km s^-1"))[po] ** 2).sum(1).mean())
                            / np.sqrt((v[order] ** 2).sum(1).mean()))
    if u_raw is not None:
        gu = np.asarray(s.g["u"].in_units("km^2 s^-2"))[np.argsort(np.asarray(s.g["iord"]))]
        out["u"] = float(gu.mean() / u_raw[np.argsort(g_ids)].mean())
    return out


def run_pynbody_in(cwd, path):
    r = subprocess.run([sys.executable, os.path.abspath(__file__), "--pynbody-only", os.path.abspath(path)],
                       cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        return {"error": r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "unknown"}
    return json.loads(r.stdout.strip().splitlines()[-1])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--compare-u", help="another IC of the same model: compare gas u and positions")
    ap.add_argument("--no-antithetic", dest="antithetic", action="store_false",
                    help="the ICs were made without mirrored spheroid sampling (assembly.antithetic: false, "
                         "or InkWell < 3e5907e): report the pair check but do not fail on it")
    ap.add_argument("--pynbody-only", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.pynbody_only:
        print(json.dumps(pynbody_ratios(args.file)))
        return

    fails = 0
    with h5py.File(args.file, "r") as f:
        hdr = dict(f["Header"].attrs)
        print(f"File: {args.file}")
        print("\n[1] Unit metadata")
        par = dict(f["Parameters"].attrs) if "Parameters" in f else {}
        want = {"UnitLength_in_cm": 3.085678e21, "UnitMass_in_g": 1.989e43, "UnitVelocity_in_cm_per_s": 1e5,
                "ComovingIntegrationOn": 0, "HubbleParam": 1.0}
        for k, v in want.items():
            ok = k in par and np.isclose(float(par[k]), v)
            fails += not ok
            print(f"  {status(ok)}  Parameters/{k} = {par.get(k)} (want {v})")
        for k, v in {"HubbleParam": 1.0, "Omega0": 0.0, "OmegaLambda": 0.0}.items():
            ok = k in hdr and np.isclose(float(hdr[k]), v)
            fails += not ok
            print(f"  {status(ok)}  Header/{k} = {hdr.get(k)} (want {v})")
        prov = {k: hdr[k] for k in hdr if k.startswith("InkWell")}
        print(f"  info  provenance: {prov}")
        ds = f["PartType1/Coordinates"]
        scal = {k: ds.attrs[k] for k in ds.attrs}
        print(f"  info  PartType1/Coordinates attrs: {scal}")

        print("\n[2] InternalEnergy convention")
        conv = hdr.get("InkWellInternalEnergy")
        conv = conv.decode() if isinstance(conv, bytes) else conv
        print(f"  info  InkWellInternalEnergy = {conv!r}")
        if "PartType0" in f:
            u = f["PartType0/InternalEnergy"][:]
            print(f"  info  gas u: median {np.median(u):.2f} (km/s)^2, min {u.min():.2f}, max {u.max():.2f}")
        if args.compare_u:
            with h5py.File(args.compare_u, "r") as g:
                ia, ib = np.argsort(f["PartType0/ParticleIDs"][:]), np.argsort(g["PartType0/ParticleIDs"][:])
                ua, ub = f["PartType0/InternalEnergy"][:][ia], g["PartType0/InternalEnergy"][:][ib]
                same_pos = np.allclose(f["PartType0/Coordinates"][:][ia], g["PartType0/Coordinates"][:][ib])
                ratio = ua / ub
                print(f"  info  gas positions identical to {args.compare_u}: {same_pos}")
                print(f"  info  u(this) / u(other): median {np.median(ratio):.6f}, range {ratio.min():.6f}-{ratio.max():.6f}")

        print("\n[3] Component centre of mass and bulk velocity (InkWell recentring)")
        for k in sorted(f):
            if k.startswith("PartType"):
                g = f[k]
                m = g["Masses"][:]
                com = (m[:, None] * g["Coordinates"][:]).sum(0) / m.sum()
                vcm = (m[:, None] * g["Velocities"][:]).sum(0) / m.sum()
                print(f"  info  {k}: |COM| = {np.linalg.norm(com):.2e} kpc  |v_COM| = {np.linalg.norm(vcm):.2e} km/s")

        print("\n[4] Antithetic spheroids (InkWell >= 3e5907e): second half = mirror (-x, -v) of the first half")
        for k, name in [("PartType1", "DM halo"), ("PartType3", "bulge")]:
            if k not in f:
                continue
            x, v = f[f"{k}/Coordinates"][:], f[f"{k}/Velocities"][:]
            n = len(x)
            h = n // 2
            if n % 2:
                ok, detail = False, f"N = {n} is odd, so not antithetic"
            else:
                dx = np.abs(x[:h] + x[h:]).max()
                dv = np.abs(v[:h] + v[h:]).max()
                ok = dx < 1e-9 and dv < 1e-9
                detail = (f"N = {n}, max |x_i + x_(i+N/2)| = {dx:.1e} kpc, max |v_i + v_(i+N/2)| = {dv:.1e} km/s"
                          + ("  -> mirrored pairs" if ok else "  -> not mirrored"))
            if args.antithetic:
                fails += not ok
                print(f"  {status(ok)}  {name}: {detail}")
            else:
                print(f"  info  {name}: {detail} (not required: --no-antithetic)")

    print("\n[1b] pynbody unit factors (pynbody value / raw value; 1 = correct)")
    with tempfile.TemporaryDirectory() as tmp:
        for label, cwd in [("default config", tmp), ("notebooks/config.ini", os.path.join(REPO, "notebooks"))]:
            r = run_pynbody_in(cwd, args.file)
            if "error" in r:
                fails += 1
                print(f"  FAIL  {label}: {r['error']}")
                continue
            facs = {k: r[k] for k in ("mass", "length", "velocity", "u") if k in r}
            ok = all(abs(v - 1) < TOL for v in facs.values())
            fails += not ok
            print(f"  {status(ok)}  {label}: " + ", ".join(f"{k} x{v:.5f}" for k, v in facs.items())
                  + f"  | h = {r['h']} | families {r['families']}")

    print(f"\n{'ALL PASS' if fails == 0 else f'{fails} FAIL(S)'}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
