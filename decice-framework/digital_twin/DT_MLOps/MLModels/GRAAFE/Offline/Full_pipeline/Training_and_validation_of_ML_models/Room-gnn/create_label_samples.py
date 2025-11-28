import numpy as np
import pandas as pd
import os
import pickle
from datetime import datetime
from tqdm import tqdm
from utils import *

save_path = LABELS_PATH

if(os.path.exists(save_path)):
    print('save path exits!')
else:
    os.makedirs(save_path)
    for FW in [4,6,12,24,32,64,96,192,288]:
        os.makedirs(os.path.join(save_path,'{}'.format(FW)))
    print("The new directory is created!")

def get_node(x):
    tmp = x.split('/')
    tmp = tmp[-1]
    tmp = tmp.split('.')
    return int(tmp[0])

def format_timestamp(ts):
    tmp = str(ts)
    tmp = datetime.strptime(tmp[:-6], "%Y-%m-%d %H:%M:%S")
    tmp = tmp.strftime("%Y-%m-%d_%H:%M:%S")
    return tmp

for fw in [4,6,12,24,32,64,96,192,288]:
    dir_path = '{}'.format(fw)
    files = [os.path.join(dirpath,f) for (dirpath, dirnames, filenames) in os.walk(dir_path) for f in filenames]
    files = sorted(files, key = lambda x:get_node(x))

    df = pd.read_parquet(files[0])
    df = df[['timestamp', 'new_label']]
    for i in tqdm(range(1,len(files))):
        node = pd.read_parquet(files[i])
        node = node[['timestamp', 'new_label']]
        df = pd.concat([df,node])

    grouped = df.groupby('timestamp')
    grouped_dfs = [group for _, group in grouped]

    for df in grouped_dfs:
        ts = df.iloc[0,0]
        ts = format_timestamp(ts)

        labels = df['new_label'].to_numpy()

        file_name = os.path.join(save_path,"{}/{}.pickle".format(fw,ts))
        with open(file_name,'wb') as f:
            pickle.dump(labels,f)