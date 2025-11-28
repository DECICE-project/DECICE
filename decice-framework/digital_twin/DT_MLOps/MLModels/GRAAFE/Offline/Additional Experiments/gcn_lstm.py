import numpy as np
import os
import torch
from torch.utils.data import Dataset
from torch_geometric.data import Data
from torch_geometric.loader import DataLoader
from torch_geometric.nn import GCNConv
import time

from utils import *
import pickle
import sys
from sklearn.metrics import roc_auc_score

inpts = sys.argv
fw = int(inpts[1])
experiment = str(inpts[2])

class AP_SequenceDataset(Dataset):
  def __init__(self, seq_length:int ,task:str):
    self.task = task
    if(self.task == 'train'):
        self.data_path = os.path.join(BASE_AP_DATA_PATH,"{}/train".format(fw))
    elif(self.task == 'test'):
        self.data_path = os.path.join(BASE_AP_DATA_PATH,"{}/test".format(fw))
    elif(self.task == 'val'):
        self.data_path = os.path.join(BASE_AP_DATA_PATH,"{}/val".format(fw))
    else:
        raise Exception("Enter Valid Task!")

    self.seq_length = seq_length
    self.files = get_files_path(self.data_path)


  def __len__(self) -> int:
    return len(self.files) - self.seq_length - 1

  def train(self,gnn_model,lstm_model,gnn_optim,lstm_optim,train_loader: DataLoader,test_loader: DataLoader):
    gnn_model.train()
    lstm_model.train()
    
    train_loss = 0.0

    for graphsX,graphsY in train_loader:
        graphsX = [tensor.to(device) for tensor in graphsX]
        graphsY = graphsY.to(device)
        gnn_optim.zero_grad()
        lstm_optim.zero_grad()
        outs = []
        for graphs in graphsX:
          gnn_out = gnn_model(graphs.x,graphs.edge_index, graphs.edge_attr)
          outs.append(gnn_out)

          print(gnn_out.size())
          
          lstm_out = lstm_model(gnn_out)
        gnn_loss = criterion(gnn_out, graphsY.x)
        lstm_loss = criterion(lstm_out[-1], graphsY.x)
        gnn_loss.backward()
        lstm_loss.backward()
        gnn_optim.step()
        lstm_optim.step()
        gnn_loss_item = gnn_loss.item()
        lstm_loss_item = lstm_loss.item()
        train_loss += gnn_loss_item+lstm_loss_item
    avg_train_loss = train_loss/len(train_loader)
    print(f"Epoch [{epoch+1}/{NUM_EPOCHS}] Train Loss: {avg_train_loss:.4f}")

    # Validation
    gnn_model.eval()
    lstm_model.eval()

    val_loss = 0.0

    with torch.no_grad():
        for graphsX,graphsY in test_loader:
            graphsX = [tensor.to(device) for tensor in graphsX]
            graphsY = graphsY.to(device)
            for graphs in graphsX:
              gnn_val_output = gnn_model(graphs.x,graphs.edge_index,graphs.edge_attr)
              lstm_val_output = gnn_model(graphs.x)
            gnn_val_loss = criterion(gnn_val_output, graphsY.x)
            lstm_val_loss = criterion(lstm_val_output, graphsY.x)
            
            gnn_val_loss_item = gnn_val_loss.item()
            lstm__val_loss_item = lstm_val_loss.item()
            # Accumulate the batch loss
            val_loss += gnn_val_loss_item + lstm__val_loss_item
    # Calculate the average val loss
    avg_val_loss = val_loss/len(test_loader)
    print(f"Validation Loss: {avg_val_loss:.4f}")

    return float(avg_val_loss)

  def eval_model(self,gnn_model,lstm_model,loader:DataLoader) -> pd.DataFrame:
    gnn_model.eval()
    lstm_model.eval()

    reconstruction = []
    ground_truth = []

    with torch.no_grad():
        for graphsX,_ in loader:
            graphsX = [tensor.to(device) for tensor in graphsX]
            graphsY = graphsY.to(device)
            for graphs in graphsX:
              gnn_raw_out = gnn_model(graphs.x,graphs.edge_index,graphs.edge_attr)
              lstm_out = lstm_model(gnn_raw_out)
            # reconstruction
            reconstruction_loss = criterion(lstm_out,graphsY.x)
            reconstruction.extend(reconstruction_loss.cpu().numpy().flatten())
            ground_truth.extend(graphsX.y.cpu().numpy().flatten())
    return reconstruction,ground_truth

  def __getitem__(self, idx: int) -> Data:
    x = []
    for i in range(self.seq_length):
      file_name = self.files[idx+i]

      with open(file_name,'rb') as f:
        graph = pickle.load(f)

      # setting the edge weight to float32
      graph.edge_attr = graph.edge_attr.to(torch.float32)
      x.append(graph)

    # now preparing label
    file_name = self.files[idx+self.seq_length+1]

    with open(file_name,'rb') as f:
      graph = pickle.load(f)

    # setting the edge weight to float32
    graph.edge_attr = graph.edge_attr.to(torch.float32)
    y = graph
    return x,y

