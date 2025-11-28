import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn import preprocessing
from tqdm import tqdm
import pickle

fw = [4,6,12,24,32,64,96,192,288]

prob_fw = []
l_fw = []

files = ['data/12_4.pickle',
         'data/12_6.pickle',
         'data/12_12.pickle',
         'data/12_24.pickle',
         'data/12_32.pickle',
         'data/12_64.pickle',
         'data/12_96.pickle',
         'data/12_192.pickle',
         'data/12_288.pickle']
print(files)


for i in range(len(files)):
    print(files[i])
    f = open(files[i], 'rb')
    df = pickle.load(f)
    f.close()
    
    node_true = []
    idx = 0
    for j in range(df.shape[0]):
        if(j == idx):
            node_true.append(df['true_class'][j])
            idx = idx + 18
            
    node_true = node_true[:13507]
  
    print(df.shape)
    
    node_prob = []
    idx = 0
    for j in range(df.shape[0]):
        if(j == idx):
            node_prob.append(df['prob'][j])
            idx = idx + 18
            
    node_prob = node_prob[:13507]
    
    l_fw.append(node_true)
    prob_fw.append(node_prob)


data = pd.read_parquet("240.parquet")
data = data.dropna()
data.reset_index(drop=True, inplace = True)
data['value'] = data['value'].replace(2,1)
data['value'] = data['value'].replace(3,1)

print(data.shape)

value = data['value'].to_numpy()
value = value[int(data.shape[0]*0.8):]

true = value[:13507]
print(true)

ts = data['timestamp'].to_numpy()
ts = ts[int(data.shape[0]*0.8):]
ts = ts[:13507]

print(len(true),len(ts))

prob_4 = prob_fw[0]
prob_6 = prob_fw[1]
prob_12 = prob_fw[2]
prob_24 = prob_fw[3]
prob_32 = prob_fw[4]
prob_64 = prob_fw[5]
prob_96 = prob_fw[6]
prob_192 = prob_fw[7]
prob_288 = prob_fw[8]

df_heat = pd.DataFrame({'raw a.label': true,
'TW 4': prob_4,
'TW 6': prob_6,
'TW 12': prob_12,
'TW 24': prob_24,
'TW 32': prob_32,
'TW 64': prob_64,
'TW 96': prob_96,
'TW 192': prob_192,
'TW 288': prob_288,
})

print(df_heat)

scaler = preprocessing.MinMaxScaler()
names = df_heat.columns
d = scaler.fit_transform(df_heat)
df_heat = pd.DataFrame(d, columns=names)

df_heat['Timestamp'] = ts

a = df_heat['Timestamp'].dt.date
a = []
for i in tqdm(range(df_heat.shape[0])):
    if((i>=6630) & (i<=6740)):
        t = str(df_heat['Timestamp'].dt.strftime('%H:%M')[i])
        a.append(t)
    else:
        a.append("0")
a[6738] = '18:00'

df_heat['Time (HH:MM)'] = a 
df_heat = df_heat.drop(['Timestamp'],axis = 1)
df_heat = df_heat.set_index('Time (HH:MM)')

print(df_heat)

plt.figure(figsize=(5,5))
df = df_heat.iloc[:, 0:2]
df = df[6734:6739].astype(float)
svm = sns.heatmap(df.T,cbar_kws={'label': 'Failure probability'})
figure = svm.get_figure()    
figure.savefig('5.pdf', dpi=400,bbox_inches='tight')

plt.figure(figsize=(5,5))
df = df_heat.iloc[:, 0:3]
df = df[6729:6739].astype(float)
svm = sns.heatmap(df.T,cbar_kws={'label': 'Failure probability'})
figure = svm.get_figure()    
figure.savefig('10.pdf', dpi=400,bbox_inches='tight')

plt.figure(figsize=(10,5))
df = df_heat.iloc[:, 0:4]
df = df[6719:6739].astype(float)
svm = sns.heatmap(df.T,cbar_kws={'label': 'Failure probability'})
figure = svm.get_figure()    
figure.savefig('20.pdf', dpi=400,bbox_inches='tight')

plt.figure(figsize=(10,5))
df = df_heat[6709:6739].astype(float)
svm = sns.heatmap(df.T,cbar_kws={'label': 'Failure probability'})
figure = svm.get_figure()    
figure.savefig('30.pdf', dpi=400,bbox_inches='tight')

plt.figure(figsize=(10,5))
df = df_heat[6689:6739].astype(float)
svm = sns.heatmap(df.T,cbar_kws={'label': 'Failure probability'})
figure = svm.get_figure()    
figure.savefig('50.pdf', dpi=400,bbox_inches='tight')

plt.figure(figsize=(10,5))
df = df_heat[6639:6739].astype(float)
svm = sns.heatmap(df.T,cbar_kws={'label': 'Failure probability'})
figure = svm.get_figure()    
figure.savefig('100.pdf', dpi=400,bbox_inches='tight')
