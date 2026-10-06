#!/bin/bash
#SBATCH --job-name=mw_gas_test
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=64        # one MPI rank per core
#SBATCH --time=12:00:00
#SBATCH --output=%x_%j.out
#
# Low-resolution test (100k particles, 500 Myr).  Submit from examples/mw_gas/:
#   sbatch run_gadget4_test.sbatch
set -euo pipefail
NAME=mw_gas_test
PARAM=param_test.txt
cd "$SLURM_SUBMIT_DIR"
source ../../env/modules.sh

RUN=$NBODY_RUNS/runs/$NAME
mkdir -p "$RUN"
cp "$PARAM" "$RUN/param.txt"
cp Config.sh "$RUN/"
cp "$NBODY_RUNS/builds/gadget4_mw_gas/Gadget4" "$RUN/"
touch "$RUN/empty.txt"
python - "$NBODY_RUNS/ics/$NAME/ic_gadget.hdf5" <<'PY'
import sys, h5py
conv = h5py.File(sys.argv[1], "r")["Header"].attrs.get("InkWellInternalEnergy", b"")
conv = conv.decode() if isinstance(conv, bytes) else str(conv)
if not conv.startswith("cs2"):
    sys.exit(f"{sys.argv[1]}: InternalEnergy is {conv!r}; regenerate with --gadget-eos isothermal (run_ics.sbatch)")
PY
[ -f "$RUN/ics.hdf5" ] || cp "$NBODY_RUNS/ics/$NAME/ic_gadget.hdf5" "$RUN/ics.hdf5"

cd "$RUN"
FLAG=""
if [ -d output/restartfiles ]; then FLAG=1; echo "Restarting from output/restartfiles"; fi
echo "Gadget4 on $SLURM_NNODES node(s), $SLURM_NTASKS ranks: $SLURM_JOB_NODELIST  ($(date))"
mpirun -np "$SLURM_NTASKS" ./Gadget4 param.txt $FLAG
echo "Finished $(date)"
