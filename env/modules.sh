# Module environment for the geryon3 N-body tutorials.
# Usage:  source env/modules.sh
# Used for building Gadget4/Agama and inside every Slurm script.

module purge
module load openmpi/4.1.5/gnu        # mpicc/mpicxx/mpirun (GCC 8.5.0 underneath)
module load gsl-1.16                 # GSL headers+libs (no system gsl-devel on geryon3)
module load hdf5/1.14.3/serial/gnu   # HDF5 for Gadget4 snapshot I/O
module load python-3.11.4            # base interpreter for the venv

# Paths used throughout the tutorials (override before sourcing if you like)
export CODES_DIR=${CODES_DIR:-$HOME/codes}
export NBODY_RUNS=${NBODY_RUNS:-$HOME/nbody_runs}
export NBODY_VENV=${NBODY_VENV:-$HOME/environments/nbody-tutorial}

# Gadget4 picks the generic GCC build rules; headers/libs come from CPATH/LIBRARY_PATH set above
export SYSTYPE=Generic-gcc

# InfiniBand (mlx5) is driven by UCX; the legacy openib BTL only prints init errors
export OMPI_MCA_btl=^openib

if [ -f "$NBODY_VENV/bin/activate" ]; then
    source "$NBODY_VENV/bin/activate"
fi
