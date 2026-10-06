#!/bin/bash
# Clone Agama, InkWell, pynbody and Gadget4 from $CODES_DIR into $NBODY_RUNS/builds/src
# at the commits pinned in env/versions.env.  Run on the LOGIN node: git is not
# installed on the geryon3 compute nodes.  $CODES_DIR itself is never modified.
set -euo pipefail
REPO=$(cd "$(dirname "$0")/.." && pwd)
source "$REPO/env/modules.sh"
source "$REPO/env/versions.env"
SRC=$NBODY_RUNS/builds/src
mkdir -p "$SRC"

clone_at() {   # clone_at <name> <commit>
    local name=$1 commit=$2
    if [ -d "$SRC/$name" ]; then
        git -C "$SRC/$name" fetch --quiet origin   # pick up commits pulled into $CODES_DIR since the clone
    else
        git clone --quiet "$CODES_DIR/$name" "$SRC/$name"
    fi
    git -C "$SRC/$name" checkout --quiet --force "$commit"
    echo "$name @ $(git -C "$SRC/$name" rev-parse --short HEAD)"
}
clone_at Agama   "$AGAMA_COMMIT"
clone_at InkWell "$INKWELL_COMMIT"
clone_at pynbody "$PYNBODY_COMMIT"
clone_at gadget4 "$GADGET4_COMMIT"

# python-3.11.4 on geryon3 ships only a static libpython; Agama's setup.py needs a fallback
git -C "$SRC/Agama" apply --check "$REPO/env/patches/agama_static_libpython.patch" 2>/dev/null \
    && git -C "$SRC/Agama" apply "$REPO/env/patches/agama_static_libpython.patch" \
    && echo "Agama: applied agama_static_libpython.patch" \
    || echo "Agama: patch already applied"
