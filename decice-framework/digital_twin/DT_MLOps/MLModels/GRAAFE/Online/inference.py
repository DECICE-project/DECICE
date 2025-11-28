
import torch
from torch_geometric.nn import GCNConv


class anomaly_anticipation(torch.nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        #encoder
        self.conv1 = GCNConv(in_channels, 300)
        self.conv2 = GCNConv(300, 100)
        self.conv3 = GCNConv(100, out_channels)
        
        #dense layer
        self.fc1 = torch.nn.Linear(out_channels,16)
        self.fc2 = torch.nn.Linear(16,1)
        
    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index).relu()
        x = self.conv2(x, edge_index).relu()
        x = self.conv3(x, edge_index).relu()                
        x = self.fc1(x)
        x = self.fc2(x)
        
        return x


def inference(model,graph):
    out = model(graph.x,graph.edge_index)

    prediction = torch.sigmoid(out)

    return prediction