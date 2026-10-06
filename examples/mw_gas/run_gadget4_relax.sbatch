#!/bin/bash
#SBATCH --job-name=mw_gas_relax
#SBATCH --partition=batch
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=64        # one MPI rank per core: 128 ranks
#SBATCH --exclusive
#SBATCH --time=12:00:00
#SBATCH --output=%x_%j.out
#
# Relaxation test: 10M particles, 300 Myr, a snapshot every 25 Myr, to resolve the
# initial adjustment of the disk. Needs ICs made with InkWell >= 4ab25f8 and
# --gadget-eos isothermal (u = c_s^2 for ISOTHERM_EQS). Submit from examples/mw_gas/:
#   sbatch run_gadget4_relax.sbatch [ICS_DIR]
set -euo pipefail
NAME=mw_gas_relax
PARAM=param_relax.txt
cd "$SLURM_SUBMIT_DIR"
source ../../env/modules.sh
ICS=${1:-$NBODY_RUNS/ics/mw_gas_iso}

RUN=$NBODY_RUNS/runs/$NAME
mkdir -p "$RUN"
cp "$PARAM" "$RUN/param.txt"
cp Config.sh "$RUN/"
cp "$NBODY_RUNS/builds/gadget4_mw_gas/Gadget4" "$RUN/"
touch "$RUN/empty.txt"
python - "$ICS/ic_gadget.hdf5" <<'PY'
import sys, h5py
conv = h5py.File(sys.argv[1], "r")["Header"].attrs.get("InkWellInternalEnergy", b"")
conv = conv.decode() if isinstance(conv, bytes) else str(conv)
if not conv.startswith("cs2"):
    sys.exit(f"{sys.argv[1]}: InternalEnergy is {conv!r}; regenerate with --gadget-eos isothermal")
PY
[ -f "$RUN/ics.hdf5" ] || cp "$ICS/ic_gadget.hdf5" "$RUN/ics.hdf5"

cd "$RUN"
FLAG=""
if [ -d output/restartfiles ]; then FLAG=1; echo "Restarting from output/restartfiles"; fi
echo "Gadget4 on $SLURM_NNODES node(s), $SLURM_NTASKS ranks: $SLURM_JOB_NODELIST  ($(date))"
mpirun -np "$SLURM_NTASKS" ./Gadget4 param.txt $FLAG
echo "Finished $(date)"
