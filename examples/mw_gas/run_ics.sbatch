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
# Generate Gadget4 ICs with InkWell on a compute node.  Submit from examples/mw_gas/:
#   sbatch run_ics.sbatch                                    # full 10M-particle ICs
#   sbatch --partition=debug run_ics.sbatch inkwell_mw_gas_test.yaml mw_gas_test
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
time inkwell "$CONFIG" --format gadget4 -o "$OUT" --seed 42
python check_ics.py "$OUT/ic_gadget.hdf5" --plot "$OUT/ics_check.png"
