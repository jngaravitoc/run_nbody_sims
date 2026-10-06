#!/usr/bin/env python
"""Sanity checks for a Gadget4 HDF5 initial-conditions (or snapshot) file.

    python check_ics.py ic_gadget.hdf5 [--softening 0.05] [--plot ics_check.png]

Checks (units: kpc, km/s, 1e10 Msun as written by InkWell):
  * mass and particle number per PartType
  * centre of mass and net momentum of the whole system
  * circular velocity v_c(R) in the disk midplane, from the gravitational
    acceleration of all particles (pytreegrav tree code)
  * mean rotation v_phi, sigma_R, sigma_z of the stellar disk and Toomre Q(R)
  * gas rotation and gas internal energy (sound speed)
Prints PASS/WARN lines and saves a 4-panel diagnostic figure.
"""
import argparse

import h5py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pytreegrav import AccelTarget

G = 4.30091e-6 * 1e10   # kpc (km/s)^2 / (1e10 Msun)
NAMES = {0: "gas", 1: "DM halo", 2: "stellar disk", 3: "bulge", 4: "stars"}


def load(path):
    parts = {}
    with h5py.File(path, "r") as f:
        for key in f:
            if key.startswith("PartType"):
                g = f[key]
                d = {k: g[k][...] for k in ("Coordinates", "Velocities", "Masses")}
                if "InternalEnergy" in g:
                    d["u"] = g["InternalEnergy"][...]
                parts[int(key[8:])] = d
        time = f["Header"].attrs.get("Time", 0.0)
    return parts, time


