## GNN artifacts
README
This repository contains slurm batch scripts for GNN and the baselines using which the results mentioned in the paper could be replicated.

Recreate the experiments by following the next steps:
1) in the "Results_analysis" run the Python script "results_setup.py".
2) the folder "Slurm_job_orchestration", and then run the Python script, "generate_batch_scripts.py"

The slurm scripts for GNN are in the folder "GNN_b_scripts". The scripts for "dense baseline" are in "dense_b_scripts" folder, the scripts for "random forest classifier" are in "rf_b_scripts" folder, the scripts for "decision tree" are in "dt_b_scripts" folder, and the scripts for "gradient booster" are in "gb_b_scripts" folder for all the nodes in each rack for evaluation at each future window.

The files of "GNN_scripts_run.txt", "dense_scripts_run.txt", "rf_scripts_run.txt", "dt_scripts_run.txt", "gb_scripts_run.txt", contain the strings that will allocate the slurm batch jobs. 
Before running these scripts, the following libraries must be installed: 
- Pandas
- Numpy
- OS
- Sklearn
- PyTorch
- PyTorch-geometric
- Sys
- Pickle
- Seaborn
- Matplotlib
- tqdm

Since pytorch-geometric is not known by most, the information for its installation according to the used OS can be found here: https://pytorch-geometric.readthedocs.io/en/latest/install/installation.html 

For evaluation, it is a must that the repository is to be cloned in the same directory with the open dataset from the m100. Then unpack the folders of the cloned directory so that all the folders and files are next to the "data" folder of m100.


Then open one ".txt" file, copy the whole batch string, and paste it into the terminal where evaluation is to be carried out; the slurm job will be allocated, and the results will be stored accordingly in the results folders for each model. Do this for all the baselines and GNN.

When all the jobs are completed, the results will be stored in ".pickle" file in their specific folders. The results of GNN will be stored in the "results" folder, the results of Dense baseline will be stored in the "dense_results" folder, the results of the random forest will be stored in the "rf_results" folder, the results of decision-tree will be stored in the "dt_results" folder, The results of gradient-boosting will be stored in the "gb_results" folder.
Each folder contains sub-folders according to each future window, as well as sub-folders. The "results" folder for the GNN has another folder named "models" for the trained models' storage. 

When all the jobs are completed, the average "ROC" for each model and each future window can be calculated. Open the results folder of a model, the "results" folder. This folder contains the GNN results. In the "Results_analysis" folder, run the  "roc_avg.py" file and it will produce and print the average for each future window in the terminal. The same is to be repeated for every baseline.
For the Markov chain, run the file "MC.py", which will give the average ROC for all the datasets for each future window(fw).
Visualization:
For visualization, open the visualization folder and run the "visualization.py" file to generate the figures for different timesteps.

