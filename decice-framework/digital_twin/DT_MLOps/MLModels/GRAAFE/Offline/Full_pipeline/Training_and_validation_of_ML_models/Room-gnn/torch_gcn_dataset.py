import numpy as np
import pandas as pd
import os
import torch
from torch.utils.data import Dataset
from torch_geometric.data import Data
from torch_geometric.loader import DataLoader
import time

from gcn_manager import GCNDataManager
from utils import *
from room import Marconi100Room
import sys
import pickle

import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)

inpts = sys.argv
start_idx = int(inpts[1])
end_idx = int(inpts[2])

class AnomalyPredictionGraphDataset(Dataset):
    def __init__(self,manager: GCNDataManager):
        self.data_path = BASE_DATA_PATH
        self.eligible_ts_file = os.path.join(RESOURCES_PATH,"eligible_ts.pickle")
        self.col_list_nw_file = os.path.join(RESOURCES_PATH,"col_list_node_wise.pickle")
        self.M100 = Marconi100Room(None)
        self.manager = manager

        self.edges_file = os.path.join(RESOURCES_PATH, 'edges.csv')
        self.weights_file = os.path.join(RESOURCES_PATH, 'weights.csv')
        if(os.path.isfile(self.edges_file)):
            print("edges and weights file exits!")
            self.edges = torch.tensor(np.loadtxt(self.edges_file), dtype=torch.long)
            self.weights = torch.tensor(np.loadtxt(self.weights_file), dtype=torch.long)
        else:
            self.edges,self.weights = self.M100.get_edge_tuples_and_weights()
            np.savetxt(self.edges_file, self.edges, fmt='%d')
            np.savetxt(self.weights_file, self.weights, fmt='%.2f')

        if(os.path.isfile(self.eligible_ts_file)):
            print("Eligible_ts file exits!")
            with open(self.eligible_ts_file, 'rb') as f:
                self.eligible_ts = pickle.load(f)
        else:
            self.eligible_ts = get_eligible_list()

        if(os.path.isfile(self.col_list_nw_file)):
            print("Column list node wise file exits!")
            with open(self.col_list_nw_file, 'rb') as f:
                self.col_list_nw = pickle.load(f)
        else:
            self.col_list_nw = node_wise_col_list()

    def __len__(self):
        return len(self.eligible_ts)

    def convert_na_to_nan(self,value):
        return np.nan if pd.isna(value) else value

    def feature_extraction(self,df):
        df_feat = df.to_numpy()
        df_feat = torch.tensor(df_feat, dtype=torch.float)

        return df_feat

    def labels_extraction(self,df):
        df_labels = df[['new_label']]
        df_labels = df_labels.to_numpy()
        df_labels = torch.tensor(df_labels, dtype=torch.float)

        return df_labels

    def __getitem__(self, idx):
        file_ts = self.eligible_ts[idx]
        file_path = os.path.join(BASE_DATA_PATH,"{}.pickle".format(file_ts))

        #read file
        with open(file_path,'rb') as f:
            df = pickle.load(f)

        df = df.applymap(self.convert_na_to_nan)

        for node in range(980):
            added_columns = [col for col in list(df.columns) if col not in self.col_list_nw[node]]
            for col in added_columns:
                df.iloc[node,df.columns.get_loc(col)] = 0.0

        df['state'] = df['state'].replace(2,1)
        df['state'] = df['state'].replace(3,1)

        try:
            df_x = self.manager.neighbor_average_fill(df)
            df_x = df_x.astype(float)
            ts_x = self.feature_extraction(df_x)

            data_list = []
            for fw in [4,6,12,24,32,64,96,192,288]:
                with open(os.path.join(LABELS_PATH,"{}/{}.pickle".format(fw,file_ts)),'rb') as f:
                    y = pickle.load(f)

                df_y = pd.DataFrame({'new_label': y})

                ts_y = self.labels_extraction(df_y)

                data = Data(x=ts_x,y=ts_y, edge_index=self.edges.t().contiguous(), edge_attr = self.weights)
                data_list.append(data)
            return data_list
        except:
            print("The neighbours of atleast one node has all values NaNs. Therefore skipped this idx!")


if __name__ == '__main__':
    manager_agg = GCNDataManager()
    dataset = AnomalyPredictionGraphDataset(manager_agg)
    print("Number of samples:", len(dataset))

    if not os.path.exists(SAMPLES_SAVE_PATH):
        # Create a new directory because it does not exist
        os.makedirs(SAMPLES_SAVE_PATH)
        for FW in [4,6,12,24,32,64,96,192,288]:
            os.makedirs(os.path.join(SAMPLES_SAVE_PATH,'{}'.format(FW)))
        print("The new directory is created!")

    time.sleep(2)

    for idx in range(start_idx,end_idx):
        print("\nIndex: {}".format(idx))
        t1 = time.perf_counter()
        graph_items = dataset.__getitem__(idx)
        if graph_items:
            print(graph_items)
            nan_count = False
            for graph in graph_items:
                x_nan_sum = np.isnan(graph.x).sum()
                y_nan_sum = np.isnan(graph.y).sum()
                if((x_nan_sum>0) or (y_nan_sum>0)):
                    nan_count = True
                    print("Error at Idx: {}".format(idx))
            if(not nan_count):
                fw = [4,6,12,24,32,64,96,192,288]
                for i in range(len(graph_items)):
                    save_file_path = os.path.join(SAMPLES_SAVE_PATH,"{}/{}.pickle".format(fw[i],dataset.eligible_ts[idx]))
                    with open(save_file_path,'wb') as f:
                        pickle.dump(graph_items[i],f)

            t2 = time.perf_counter()
            print("time = {}".format(t2-t1))
        else:
            print("Error at Idx: {}".format(idx))
    print("DONE!")