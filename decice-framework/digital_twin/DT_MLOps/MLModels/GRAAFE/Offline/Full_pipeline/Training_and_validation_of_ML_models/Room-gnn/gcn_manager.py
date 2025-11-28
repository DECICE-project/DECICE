import numpy as np
import os
import pandas as pd
import torch
import pickle
from tqdm import tqdm
import time
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)

from room import Marconi100Room
from utils import *

class GCNDataManager:
  """
  Class that loads and manages data to feed a GCN model.
  """
  def __init__(self):
    self.raw_data_path = RAW_DATA_PATH
    self.samples_AP_path = BASE_AP_DATA_PATH
    self.M100 = Marconi100Room(None)

  def load_AP_samples(self, fw:int, idx:int):
    with open(os.path.join(BASE_AP_DATA_PATH,"{}/{}.pickle".format(fw,idx)), 'rb') as f:
      graph_item = pickle.load(f)
    return graph_item

  def neighbor_average_fill(self,df: pd.DataFrame) -> pd.DataFrame:
    vals = df.to_numpy()  # for efficiency
    # Loop over rows and columns of X matrix
    for node in range(vals.shape[0]):
      for col in range(vals.shape[1]):
        # If value is NaN, fill it
        if np.isnan(vals[node, col]):
          # get neighboring nodes
          neigh_dist = self.M100.get_neighbors_and_distances(node)
          # compute weighted average excluding NaNs
          values = []
          weights = []
          for n, d in neigh_dist.items():
            val_n = vals[n, col]
            if np.isnan(val_n):
              print("Skip")
            else:
              values.append(val_n)
              weights.append(1 / d)
              print(f"Neighbor {n} has value {val_n} and "
                                        f"weight {round(1 / d, 3)}")

          try:
            # set value in data
            df.iloc[node, col] = np.average(values, weights=weights)
            print(f"Filled with {df.iloc[node, col]}")
          except:
              print("error at node:{} col:{}".format(node,col))
              raise Exception("error at node:{} col:{}".format(node,col))
    print("Filling complete")
    return df

if __name__ == '__main__':
  manager_agg = GCNDataManager()

  node = 157
  a = pd.read_parquet("../data/nodes_aggr/{}.parquet".format(node))
  t = time.perf_counter()
  print(a.isna().sum().sum())
  print(a.shape)
  #a = a.drop(columns=["timestamp"])
  b = manager_agg.neighbor_average_fill(a,node)
  t22 = time.perf_counter()
  print(b.isna().sum().sum())
  print(b.shape)
  print(t22-t)