class GNN(torch.nn.Module):
  def __init__(self, in_dim, hidden_dim,dropout_prob):
      super().__init__()
      self.conv1 = GCNConv(in_dim, hidden_dim)
      self.conv2 = GCNConv(hidden_dim,in_dim)

      # Batch Normalization layers
      self.bn1 = torch.nn.BatchNorm1d(hidden_dim)
      self.bn2 = torch.nn.BatchNorm1d(in_dim)

      # Dropout layers
      self.dropout = torch.nn.Dropout(dropout_prob)

  def forward(self, x, edge_index, edge_attr):
      x = self.conv1(x, edge_index, edge_attr)
      x = torch.relu(x)
      x = self.bn1(x)
      x = self.dropout(x)

      x = self.conv2(x, edge_index, edge_attr)
      x = torch.relu(x)
      x = self.bn2(x)
      x = self.dropout(x)

      return x

class LSTM(torch.nn.Module):
    def __init__(self, input_size, hidden_size, output_size, num_layers=1):
        super(LSTM, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        # LSTM layer
        self.lstm = torch.nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)

        # Output layer
        self.fc = torch.nn.Linear(hidden_size, output_size)

    def forward(self, x):
         # Initialize hidden state with zeros
        batch_size = x.size(0)  # Get the batch size from the input x
        h0 = torch.zeros(self.num_layers, batch_size, self.hidden_size).to(x.device)

        # Initialize cell state with zeros
        c0 = torch.zeros(self.num_layers, batch_size, self.hidden_size).to(x.device)
        """
        # Initialize hidden state with zeros
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)

        # Initialize cell state with zeros
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        """
        # Forward propagate LSTM
        out, _ = self.lstm(x, (h0, c0))

        # Decode the hidden state of the last time step
        out = self.fc(out[:, -1, :])
        return out

if __name__ == '__main__':
  print("Training Setup:")
  print("- FW:{}, Experiment:{}".format(fw,experiment))
  print("- Batch:{}, Epochs:{}, Lr:{}".format(BATCH_SIZE,NUM_EPOCHS,LEARNING_RATE))
  print("- Dropout: {}, Hidden_dim: {}".format(DROPOUT,HIDDEN_DIM))
  print("- Optimizer: {}, Loss Function: {}".format(OPTIMIZER,CRITERION))
  print("***********************************************\n")

  BATCH_SIZE = 1
  # Define the CUDA device
  device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

  in_dim, hidden_dim = 417, HIDDEN_DIM

  dropout_prob = DROPOUT

  np.random.seed(42)
  torch.manual_seed(43)

  # Training Dataset
  train_dataset = AP_SequenceDataset(task='train',seq_length=20)
  training_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)

  # Validation Dataset
  val_dataset = AP_SequenceDataset(task='val',seq_length=20)
  val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=True)

  print("Train sample graph metadeta:")
  sample_x,sample_y = train_dataset.__getitem__(0)
  #print(sample_x[0])

  #print(sample_y)

  print("Number of Samples: {}".format(train_dataset.__len__()))
  time.sleep(2)

  GNN_Model = GNN(in_dim, hidden_dim, dropout_prob)
  print("***********************************************")
  print("Model")
  print("***********************************************")
  print(GNN_Model)

  LSTM_Model = LSTM(input_size=in_dim,output_size=in_dim, hidden_size=hidden_dim)
  print(LSTM_Model)

  GNN_Model = GNN_Model.to(device)
  LSTM_Model = LSTM_Model.to(device)

  GNN_Model.train()
  LSTM_Model.train()

  criterion = torch.nn.MSELoss()
  optimizer1 = torch.optim.Adam(GNN_Model.parameters(), lr=LEARNING_RATE)
  optimizer2 = torch.optim.Adam(LSTM_Model.parameters(), lr=LEARNING_RATE)

  print("***********************************************")
  print("Training")
  print("***********************************************")

  training_start = time.perf_counter()
  for epoch in range(NUM_EPOCHS):
    loss = train_dataset.train(gnn_model=GNN_Model,lstm_model=LSTM_Model,gnn_optim=optimizer1,
                                   lstm_optim=optimizer2,train_loader=training_loader,test_loader=val_loader)
  training_end = time.perf_counter()

  print("Training time : {}".format(training_end-training_start))

  print("***********************************************")
  print("Evaluation")
  print("***********************************************")

  GNN_Model.eval()
  LSTM_Model.eval()

  # Test Dataset
  test_dataset = AP_SequenceDataset(task='test',seq_length=20)
  test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=True)
  print("Number of Samples: {}".format(test_dataset.__len__()))

  eval_start = time.perf_counter()
  reconstruction,ground_truths = test_dataset.eval_model(gnn_model=GNN_Model,lstm_model=LSTM_Model,
                                                      loader=test_loader)
  eval_end = time.perf_counter()

  error_df = pd.DataFrame({'prob': reconstruction,'true_class': ground_truths})
  print(error_df)

  print("Evaluation time : {}".format(eval_end-eval_start))

  # Calculate ROC-AUC score
  roc_auc = roc_auc_score(ground_truths, reconstruction)
  print(f"ROC-AUC Score: {roc_auc:.4f}")

  print("DONE!")
