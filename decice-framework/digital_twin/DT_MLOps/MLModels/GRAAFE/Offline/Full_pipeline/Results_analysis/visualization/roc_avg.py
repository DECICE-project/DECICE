import numpy as np
import os
import pickle
import pandas as pd
from pandas import Series
import numpy as np
from sklearn.metrics import roc_auc_score

roc_list = []
FW = [4,6,12,24,32,64,96,192,288]
def remove_rows_with_preceding_one(df):
    #Shift the true_class column by one row
    shifted = df['true_class'].shift()
    #Select the rows where the shifted column does not have a value of 1
    filtered = df[shifted != 1]
    return filtered

for fw in FW:
    dir_path = '{}/'.format(fw)
    files = []
    # loop over the contents of the directory
    for filename in os.listdir(dir_path):
        # construct the full path of the file
        file_path = os.path.join(dir_path, filename)
        # check if the file is a regular file (not a directory)
        if os.path.isfile(file_path):
            files.append(file_path)
    print(files[:2])

    data =[]
    for i in range(len(files)):
        f = open(files[i], 'rb')
        obj = pickle.load(f)
        f.close()
        data.append(obj)
        #print(obj)

    AUCs = []
    for df in data:
        df = remove_rows_with_preceding_one(df)
        auc = roc_auc_score(df.true_class, df.prob)
        #print(auc)
        AUCs.append(auc)

    avg = sum(AUCs)/len(AUCs)
    print(avg)
    roc_list.append(avg)

print(pd.DataFrame({'fw': FW,'avg roc': roc_list}))