#!/bin/bash
#SBATCH --job-name=mw_gas
#SBATCH --partition=batch
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=64        # one MPI rank per core: 128 ranks
#SBATCH --exclusive
#SBATCH --time=7-00:00:00           # param.txt TimeLimitCPU = 6.9 days, so restart files are written first
#SBATCH --output=%x_%j.out
#
# Full run (10M particles, 2 Gyr).  Submit from examples/mw_gas/:
#   sbatch run_gadget4.sbatch
# Resubmitting the same script continues from output/restartfiles automatically.
set -euo pipefail
NAME=mw_gas
PARAM=param.txt
cd "$SLURM_SUBMIT_DIR"
source ../../env/modules.sh

RUN=$NBODY_RUNS/runs/$NAME
mkdir -p "$RUN"
cp "$PARAM" "$RUN/param.txt"
cp Config.sh "$RUN/"
cp "$NBODY_RUNS/builds/gadget4_mw_gas/Gadget4" "$RUN/"
touch "$RUN/empty.txt"
[ -f "$RUN/ics.hdf5" ] || python fix_isothermal_u.py "$NBODY_RUNS/ics/$NAME/ic_gadget.hdf5" "$RUN/ics.hdf5"

cd "$RUN"
FLAG=""
if [ -d output/restartfiles ]; then FLAG=1; echo "Restarting from output/restartfiles"; fi
echo "Gadget4 on $SLURM_NNODES node(s), $SLURM_NTASKS ranks: $SLURM_JOB_NODELIST  ($(date))"
mpirun -np "$SLURM_NTASKS" ./Gadget4 param.txt $FLAG
echo "Finished $(date)"
