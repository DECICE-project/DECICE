import os
import pandas as pd
import numpy as np
from sklearn import preprocessing
import torch
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

def feature_and_new_label_extract(train_df,test_df):
    train_feat = train_df.drop(columns=['new_label'])
    train_feat = train_feat.to_numpy()
    train_feat = torch.tensor(train_feat, dtype=torch.float)

    test_feat = test_df.drop(columns=['new_label'])
    test_feat = test_feat.to_numpy()
    test_feat = torch.tensor(test_feat, dtype=torch.float)
    
    train_label = train_df[['new_label']]
    train_label = train_label.to_numpy()
    train_label = torch.tensor(train_label, dtype=torch.float)
    
    test_label = test_df[['new_label']]
    test_label = test_label.to_numpy()
    test_label = torch.tensor(test_label, dtype=torch.float)

    return train_feat,test_feat,train_label,test_label

def create_dataset(train_x,test_x,train_y,test_y):
    train_data = []
    for i in range(train_x.shape[0]):
        train_data.append([train_x[i],train_y[i]])
    test_data = []
    for i in range(test_x.shape[0]):
        test_data.append([test_x[i],test_y[i]])
    return train_data,test_data

class baseline_1(torch.nn.Module):
    def __init__(self, in_channels):
        super().__init__()
        #encoder
        self.fc1 = torch.nn.Linear(in_channels, 300)
        self.fc2 = torch.nn.Linear(300, 100)
        self.fc3 = torch.nn.Linear(100, 16)
        
        #output
        self.fc4 = torch.nn.Linear(16,1)

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        x = torch.relu(self.fc3(x))
        x = self.fc4(x)
        return x
    
    
def training():
    model.train()
    for x,y in loader:
        x = x.to(device)
        y = y.to(device)
        optimizer.zero_grad()
        out = model(x)
        loss = criterion(out, y)
        loss.backward()
        optimizer.step()
    return float(loss)


 


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

print(files)

#checking GPU
print(device)
print(torch.cuda.is_available())
print(torch.cuda.device(0))


for i in range(len(files)):
    node = i
    DATA = read_file(files[i])
    DATA.reset_index(drop=True, inplace = True)
    DATA['value'] = DATA['value'].replace(2,1)
    DATA['value'] = DATA['value'].replace(3,1)

    DATA = new_label_creation(DATA)
    

    DATA.reset_index(drop=True, inplace = True)
    DATA = DATA.fillna(0)
    DATA = DATA.drop(columns=['timestamp'])
    DATA = DATA.astype(float)
    
    scaler = preprocessing.MinMaxScaler()
    names = DATA.columns
    d = scaler.fit_transform(DATA)
    DATA = pd.DataFrame(d, columns=names)

    print(DATA.shape)

    print("Before : ")
    print(DATA['value'].value_counts())
    print("After : ")
    print(DATA['new_label'].value_counts())

    train = DATA[:int(DATA.shape[0]*0.8)]
    train.reset_index(drop=True, inplace = True)
    test = DATA[int(DATA.shape[0]*0.8):]
    test.reset_index(drop=True, inplace = True)

    train_feat,test_feat,train_label,test_label = feature_and_new_label_extract(train,test)

    train_data,test_data = create_dataset(train_feat,test_feat,train_label,test_label)

    loader = torch.utils.data.DataLoader(train_data, batch_size=16,shuffle=False)

    in_channels = train_feat.shape[1]

    model = baseline_1(in_channels)
    model = model.to(device)
    print(model)

    optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
    criterion = torch.nn.BCEWithLogitsLoss()
    
    # Early stopping
    last_loss = 100
    patience = 2
    trigger_times = 0
    EARLY_STOPPING = False

    for epoch in range(30):
        loss = training()
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
    
    
    test_loader = torch.utils.data.DataLoader(test_data, batch_size=1,shuffle=False)

    model.eval()

    pred_list = []
    y_true = []
    for x,y in test_loader:
        x = x.to(device)
        out = model(x)
        pred = torch.sigmoid(out)
        pred_list.append(pred)
        y_true.append(y)

    for i in range(len(pred_list)):
        pred_list[i] = pred_list[i].detach().cpu().numpy()

    y_true = [item for sublist in y_true for item in sublist]
    y_true = [int(item) for item in y_true]
    pred_list = [item for sublist in pred_list for item in sublist]
    pred_list = [float(item) for item in pred_list]

    error_df = pd.DataFrame({'prob': pred_list,'true_class': y_true})
    
    
    print(n_rack)
    print(node)

    filename = 'dense_results/{}/{}_{}_{}.pickle'.format(t_n,n_rack,node,t_n)

    with open(filename, 'wb') as f:
        pickle.dump(error_df, f)

