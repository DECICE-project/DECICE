import os
import shutil
import time
from utils import *

data_path = BASE_AP_DATA_PATH

def get_ts(x):
    tmp = x.split('/')
    tmp = tmp[-1]
    tmp = tmp.split('.')
    return tmp[0]

for fw in [4,6,12,24,32,64,96,192,288]:
    files = []
    # loop over the contents of the directory
    for filename in os.listdir(os.path.join(data_path,"{}".format(fw))):
        # construct the full path of the file
        file_path = os.path.join(os.path.join(data_path,"{}".format(fw)), filename)
        # check if the file is a regular file (not a directory)
        if os.path.isfile(file_path):
            files.append(file_path)
    print(files[:5])
    print(fw)

    print("Sorted:")
    files = sorted(files, key = lambda x:get_ts(x))
    print(files[:5])

    if not os.path.exists(os.path.join(data_path,"{}/train".format(fw))):
        os.makedirs(os.path.join(data_path,"{}/train".format(fw)))
        os.makedirs(os.path.join(data_path,"{}/val".format(fw)))
        os.makedirs(os.path.join(data_path,"{}/test".format(fw)))

    train_samples = int(len(files)*0.8)
    val_samples = 1000
    test_samples = len(files)-train_samples-val_samples

    print(train_samples,val_samples,test_samples)
    time.sleep(5)
    for i in range(len(files)):
        file = get_ts(files[i])
        if(i<=train_samples):
            source = files[i]
            destination = os.path.join(data_path,"{}/train/{}.pickle".format(fw,file))
            print(source, destination)
            shutil.move(source,destination)
        elif(i<=train_samples+val_samples):
            source = files[i]
            destination = os.path.join(data_path,"{}/val/{}.pickle".format(fw,file))
            print(source, destination)
            shutil.move(source,destination)
        else:
            source = files[i]
            destination = os.path.join(data_path,"{}/test/{}.pickle".format(fw,file))
            print(source, destination)
            shutil.move(source,destination)

