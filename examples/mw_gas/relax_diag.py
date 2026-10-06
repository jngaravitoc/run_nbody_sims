#!/usr/bin/env python
"""Relaxation diagnostics of Gadget4 runs of the mw_gas model, snapshot by snapshot.

    python relax_diag.py RUN_OUTPUT_DIR [RUN_OUTPUT_DIR ...] [--labels a b] [--plot out.png] [--csv out.csv]

For every snapshot it measures (PartTypes: 0 gas, 1 DM, 2 stellar disk, 3 bulge):
  * the centre of mass and bulk velocity of each component;
  * the rms height z_rms of the gas and of the stellar disk at R = 4-10 and 7-9 kpc, measured
    about the component's OWN centre of mass (zc_*), and about the stellar-disk centre
    (zs_*, the convention used for the earlier numbers) for comparison;
  * the stellar surface density at R = 2-4 and 7-9 kpc, the exponential scale length fitted
    over 3-12 kpc, and the bar strength A2 (R < 6 kpc).
The disk is assumed to lie in the x-y plane, as InkWell generates it.
"""
import argparse
import csv
import glob
import os

import h5py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

TIME_UNIT_MYR = 977.792


def com(g):
    m = g["Masses"][:]
    return (m[:, None] * g["Coordinates"][:]).sum(0) / m.sum(), (m[:, None] * g["Velocities"][:]).sum(0) / m.sum()


def zrms(x, c, lo, hi):
    d = x - c
    R = np.hypot(d[:, 0], d[:, 1])
    sel = (R > lo) & (R < hi)
    return float(np.sqrt(np.mean(d[sel, 2] ** 2)))


def snapshot_row(path):
    with h5py.File(path, "r") as f:
        row = {"t_myr": f["Header"].attrs["Time"] * TIME_UNIT_MYR}
        cen = {}
        for t, name in [(0, "gas"), (1, "dm"), (2, "disk"), (3, "bulge")]:
            if f"PartType{t}" in f:
                c, v = com(f[f"PartType{t}"])
                cen[name] = c
                row.update({f"com_{name}_{a}": c[i] for i, a in enumerate("xyz")})
                row.update({f"vcom_{name}_{a}": v[i] for i, a in enumerate("xyz")})
        xs = f["PartType2/Coordinates"][:]
        ms = f["PartType2/Masses"][:]
        xg = f["PartType0/Coordinates"][:] if "PartType0" in f else None
    for lo, hi in [(4, 10), (7, 9)]:
        tag = f"{lo}_{hi}"
        row[f"zc_disk_{tag}"] = zrms(xs, cen["disk"], lo, hi)
        if xg is not None:
            row[f"zc_gas_{tag}"] = zrms(xg, cen["gas"], lo, hi)
            row[f"zs_gas_{tag}"] = zrms(xg, cen["disk"], lo, hi)
    d = xs - cen["disk"]
    R = np.hypot(d[:, 0], d[:, 1])
    phi = np.arctan2(d[:, 1], d[:, 0])
    sig = lambda lo, hi: ms[(R > lo) & (R < hi)].sum() * 1e10 / (np.pi * (hi ** 2 - lo ** 2)) / 1e6
    row["sig_disk_2_4"], row["sig_disk_7_9"] = sig(2, 4), sig(7, 9)
    sel = (R > 3) & (R < 12)
    h, e = np.histogram(R[sel], 18, weights=ms[sel])
    rc = 0.5 * (e[1:] + e[:-1])
    row["Rd_fit"] = float(-1 / np.polyfit(rc, np.log(h / (2 * np.pi * rc)), 1)[0])
    inner = (R < 6) & (abs(d[:, 2]) < 1)
    row["A2"] = float(abs(np.sum(ms[inner] * np.exp(2j * phi[inner]))) / ms[inner].sum())
    for a, b in [("gas", "disk"), ("disk", "dm")]:
        if a in cen and b in cen:
            row[f"sep_{a}_{b}"] = float(np.linalg.norm(cen[a] - cen[b]))
    return row


def diagnose(outdir):
    return [snapshot_row(p) for p in sorted(glob.glob(os.path.join(outdir, "snapshot_*.hdf5")))]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("outdirs", nargs="+")
    ap.add_argument("--labels", nargs="+")
    ap.add_argument("--plot")
    ap.add_argument("--csv")
    args = ap.parse_args()
    labels = args.labels or [os.path.basename(os.path.dirname(os.path.abspath(d))) for d in args.outdirs]

    runs = {lab: diagnose(d) for lab, d in zip(labels, args.outdirs)}
    cols = ["t_myr", "zc_gas_4_10", "zs_gas_4_10", "zc_gas_7_9", "zc_disk_7_9", "sep_gas_disk", "sep_disk_dm",
            "com_disk_z", "sig_disk_2_4", "sig_disk_7_9", "Rd_fit", "A2"]
    for lab, rows in runs.items():
        print(f"\n== {lab}")
        print("  ".join(f"{c:>12s}" for c in cols))
        for r in rows:
            print("  ".join(f"{r.get(c, np.nan):12.4g}" for c in cols))
    if args.csv:
        keys = sorted({k for rows in runs.values() for r in rows for k in r})
        with open(args.csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["run"] + keys)
            w.writeheader()
            for lab, rows in runs.items():
                for r in rows:
                    w.writerow({"run": lab, **r})
    if args.plot:
        fig, ax = plt.subplots(2, 2, figsize=(11, 7.5), constrained_layout=True)
        for lab, rows in runs.items():
            t = [r["t_myr"] for r in rows]
            g = lambda k: [r.get(k, np.nan) for r in rows]
            l, = ax[0, 0].plot(t, g("zc_gas_4_10"), "o-", ms=3, label=f"{lab}")
            ax[0, 0].plot(t, g("zs_gas_4_10"), ":", color=l.get_color())
            ax[0, 1].plot(t, g("zc_disk_7_9"), "o-", ms=3, color=l.get_color(), label=lab)
            ax[1, 0].plot(t, g("sep_gas_disk"), "o-", ms=3, color=l.get_color(), label=f"{lab} gas-disk")
            ax[1, 0].plot(t, g("sep_disk_dm"), "s--", ms=3, color=l.get_color(), label=f"{lab} disk-DM")
            ax[1, 1].plot(t, np.array(g("sig_disk_2_4")) / rows[0]["sig_disk_2_4"], "o-", ms=3, color=l.get_color(),
                          label=f"{lab} Σ(2-4 kpc)")
            ax[1, 1].plot(t, np.array(g("Rd_fit")) / rows[0]["Rd_fit"], "s--", ms=3, color=l.get_color(),
                          label=f"{lab} R_d")
        ax[0, 0].set(xlabel="t [Myr]", ylabel="kpc", title="gas z_rms, R = 4-10 kpc (solid: own COM; dotted: disk COM)")
        ax[0, 1].set(xlabel="t [Myr]", ylabel="kpc", title="stellar disk z_rms, R = 7-9 kpc")
        ax[1, 0].set(xlabel="t [Myr]", ylabel="kpc", title="centre-of-mass separations", yscale="log")
        ax[1, 1].set(xlabel="t [Myr]", ylabel="relative to t = 0", title="inner Σ and fitted R_d")
        for a in ax.flat:
            a.legend(fontsize=7)
        fig.savefig(args.plot, dpi=110)
        print(f"\nSaved {args.plot}")


if __name__ == "__main__":
    main()
