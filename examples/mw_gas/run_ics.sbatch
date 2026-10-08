#!/bin/bash
#SBATCH --job-name=mw_gas_ics
#SBATCH --partition=batch
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64          # Agama uses OpenMP threads
#SBATCH --mem=200G
#SBATCH --time=12:00:00
#SBATCH --output=%x_%j.out
#
# Generate Gadget4 ICs with InkWell (>= 3e5907e) on a compute node and check them.
# Submit from examples/mw_gas/:
#   sbatch run_ics.sbatch                                    # full 10M-particle ICs (~17 min)
#   sbatch --partition=debug run_ics.sbatch inkwell_mw_gas_test.yaml mw_gas_test    # 100k (~16 min)
# Set KEEP_INKWELL_HDF5=1 to keep ic.hdf5 (InkWell format, 1.1 GB at 10M) after the checks.
set -euo pipefail
CONFIG=${1:-inkwell_mw_gas.yaml}
NAME=${2:-mw_gas}
cd "$SLURM_SUBMIT_DIR"
source ../../env/modules.sh
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

OUT=$NBODY_RUNS/ics/$NAME
mkdir -p "$OUT"
cp "$CONFIG" "$OUT/"
echo "InkWell: $CONFIG -> $OUT  ($(date))"
# --gadget-eos isothermal: InternalEnergy = c_s^2, as Gadget4 ISOTHERM_EQS (Config.sh) expects.
# make_ics.py writes ic_gadget.hdf5 (Gadget-4) and ic.hdf5 (InkWell) from the same particles.
time python make_ics.py "$CONFIG" "$OUT" --gadget-eos isothermal --seed 42

# 1. Our checks: masses, centring, rotation curve, Toomre Q (figure: ics_check.png)
python check_ics.py "$OUT/ic_gadget.hdf5" --plot "$OUT/ics_check.png"

# 2. InkWell's disk-equilibrium check: realised disk vs the disk in the Agama potential, and
#    disk orbits integrated in that potential. Softening 50 pc suits 10M particles; at 100k a
#    few gas particles near the test radii dominate, so use 0.2 kpc there.
NPART=$(python -c "import h5py; print(int(sum(h5py.File('$OUT/ic_gadget.hdf5')['Header'].attrs['NumPart_Total'])))")
EPS=$(python -c "print(0.05 if $NPART >= 1000000 else 0.2)")
python "$NBODY_RUNS/builds/src/InkWell/scripts/check_disc_equilibrium.py" "$OUT" --softening "$EPS" \
    | tee "$OUT/disc_equilibrium.txt"

if [ "${KEEP_INKWELL_HDF5:-0}" != "1" ]; then rm -f "$OUT/ic.hdf5"; fi
