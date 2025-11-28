import os
import pandas as pd
import pickle
import torch
import numpy as np
from datetime import datetime
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report, f1_score

BASE_AP_DATA_PATH = ""          # add here the generated samples path
BASE_DATA_PATH = ""             # add here the base samples path (aggregated data -> nodes as rows and metrics as col)
RAW_DATA_PATH = ""              # add here the raw data path (aggregated data -> timestamps as rows and metrics as col)
RAW_NEW_LABEL_DATA_PATH = ""    # add here the raw new label data path (path where the new labels are constructed)
RESOURCES_PATH = "resources"
RESULTS_PATH = "results"
LABELS_PATH = ""                # add here the path to the label samples that are created from the raw new label data
SAMPLES_SAVE_PATH = ""          # add here the path where you want to save the samples

BATCH_SIZE= 32
NUM_EPOCHS = 20
LEARNING_RATE = 0.001
OPTIMIZER = "Adam"
CRITERION = "BCEwithLogits"

def min_max_scalar(tensor):
  # Calculate min and max values column-wise
  min_values, _ = torch.min(tensor, dim=0)
  max_values, _ = torch.max(tensor, dim=0)

  # Perform min-max scaling
  normalized_tensor = (tensor - min_values) / (max_values - min_values)

  return normalized_tensor

def z_score_normalization(tensor):
  # Normalize input features using z-score normalization
  feature_scaler = StandardScaler()

  # Reshape the entire tensor to (n_samples, n_features)
  reshaped_features = tensor.reshape(-1, tensor.size(1))

  # Apply normalization to the reshaped tensor
  normalized_features = torch.tensor(feature_scaler.fit_transform(reshaped_features),dtype=torch.float32)
  # Reshape the normalized tensor back to its original shape
  tensor.x = normalized_features.reshape(tensor.size())

  return tensor

def get_ts(x):
  tmp = x.split('/')
  tmp = tmp[-1]
  tmp = tmp.split('.')
  return tmp[0]

def get_files_path(dir_path:str) ->list:
  files = [os.path.join(dirpath,f) for (dirpath, dirnames, filenames) in os.walk(dir_path) for f in filenames]
  files = sorted(files, key = lambda x:get_ts(x))
  return files

def convert_na_to_nan(value):
  return np.nan if pd.isna(value) else value

def get_eligible_list() -> list:
  print("Generating Eligible TS list.....")
  file_path = os.path.join(RAW_NEW_LABEL_DATA_PATH,'4/0.parquet')
  node_data = pd.read_parquet(file_path)

  ts_list = node_data['timestamp']
  split_list = []
  for ts in ts_list:
    tmp = str(ts)
    tmp = datetime.strptime(tmp[:-6], "%Y-%m-%d %H:%M:%S")
    tmp = tmp.strftime("%Y-%m-%d_%H:%M:%S")
    split_list.append(tmp)

  files = [os.path.join(dirpath,f) for (dirpath, dirnames, filenames) in os.walk(BASE_DATA_PATH) for f in filenames]
  files = sorted(files, key = lambda x:get_ts(x))

  files_split_list = []
  for file_ts in files:
    ts = get_ts(file_ts)
    tmp = str(ts)
    files_split_list.append(tmp)

  eligible_ts = [value for value in files_split_list if value in split_list]

  print("DONE!")
  with open(os.path.join(RESOURCES_PATH,'eligible_ts.pickle'),'wb') as f:
    pickle.dump(eligible_ts,f)

  return eligible_ts

def node_wise_col_list() ->list:
  print("Generating Node-Wise Columns list.....")
  col_list = []
  for i in range(980):
    df = pd.read_parquet(os.path.join(RAW_DATA_PATH,"{}.parquet".format(i)))
    col_list.append(list(df.columns))

  print("DONE!")
  with open(os.path.join(RESOURCES_PATH,'col_list_node_wise.pickle'),'wb') as f:
    pickle.dump(col_list,f)

  return col_list

def line_graph_edges() -> list:
    edges = []
    for j in range(49):
        for i in range(20):
            temp = []
            node = i+(j*20)
            if i == 0:
                temp.append([node,node+1])
            elif i == 20-1:
                temp.append([node,node-1])
            else:
                temp.append([node,node-1])
                temp.append([node,node+1])
            edges = edges + temp
    edges = torch.tensor(edges, dtype=torch.long)
    edges = edges.t().contiguous()
    return edges

def classification_report(ground_truths,predictions):
  # Define a range of threshold values to explore
  thresholds = np.arange(0.1, 1.0, 0.05)

  best_threshold = 0.0
  best_f1_score = 0.0

  for threshold in thresholds:
    predicted_labels = [1 if prob >= threshold else 0 for prob in predictions]
    f1 = f1_score(ground_truths, predicted_labels)

    if f1 > best_f1_score:
      best_f1_score = f1
      best_threshold = threshold

  print(f"Best Threshold: {best_threshold}")
  print(f"Best F1-Score: {best_f1_score}")


  predictions = [1 if p > best_threshold else 0 for p in predictions]  # Convert to binary predictions
  accuracy = accuracy_score(ground_truths, predictions)
  print(f"Accuracy: {accuracy:.4f}")
  print(classification_report(ground_truths, predictions))

def get_min_samples(root: str) -> int:
  no_of_samples = []

  for fw in [4,6,12,24,32,64,96,192,288]:
    dir_path = os.path.join(root,'{}/'.format(fw))
    files = []
    # loop over the contents of the directory
    for filename in os.listdir(os.path.join(dir_path.format(fw))):
      # construct the full path of the file
      file_path = os.path.join(dir_path, filename)
      # check if the file is a regular file (not a directory)
      if os.path.isfile(file_path):
        files.append(file_path)

    no_of_samples = []

    for file in tqdm(files):
      node_data = pd.read_parquet(file)
      node_data.reset_index(drop=True, inplace = True)
      if(node_data.shape[0] != 0):
        no_of_samples.append(node_data.shape[0])

  get_min = min(no_of_samples)
  print(get_min)
  return get_min

def get_column_names(root: str) -> list[str]:
    files = []
    # loop over the contents of the directory
    for filename in os.listdir(root):
        # construct the full path of the file
        file_path = os.path.join(root, filename)
        # check if the file is a regular file (not a directory)
        if os.path.isfile(file_path):
            files.append(file_path)

    DATA = pd.read_parquet(files[0])

    for i in tqdm(range(1,len(files))):
       data= pd.read_parquet(files[i])
       data.reset_index(drop=True, inplace = True)
       DATA = pd.concat([DATA[:1], data[:1]])

    DATA.reset_index(drop=True, inplace = True)

    return DATA.columns