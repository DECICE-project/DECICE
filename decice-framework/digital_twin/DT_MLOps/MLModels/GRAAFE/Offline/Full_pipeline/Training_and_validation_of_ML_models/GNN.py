import os
import pandas as pd
import torch
import torchvision
from torchvision.transforms import ToTensor
import numpy as np
from sklearn import preprocessing
from torch_geometric.data import Data
from torch_geometric.loader import DataLoader
from torch_geometric.nn import GCNConv
import sys
import pickle

inpts = sys.argv
rack = int(inpts[1])
t_n = int(inpts[2])


ln = len(str(rack))

anticipation = True

#setting up cuda
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


n_rack = rack
print(rack,t_n)


#helper functions
#---------------------------------------------------------------------------------------------------------------
def read_file(node_dir):
    node_data = pd.read_parquet(node_dir)
    node_data = node_data.dropna()
    return node_data

def new_label_creation(df):
    new_label = []
    for i in range(df.shape[0]):
        anomaly_ahead = False
        for j in range(i+1,i+1+t_n):
            if(j>=df.shape[0]):
                break
            else: 
                if(df['value'][j]==1):
                    anomaly_ahead = True
                    break
        if(anomaly_ahead):
            new_label.append(1)
        else:
            new_label.append(0)    
    df['new_label'] = new_label
    return df

def feature_extraction(df):
    if(anticipation):
        df_feat = df.drop(columns=['new_label'])
    else:
        pass
    
    df_feat = df_feat.to_numpy()

    df_feat = torch.tensor(df_feat, dtype=torch.float)
    
    return df_feat

def labels_extraction(df):
    if(anticipation):
        df_labels = df[['new_label']]
    else:
        pass
    df_labels = df_labels.to_numpy()
    df_labels = torch.tensor(df_labels, dtype=torch.float)
    
    return df_labels

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

    
    
def train():
    model.train()
    for d in loader:
        d = d.to(device)
        optimizer.zero_grad()
        out = model(d.x,d.edge_index)
        loss = criterion(out, d.y)
        loss.backward()
        optimizer.step()
    return float(loss)
#-----------------------------------------------------------------------------------------------------------------------

print("Future prediction(hours) : ",t_n/4)

#reading files for all the nodes in a rack
dir_path = 'data/{}/'.format(rack)

files = []
# loop over the contents of the directory
for filename in os.listdir(dir_path):
    # construct the full path of the file
    file_path = os.path.join(dir_path, filename)
    # check if the file is a regular file (not a directory)
    if os.path.isfile(file_path):
        files.append(file_path)



#checking GPU
print(device)
print(torch.cuda.is_available())
print(torch.cuda.device(0))


len_nodes = []
node_start = 0

DATA = read_file(files[0])
len_nodes.append((node_start,node_start + DATA.shape[0]))
node_start = node_start + DATA.shape[0]

for i in range(1,len(files)):
    data = read_file(files[i])
    len_nodes.append((node_start,node_start + data.shape[0]))
    node_start = node_start + data.shape[0]
    DATA = DATA.append(data)

DATA.reset_index(drop=True, inplace = True)
DATA = DATA.fillna(0)
DATA = DATA.drop(columns=['timestamp'])
DATA = DATA.astype(float)
DATA['value'] = DATA['value'].replace(2,1)
DATA['value'] = DATA['value'].replace(3,1)
scaler = preprocessing.MinMaxScaler()
names = DATA.columns
d = scaler.fit_transform(DATA)
DATA = pd.DataFrame(d, columns=names)

print(DATA.shape)



rack = []
node = []
i = 0
for j in range(len(files)):
    df = DATA[len_nodes[j][0]:len_nodes[j][1]]
    df.reset_index(drop=True, inplace = True)
    df = df.fillna(0)
    node.append(df)   
    rack.append(node)
    node = []
print(len(rack))

node_names = [f.strip('data//.parquet') for f in files]


print(node_names)
print('len',ln)
node_names = [int(f[ln+1:]) for f in node_names]

print(node_names)


sorted_rack = sorted(zip(node_names,rack))

print(files)
print([t[0] for t in sorted_rack])

rack = [t[1] for t in sorted_rack]


#anticipation label pre-processing
if(anticipation):
    for i in range(len(rack)):
        for j in range(len(rack[i])):
            new_label_creation(rack[i][j])
    print("Before : ")
    print(rack[0][0]['value'].value_counts())
    print("After : ")
    print(rack[0][0]['new_label'].value_counts())


rack_split = []

for i in range(len(rack)):
    node_split = []
    for j in range(len(rack[i])):
        data = {
            "train": rack[i][j][:int(rack[i][j].shape[0]*0.8)],
            "test": rack[i][j][int(rack[i][j].shape[0]*0.8):],
        }
        node_split.append(data)

    rack_split.append(node_split)
    
#print(rack_split)


rack_feats_labels = []

