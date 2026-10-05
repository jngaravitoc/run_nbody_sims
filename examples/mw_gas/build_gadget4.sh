#!/bin/bash
# Compile Gadget4 for this example, out of tree, on a compute node.
#   srun -p debug -N1 -n1 -c 32 -t 30 bash build_gadget4.sh
# Produces $NBODY_RUNS/builds/gadget4_mw_gas/Gadget4.  $CODES_DIR/gadget4 is never touched:
# it builds from the clone made by env/fetch_sources.sh (run that on the login node first).
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../.." && pwd)
source "$REPO/env/modules.sh"          # also sets SYSTYPE=Generic-gcc

SRC=$NBODY_RUNS/builds/src/gadget4
DIR=$NBODY_RUNS/builds/gadget4_mw_gas
if [ ! -d "$SRC/src" ]; then
    echo "No Gadget4 source in $SRC: run 'bash env/fetch_sources.sh' on the login node first" >&2
    exit 1
fi

mkdir -p "$DIR"
cp "$HERE/Config.sh" "$DIR/Config.sh"
cd "$SRC"
make -j "${SLURM_CPUS_PER_TASK:-8}" DIR="$DIR" PYTHON=python3
echo "Built: $DIR/Gadget4"
ldd "$DIR/Gadget4" | grep -E 'hdf5|gsl|mpi'
