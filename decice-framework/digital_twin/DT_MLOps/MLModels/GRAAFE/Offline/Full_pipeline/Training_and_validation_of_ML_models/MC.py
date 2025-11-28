import pandas as pd
import numpy as np
from sklearn import preprocessing
import pickle
import os
import glob
import random
from tqdm import tqdm
from sklearn.metrics import roc_auc_score,roc_curve

racks = [0,10,12,14,16,18,2,21,23,25,27,29,30,32,34,36,38,40,42,44,46,48,6,8,
        1,11,13,15,17,19,20,22,24,26,28,3,31,33,35,37,39,4,41,43,45,47,5,7,9]
fw = [4,6,12,24,32,64,96,192,288]

def read_files(node_dir):
    node_data = pd.read_parquet(node_dir)
    node_data = node_data['value'].to_frame()
    node_data = node_data.dropna()
    return node_data
def anticipation_transition_stats(df,z_to_z,z_to_o,o_to_o,o_to_z):
    current = df['new_label'][0]
    for i in range(1,df.shape[0]):
        if(current == 0):
            if(df['new_label'][i]==0):
                z_to_z = z_to_z + 1
            else:
                z_to_o = z_to_o + 1
                current = 1
        else:
            if(df['new_label'][i]==1):
                o_to_o = o_to_o + 1
            else:
                o_to_z = o_to_z + 1
                current = 0
    return z_to_z,z_to_o,o_to_o,o_to_z
def new_label_creation(df,t_n):
    value = df['value'].to_numpy()
    new_label = []
    for i in range(len(value)):
        anomaly_ahead = False
        for j in range(i+1,i+1+t_n):
            if(j>=len(value)):
                break
            else: 
                if(value[j]==1):
                    anomaly_ahead = True
                    break
        if(anomaly_ahead):
            new_label.append(1)
        else:
            new_label.append(0)   
    df['new_label'] = new_label        
    return df

roc_avg = [0,0,0,0,0,0,0,0,0]

for rack in racks:
    print(rack)
    dir_path = 'data/{}/'.format(rack)

    files = []
    # loop over the contents of the directory
    for filename in os.listdir(dir_path):
        # construct the full path of the file
        file_path = os.path.join(dir_path, filename)
        # check if the file is a regular file (not a directory)
        if os.path.isfile(file_path):
            files.append(file_path)
    roc = []
    for t_n in fw:
        print(t_n)
        print("Future prediction(hours) : ",t_n/4)
        
        DATA = read_files(files[0])
        DATA.reset_index(drop=True, inplace = True)
        DATA['value'] = DATA['value'].replace(2,1)
        DATA['value'] = DATA['value'].replace(3,1)
        DATA = new_label_creation(DATA,t_n)
        
        z_to_z = 0
        z_to_o = 0
        o_to_o = 0
        o_to_z = 0
        z_to_z,z_to_o,o_to_o,o_to_z = anticipation_transition_stats(DATA,z_to_z,z_to_o,o_to_o,o_to_z)
        z_to_z,z_to_o,o_to_o,o_to_z
        
        for i in tqdm(range(1,len(files))):
            data = read_files(files[i])
            data['value'] = data['value'].replace(2,1)
            data['value'] = data['value'].replace(3,1)
            data.reset_index(drop=True, inplace = True)
            data = new_label_creation(data,t_n)
            z_to_z,z_to_o,o_to_o,o_to_z = anticipation_transition_stats(data,z_to_z,z_to_o,o_to_o,o_to_z)

            DATA = DATA.append(data)

        DATA.reset_index(drop=True, inplace = True)
        DATA = DATA.fillna(0)
        
        tot = z_to_z+z_to_o+o_to_o+o_to_z
        p_00 = z_to_z/tot
        p_01 = z_to_o/tot
        p_11 = o_to_o/tot
        p_10 = o_to_z/tot

        p_0 = p_00+p_10
        p_1 = p_11+p_01
        #print(p_0,p_1)
        
        y_true = DATA['new_label']
        y_true = y_true.to_numpy()
        
        pred_list = []
        for i in range(DATA.shape[0]):
            pred_list.append(np.random.choice([0,1],p=[p_0,p_1]))
            
        y_true = [int(item) for item in y_true]
        error_df = pd.DataFrame({'prob': pred_list,'true_class': y_true})
        
        
        roc.append(roc_auc_score(error_df['true_class'],error_df['prob']))
    for i in range(len(roc_avg)):
        roc_avg[i] = roc_avg[i]+roc[i]   


for i in range(len(roc_avg)):
    roc_avg[i] = roc_avg[i]/len(roc_avg)    
print(pd.DataFrame({'fw': fw,'roc_auc': roc_avg}))