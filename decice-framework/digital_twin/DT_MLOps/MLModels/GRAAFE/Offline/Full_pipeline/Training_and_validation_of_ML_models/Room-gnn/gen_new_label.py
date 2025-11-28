import os
import pandas as pd
import numpy as np
import sys
from utils import *

inpts = sys.argv
fw = int(inpts[1])

dir_path = RAW_DATA_PATH
new_label_data_path = RAW_NEW_LABEL_DATA_PATH

def new_label_creation(df: pd.DataFrame, t_n: int) -> pd.DataFrame:
  """
  Create new_labels for anomaly anticipation for future window (t_n). The algorithm looks
  for an anomaly in the next t_n timesteps. The current timestep is said to be an anomaly
  if atleast one anomaly ahead in the future window (t_n)
  """
  value = df['state'].to_numpy()
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

def read_file(node_dir):
    """ Read the node's parquet files """
    node_data = pd.read_parquet(node_dir)
    node_data = node_data.dropna(subset = ['state'])
    return node_data


print("Generating new labels")

print("******************************")

new_label_path = os.path.exists(new_label_data_path)

if not new_label_path:
   # Create a new directory because it does not exist
   os.makedirs(new_label_data_path)

   for FW in [4,6,12,24,32,64,96,192,288]:
      os.makedirs(os.path.join(new_label_data_path,'{}'.format(FW)))
   print("The new directory is created!")

#reading files from data directory
files = [os.path.join(dirpath,f) for (dirpath, dirnames, filenames) in os.walk(dir_path) for f in filenames]

print("Total files: ",len(files))

print("\nFW : {}".format(fw))
for node_file in files:
    df = read_file(node_file)
    df['state'] = df['state'].replace(2,1)
    df['state'] = df['state'].replace(3,1)

    df = new_label_creation(df, fw)

    tmp = node_file.split("/")
    tmp = tmp[-1]
    tmp = tmp.split(".")
    node_name = tmp[0]

    df.to_parquet('{}/{}/{}.parquet'.format(new_label_data_path,fw,node_name),
            compression='gzip')
    print('Written at: {}/{}/{}.parquet'.format(new_label_data_path,fw,node_name))