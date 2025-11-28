import pandas as pd 
import torch
from torch_geometric.data import Data


def graph_rack(df_raw, rack_name):
    df_agg = agg_df_avg_min_max_std(df_raw)
    df_rack = rack_df(df_agg, rack_name=rack_name)     
    dg_rack = convert_to_graph_data(df_rack)
    return dg_rack



def agg_df_avg_min_max_std(df):
    df_agg = pd.concat(
        [df.groupby(['name', 'node']).mean().pivot_table(index='node', columns='name').add_suffix('_avg'),
         df.groupby(['name', 'node']).std().pivot_table(index='node', columns='name').add_suffix('_std'),
         df.groupby(['name', 'node']).min().pivot_table(index='node', columns='name').add_suffix('_min'),
         df.groupby(['name', 'node']).max().pivot_table(index='node', columns='name').add_suffix('_max')],
        axis=1, ignore_index=False)
    df_agg.columns = df_agg.columns.droplevel(0)
    df_agg['value'] = 0
    return df_agg


def rack_df(df, rack_name):
    df = df.loc[df.index.str.contains(rack_name)]
    df = df.sort_index(axis=0)
    df = df.sort_index(axis=1)
    return df




def convert_to_graph_data(df):
    df.reset_index(drop=True, inplace = True)
    df = df.fillna(0)
    df = df.astype(float)
    df['value'] = df['value'].replace(2,1)
    df['value'] = df['value'].replace(3,1)
    
    n_nodes = df.shape[0]

    edges = []
    k = 0
    for i in range(n_nodes):
        temp = []
        if i == 0:
            temp.append([i,i+1])
        elif i == n_nodes-1:
            temp.append([i,i-1])
        else:
            temp.append([i,i-1])
            temp.append([i,i+1])
        edges = edges + temp

    edges = torch.tensor(edges, dtype=torch.long)

    x = []

    for i in range(n_nodes):
        df_feat = df.loc[i]
        df_feat = df_feat.to_numpy()

        df_feat = torch.tensor(df_feat, dtype=torch.float)
        x.append(df_feat)

    x = torch.stack(x)

    graph = Data(x=x, edge_index=edges.t().contiguous())

    return graph




def sleep_time(rate, loop_taken_time):
    sl_t = rate - loop_taken_time
    if sl_t <= 0:
        sl_t = 0
    return sl_t
