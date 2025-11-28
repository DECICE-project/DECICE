import os

index_ranges = []

for i in range(0,51037,500):
    start_idx = i
    end_idx = i + 500
    index_ranges.append((start_idx,end_idx))

del index_ranges[-1]
index_ranges.append((51000, 51037))

os.mkdir('samples_batch_files')
for fw in [4,6,12,24,32,64,96,192,288]:
    for idx in index_ranges:
        start_idx = idx[0]
        end_idx = idx[1]

        with open ('samples_batch_files/samples_{}_{}.sh'.format(start_idx,end_idx), 'w') as rsh:
                    rsh.write('''\
#!/bin/bash
#SBATCH -A GrM_GRAPHHPC   # project
#SBATCH -p boost_usr_prod    # partition (see Leonardo User guide)
#SBATCH --time 01:10:00       # format: HH:MM:SS
#SBATCH -N 1                         # number of node
#SBATCH --ntasks-per-node=1    # number of tasks-per-node
#SBATCH --gres=gpu:1           # 4 gpus per node out of 4
#SBATCH -e slurm/error/%j.err         # error file (%j needed to have the job id in the file name)
#SBATCH -o slurm/output/%j.out      # output file (%j needed to have the job id in the file name)
cd /leonardo_work/GrM_GRAPHHPC/UseCases/UC4/junaid
python test_new_dataset.py {} {}'''.format(start_idx, end_idx))