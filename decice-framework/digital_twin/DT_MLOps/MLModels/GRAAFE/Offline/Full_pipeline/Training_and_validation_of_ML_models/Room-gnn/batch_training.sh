#!/bin/bash
#SBATCH -A GrM_GRAPHHPC   # project
#SBATCH -p boost_usr_prod    # partition (see Leonardo User guide)
#SBATCH --time 10:00:00       # format: HH:MM:SS
#SBATCH -N 1                         # number of node
#SBATCH --ntasks-per-node=1     # number of tasks-per-node
#SBATCH --gres=gpu:1           # 1 gpus per node out of 4
#SBATCH -e slurm/error/%j.err         # error file (%j needed to have the job id in the file name)
#SBATCH -o slurm/output/%j.out      # output file (%j needed to have the job id in the file name)
python test_new_model.py 4 lr001_BN_DR50