for i in range(len(rack_split)):
    node_feats_labels = []
    for j in range(len(rack_split[i])):
        train_feat = feature_extraction(rack_split[i][j]['train'])
        train_label = labels_extraction(rack_split[i][j]['train'])
        
        test_feat = feature_extraction(rack_split[i][j]['test'])
        test_label = labels_extraction(rack_split[i][j]['test'])
        
        data = {
            "train_feat": train_feat,
            "train_labels": train_label,
            "test_feat": test_feat,
            "test_labels": test_label,
        }
        node_feats_labels.append(data)

    rack_feats_labels.append(node_feats_labels)




edges = []
k = 0
for i in range(len(files)):
    temp = []
    if i == 0:
        temp.append([i,i+1])
    elif i == len(files)-1:
        temp.append([i,i-1])
    else:
        temp.append([i,i-1])
        temp.append([i,i+1])
    edges = edges + temp



edges = torch.tensor(edges, dtype=torch.long)
print(edges.t().contiguous())


train_min = len(rack_feats_labels[0][0]['train_feat'])

for i in range(len(rack_feats_labels)):
    for j in range(len(rack_feats_labels[i])):
        temp = len(rack_feats_labels[i][j]['train_feat'])
        #print(temp)
        if(temp<train_min):
            train_min = temp
print(train_min)


test_min = len(rack_feats_labels[0][0]['test_feat'])

for i in range(len(rack_feats_labels)):
    for j in range(len(rack_feats_labels[i])):
        temp = len(rack_feats_labels[i][j]['test_feat'])
        #print(temp)
        if(temp<test_min):
            test_min = temp
print(test_min)




data_list = []

for k in range(train_min):              # k is the timestamp
    g_x = []
    g_y = []
    for i in range(len(rack_feats_labels)):
        for j in range(len(rack_feats_labels[i])):
            g_x.append(rack_feats_labels[i][j]['train_feat'][k])
            g_y.append(rack_feats_labels[i][j]['train_labels'][k])
            
    g_x = torch.stack(g_x)
    g_y = torch.stack(g_y)
            
    data = Data(x=g_x, edge_index=edges.t().contiguous(),y=g_y)
    data_list.append(data)

print(data_list[:10])

test_data_list = []

for k in range(test_min):              # k is the timestamp
    g_x = []
    g_y = []
    for i in range(len(rack_feats_labels)):
        for j in range(len(rack_feats_labels[i])):
            g_x.append(rack_feats_labels[i][j]['test_feat'][k])
            g_y.append(rack_feats_labels[i][j]['test_labels'][k])
            
    g_x = torch.stack(g_x)
    g_y = torch.stack(g_y)
            
    data = Data(x=g_x, edge_index=edges.t().contiguous(),y=g_y)
    test_data_list.append(data)

loader = DataLoader(data_list, batch_size = 16, shuffle = False)
test_loader = DataLoader(test_data_list, shuffle = False)


in_channels, out_channels = data.num_node_features, 16

model = anomaly_anticipation(in_channels, out_channels)
print(model)


model = model.to(device)
optimizer = torch.optim.SGD(model.parameters(), lr=0.01)


criterion = torch.nn.BCEWithLogitsLoss()

# Early stopping
last_loss = 100
patience = 2
trigger_times = 0
EARLY_STOPPING = False


for epoch in range(30):
    loss = train()
    print(f'Epoch: {epoch+1:02d}, Loss: {loss:.4f}')
    if loss > last_loss:
        trigger_times += 1
        print('Trigger Times:', trigger_times)

        if trigger_times >= patience:
            EARLY_STOPPING = True
            print('Early stopping!')
    else:
        print('trigger times: 0')
        trigger_times = 0
    if(EARLY_STOPPING == True):
        break
    last_loss = loss


loss = []
pred_list = []
y_true = []
for d in test_loader:
    d = d.to(device)
    out = model(d.x,d.edge_index)
    pred = torch.sigmoid(out)
    pred_list.append(pred)
    y_true.append(d.y.detach().cpu().numpy())
    

for i in range(len(pred_list)):
    pred_list[i] = pred_list[i].detach().cpu().numpy()
y_true = [item for sublist in y_true for item in sublist]
y_true = [int(item) for item in y_true]
pred_list = [item for sublist in pred_list for item in sublist]
pred_list = [float(item) for item in pred_list]
len(y_true),len(pred_list)

error_df = pd.DataFrame({'prob': pred_list,
                        'true_class': y_true})

print(n_rack)
      
filename = 'results/{}/{}_{}.pickle'.format(t_n,n_rack,t_n)

with open(filename, 'wb') as f:
    pickle.dump(error_df, f)

    
filepath = 'results/model/{}/{}_{}.pth'.format(t_n,n_rack,t_n)

#save model
torch.save(model.state_dict(), filepath)

#load model
#model = anomaly_anticipation(*args, **kwargs)
#model.load_state_dict(torch.load(PATH))
#model.eval()
    