def radial_profile(R, values, edges, func=np.mean):
    idx = np.digitize(R, edges) - 1
    out = np.full(len(edges) - 1, np.nan)
    for i in range(len(edges) - 1):
        sel = idx == i
        if sel.sum() >= 10:
            out[i] = func(values[sel])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--softening", type=float, default=0.05, help="softening for v_c estimate [kpc]")
    ap.add_argument("--plot", default="ics_check.png")
    ap.add_argument("--rmax", type=float, default=25.0, help="outer radius of profiles [kpc]")
    args = ap.parse_args()

    parts, time = load(args.file)
    print(f"File: {args.file}   Time = {time:g}")

    # --- masses and numbers
    print("\nComponent           N        M_tot [Msun]   m_p [Msun]")
    for t, d in sorted(parts.items()):
        m = d["Masses"]
        print(f"  {t} {NAMES.get(t, '?'):14s} {len(m):9d}   {m.sum() * 1e10:11.4e}   {m.mean() * 1e10:10.3e}")

    pos = np.concatenate([d["Coordinates"] for d in parts.values()])
    vel = np.concatenate([d["Velocities"] for d in parts.values()])
    mass = np.concatenate([d["Masses"] for d in parts.values()])
    com = (mass[:, None] * pos).sum(0) / mass.sum()
    vcom = (mass[:, None] * vel).sum(0) / mass.sum()
    print(f"\nCentre of mass        [kpc]  : {np.round(com, 3)}")
    print(f"Centre-of-mass velocity [km/s]: {np.round(vcom, 3)}")
    ok = np.linalg.norm(com) < 0.5 and np.linalg.norm(vcom) < 2.0
    print(("PASS" if ok else "WARN") + ": system centred at rest (|COM| < 0.5 kpc, |v_COM| < 2 km/s)")

    # Centre on the stellar disk for the profiles
    ref = parts.get(2, parts[max(parts)])
    c0 = np.average(ref["Coordinates"], axis=0, weights=ref["Masses"])
    v0 = np.average(ref["Velocities"], axis=0, weights=ref["Masses"])

    # --- circular velocity in the midplane from the actual particle distribution
    Rgrid = np.linspace(0.5, args.rmax, 50)
    phis = np.linspace(0, 2 * np.pi, 64, endpoint=False)  # many azimuths: a 1e5-particle halo is lumpy on a ring
    tgt = np.array([[R * np.cos(p), R * np.sin(p), 0.0] for R in Rgrid for p in phis]) + c0
    vc_comp = {}
    for t, d in sorted(parts.items()):
        a = AccelTarget(tgt, d["Coordinates"], d["Masses"], softening_source=np.full(len(d["Masses"]), args.softening),
                        G=G, theta=0.5, method="tree", parallel=True)
        rhat = (tgt - c0) / np.linalg.norm(tgt - c0, axis=1)[:, None]
        ar = -(a * rhat).sum(1).reshape(len(Rgrid), len(phis)).mean(1)
        vc_comp[t] = ar * Rgrid
    vc2 = sum(vc_comp.values())
    vc = np.sqrt(np.clip(vc2, 0, None))

    i8 = np.argmin(abs(Rgrid - 8.0))
    sel = (Rgrid > 5) & (Rgrid < 20)
    print(f"\nv_c(R = 8 kpc) = {vc[i8]:.1f} km/s;  v_c in 5-20 kpc: {vc[sel].min():.0f}-{vc[sel].max():.0f} km/s")
    ok = 190 < vc[i8] < 250 and vc[sel].max() / vc[sel].min() < 1.25
    print(("PASS" if ok else "WARN") + ": MW-like, roughly flat rotation curve (190 < v_c(8) < 250, max/min < 1.25 in 5-20 kpc)")

    # --- stellar disk kinematics and Toomre Q
    edges = np.linspace(0, args.rmax, 26)
    Rc = 0.5 * (edges[1:] + edges[:-1])
    prof = {}
    for t in (2, 0):
        if t not in parts:
            continue
        x = parts[t]["Coordinates"] - c0
        v = parts[t]["Velocities"] - v0
        R = np.hypot(x[:, 0], x[:, 1])
        phi = np.arctan2(x[:, 1], x[:, 0])
        vR = v[:, 0] * np.cos(phi) + v[:, 1] * np.sin(phi)
        vphi = -v[:, 0] * np.sin(phi) + v[:, 1] * np.cos(phi)
        m = parts[t]["Masses"]
        prof[t] = dict(
            vphi=radial_profile(R, vphi, edges),
            sigR=radial_profile(R, vR, edges, np.std),
            sigz=radial_profile(R, v[:, 2], edges, np.std),
            Sigma=np.histogram(R, edges, weights=m)[0] / (np.pi * np.diff(edges ** 2)),
            zrms=radial_profile(R, x[:, 2], edges, lambda z: np.sqrt(np.mean(z ** 2))),
        )
    vc_at = np.interp(Rc, Rgrid, vc)
    Omega = vc_at / Rc
    dOm2 = np.gradient(Omega ** 2 * Rc ** 4, Rc)
    kappa = np.sqrt(np.clip(dOm2 / Rc ** 3, 0, None))
    if 2 in prof:
        p = prof[2]
        Q = p["sigR"] * kappa / (3.36 * G * p["Sigma"])
        print("\nStellar disk:  R [kpc]  v_phi  sigma_R  sigma_z   Q")
        for R in (4.0, 6.0, 8.0, 12.0):
            i = np.argmin(abs(Rc - R))
            print(f"               {Rc[i]:5.1f}  {p['vphi'][i]:6.1f}  {p['sigR'][i]:6.1f}  {p['sigz'][i]:6.1f}  {Q[i]:5.2f}")
        i6 = np.argmin(abs(Rc - 6.0))
        ok = 1.3 < Q[i6] < 3.0
        print(("PASS" if ok else "WARN") + f": Toomre Q(2 R_d) = {Q[i6]:.2f} (target ~2)")
    if 0 in prof:
        u = parts[0]["u"]
        print(f"\nGas: u = {u.min():.1f}-{u.max():.1f} (km/s)^2;  v_phi(8 kpc) = "
              f"{prof[0]['vphi'][np.argmin(abs(Rc - 8))]:.1f} km/s")

    # --- figure
    fig, ax = plt.subplots(2, 2, figsize=(10, 8), constrained_layout=True)
    a = ax[0, 0]
    for t, v2 in vc_comp.items():
        a.plot(Rgrid, np.sqrt(np.clip(v2, 0, None)), label=NAMES.get(t, t))
    a.plot(Rgrid, vc, "k", lw=2, label="total")
    if 2 in prof:
        a.plot(Rc, prof[2]["vphi"], "k--", label=r"stars $\langle v_\phi \rangle$")
    if 0 in prof:
        a.plot(Rc, prof[0]["vphi"], "k:", label=r"gas $\langle v_\phi \rangle$")
    a.set(xlabel="R [kpc]", ylabel="v [km/s]", title="Rotation curve", ylim=(0, None))
    a.legend(fontsize=8)
    a = ax[0, 1]
    for t, p in prof.items():
        a.semilogy(Rc, p["Sigma"] * 1e10 / 1e6, label=NAMES[t])
    a.set(xlabel="R [kpc]", ylabel=r"$\Sigma$ [M$_\odot$ pc$^{-2}$]", title="Surface density")
    a.legend()
    a = ax[1, 0]
    if 2 in prof:
        a.plot(Rc, prof[2]["sigR"], label=r"$\sigma_R$")
        a.plot(Rc, prof[2]["sigz"], label=r"$\sigma_z$")
    a.set(xlabel="R [kpc]", ylabel="km/s", title="Stellar disk dispersions")
    a.legend()
    a = ax[1, 1]
    if 2 in prof:
        a.plot(Rc, Q, label="Toomre Q (stars)")
        a.axhline(1, color="gray", ls=":")
    for t, p in prof.items():
        a.plot(Rc, p["zrms"], "--", label=f"z_rms {NAMES[t]} [kpc]")
    a.set(xlabel="R [kpc]", title="Stability and thickness", ylim=(0, 4))
    a.legend()
    fig.suptitle(f"{args.file}  (t = {time:g})")
    fig.savefig(args.plot, dpi=110)
    print(f"\nSaved {args.plot}")


if __name__ == "__main__":
    main()
