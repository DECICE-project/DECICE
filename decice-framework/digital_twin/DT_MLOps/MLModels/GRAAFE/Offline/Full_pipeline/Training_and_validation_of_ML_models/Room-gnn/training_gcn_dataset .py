import numpy as np
import os
import torch
from torch.utils.data import Dataset
from torch_geometric.data import Data
from torch_geometric.loader import DataLoader
from torch_geometric.nn import GCNConv
import time
import torch.nn as nn
from tqdm import tqdm

from utils import *
import pickle
import sys

inpts = sys.argv
fw = int(inpts[1])
experiment = str(inpts[2])

class AP_train_validaion_Dataset(Dataset):
  """PyTorch dataset class for M100 training data.

  This simple class is needed to perform batch training of the GCN model.
  Like all `Dataset` classes, it can be given to a `DataLoader` object which in
  turn can be looped on in order to get training batches.
  """
  def __init__(self, task:str):
    self.task = task
    if(self.task == 'train'):
        self.data_path = os.path.join(BASE_AP_DATA_PATH,"{}/train".format(fw))
    elif(self.task == 'test'):
        self.data_path = os.path.join(BASE_AP_DATA_PATH,"{}/test".format(fw))
    else:
        raise Exception("Enter Valid Task!")
    
    self.files = get_files_path(self.data_path)

  def __len__(self) -> int:
    return len(self.files)

  def train(self,loader: DataLoader):
    model.train()
    for graphs in loader:
        graphs = graphs.to(device)
        optimizer.zero_grad()
        out = model(graphs.x,graphs.edge_index, graphs.edge_attr)
        loss = criterion(out, graphs.y)
        loss.backward()
        optimizer.step()
    return float(loss)

  def evaluate_model(self,loader: DataLoader) -> pd.DataFrame:
    pred_list = []
    y_true = []
    for graphs in loader:
      graphs = graphs.to(device)
      out = model(graphs.x,graphs.edge_index,graphs.edge_attr)
      pred = torch.sigmoid(out)
      pred_list.append(pred)
      y_true.append(graphs.y.detach().cpu().numpy())

    for i in range(len(pred_list)):
      pred_list[i] = pred_list[i].detach().cpu().numpy()

    y_true = [item for sublist in y_true for item in sublist]
    y_true = [int(item) for item in y_true]
    pred_list = [item for sublist in pred_list for item in sublist]
    pred_list = [float(item) for item in pred_list]
    print(len(y_true),len(pred_list))

    error_df = pd.DataFrame({'prob': pred_list,
                              'true_class': y_true})
    print(error_df)
    return error_df

  def __getitem__(self, idx: int) -> Data:
    file_name = self.files[idx]

    with open(file_name,'rb') as f:
      graph = pickle.load(f)

    #normalization
    graph.x = z_score_normalization(graph.x)

    # setting the edge weight to float32
    graph.edge_attr = graph.edge_attr.to(torch.float32)

    return graph

class GCN_anomaly_anticipation(torch.nn.Module):
  def __init__(self, in_channels, out_channels):
      super().__init__()
      #encoder
      self.conv1 = GCNConv(in_channels, 300)
      self.conv2 = GCNConv(300, 100)
      self.conv3 = GCNConv(100, out_channels)

      #dense layer
      self.fc1 = torch.nn.Linear(out_channels,16)
      self.fc2 = torch.nn.Linear(16,1)

  def forward(self, x, edge_index, edge_attr):
      x = self.conv1(x, edge_index, edge_attr).relu()
      x = self.conv2(x, edge_index, edge_attr).relu()
      x = self.conv3(x, edge_index, edge_attr).relu()
      x = self.fc1(x)
      x = self.fc2(x)
      return x

if __name__ == '__main__':
  num_epochs = 5
  batch_size = 128

  print("Training Setup - FW:{}, Experiment:{}".format(fw,experiment))
  print("               - Batch:{}, Epochs:{}".format(batch_size,num_epochs))
  print("\n***********************************************\n")
  np.random.seed(42)
  torch.manual_seed(43)

  dataset = AP_train_validaion_Dataset('train')
  training_loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

  print("Train sample graph metadeta:")
  sample = dataset.__getitem__(0)
  print(sample)
  print("Nodes: ",sample.num_nodes)
  print("Features: ",sample.num_node_features)
  print("Edges: ",sample.num_edges)

  device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
  # Define the CUDA device

  in_channels, out_channels = sample.num_node_features, 16

  model = GCN_anomaly_anticipation(in_channels, out_channels)
  print("***********************************************")
  print("Model")
  print("***********************************************")
  print(model)

  model = model.to(device)
  model.train()

  optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
  criterion = torch.nn.BCEWithLogitsLoss()

  print("***********************************************")
  print("Training")
  print("***********************************************")
  # Early stopping
  last_loss = 100
  patience = 2
  trigger_times = 0
  similar_loss_count = 0
  tolerance = 1e-4
  EARLY_STOPPING = False

  training_start = time.perf_counter()
  for epoch in range(num_epochs):
    loss = dataset.train(training_loader)
    print(f'Epoch: {epoch+1:02d}, Loss: {loss:.4f}')
    if loss > last_loss:
        trigger_times += 1
        print('Trigger Times:', trigger_times)
        if trigger_times >= patience:
            EARLY_STOPPING = True
            print('Early stopping!')
    elif abs(loss - last_loss) < tolerance:
        # Check if the difference in loss is within a tolerance threshold
        similar_loss_count = similar_loss_count + 1
        print(f'Loss change is within tolerance for {similar_loss_count} epochs')
        if similar_loss_count >= patience:
            EARLY_STOPPING = True
            print('Early stopping due to similar losses!')
    else:
        print('trigger times: 0')
        trigger_times = 0
    if(EARLY_STOPPING == True):
        break
    last_loss = loss
  training_end = time.perf_counter()

  print("Training time : {}".format(training_end-training_start))

  print("***********************************************")
  print("Evaluation")
  print("***********************************************")

  model.eval()
  test_dataset = AP_train_validaion_Dataset('test')
  test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

  eval_start = time.perf_counter()
  error_df = test_dataset.evaluate_model(test_loader)
  eval_end = time.perf_counter()

  print("Evaluation time : {}".format(eval_end-eval_start))

  if not os.path.exists(RESULTS_PATH):
    # Create a new directory because it does not exist
    os.makedirs(RESULTS_PATH)

    for FW in [4,6,12,24,32,64,96,192,288]:
        os.makedirs(os.path.join(RESULTS_PATH,'{}/model'.format(FW)))
        os.makedirs(os.path.join(RESULTS_PATH,'{}/error_df'.format(FW)))
    print("The new directory is created!")

  """
  Saving model and the table containing the predictions and true value.
  The table will then be used to calculate ROC-AUC
  """

  model_path = os.path.join(RESULTS_PATH,"{}/model/{}.pth".format(fw,experiment))
  error_df_path = os.path.join(RESULTS_PATH,'{}/error_df/{}.pickle'.format(fw,experiment))

  with open(error_df_path, 'wb') as f:
    pickle.dump(error_df, f)

  #saving model
  torch.save(model.state_dict(), model_path)

  print("DONE!")