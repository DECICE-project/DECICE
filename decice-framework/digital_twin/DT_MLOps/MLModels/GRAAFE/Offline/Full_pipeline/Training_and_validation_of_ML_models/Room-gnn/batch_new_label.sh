#!/bin/bash
#SBATCH -A GrM_GRAPHHPC   # project
#SBATCH -p boost_usr_prod    # partition (see Leonardo User guide)
#SBATCH --time 02:00:00       # format: HH:MM:SS
#SBATCH -N 1                         # number of node
#SBATCH --ntasks-per-node=1    # number of tasks-per-node
#SBATCH --gres=gpu:1           # 1 gpus per node out of 4
#SBATCH -e error/%j.err         # error file (%j needed to have the job id in the file name)
#SBATCH -o output/%j.out      # output file (%j needed to have the job id in the file name)
python generate_new_labels.py 4
