#!/bin/bash
# Create the tutorial Python environment from scratch.
#   bash env/install_python_env.sh
# Run on the login node.  Builds Agama, InkWell and pynbody from clean clones of the
# checkouts in $CODES_DIR (see env/fetch_sources.sh).  $CODES_DIR is never modified.
set -euo pipefail
REPO=$(cd "$(dirname "$0")/.." && pwd)
source "$REPO/env/modules.sh"
source "$REPO/env/versions.env"
SRC=$NBODY_RUNS/builds/src

# 0. clean clones at the pinned commits (login node: needs git)
bash "$REPO/env/fetch_sources.sh"

# 1. venv on top of the python-3.11.4 module
if [ ! -f "$NBODY_VENV/bin/activate" ]; then
    python3 -m venv "$NBODY_VENV"
fi
source "$NBODY_VENV/bin/activate"
pip install --upgrade pip setuptools wheel
pip install -r "$REPO/env/requirements.txt"

# 2. Agama (compiled extension; needs GSL from the module and Eigen headers).
#    (fetch_sources.sh already applied the static-libpython patch for geryon3.)
(
    cd "$SRC/Agama"
    export CPATH="$EIGEN_DIR:${CPATH:-}"
    pip install --no-build-isolation . --config-settings --build-option=--yes
)

# 3. InkWell (+ HDF5 writer) and pynbody
pip install "$SRC/InkWell[hdf5]"
pip install "$SRC/pynbody"

# 4. Record what was installed
python - <<'PY'
import agama, inkwell, pynbody, numpy, scipy, h5py
print("agama", getattr(agama, "__version__", "?"), "| pynbody", pynbody.__version__,
      "| numpy", numpy.__version__, "| scipy", scipy.__version__, "| h5py", h5py.__version__)
PY
pip freeze > "$NBODY_RUNS/builds/pip-freeze.txt"
echo "Environment ready: source env/modules.sh"
