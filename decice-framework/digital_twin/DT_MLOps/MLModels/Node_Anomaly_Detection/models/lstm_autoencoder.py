import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from sklearn.preprocessing import MinMaxScaler


# Define the LSTM model
class LSTMModel(nn.Module):
    def __init__(self, seq_length, n_features, hidden_size=128, dropout_rate=0.2):
        super(LSTMModel, self).__init__()

        self.encoder_lstm = nn.LSTM(input_size=n_features, hidden_size=hidden_size, batch_first=True)

        self.encoder_dropout = nn.Dropout(dropout_rate)

        self.repeat_vector = nn.Linear(hidden_size, seq_length * hidden_size)

        self.decoder_lstm = nn.LSTM(input_size=hidden_size, hidden_size=hidden_size, batch_first=True)

        self.decoder_dropout = nn.Dropout(dropout_rate)

        self.output_layer = nn.Linear(hidden_size, 1)

    def forward(self, x):
        # Encoder
        _, (hidden, _) = self.encoder_lstm(x)
        hidden = hidden[-1]

        hidden = self.encoder_dropout(hidden)

        repeated = self.repeat_vector(hidden).view(x.size(0), -1, hidden.size(-1))

        # Decoder
        decoded, _ = self.decoder_lstm(repeated)

        decoded = self.decoder_dropout(decoded)

        out = self.output_layer(decoded)

        out = torch.sigmoid(out)

        return out


def preprocess_data(df, column_names=None, timesteps=10):
    scalers = {}
    data_scaled = np.empty((len(df), 0))

    for column_name in column_names:
        scaler = MinMaxScaler()
        data = scaler.fit_transform(df[[column_name]])
        data_scaled = np.concatenate((data_scaled, data), axis=1)
        scalers[column_name] = scaler

    def create_sequences(data, seq_length):
        sequences = []
        for i in range(len(data) - seq_length + 1):
            sequences.append(data[i : i + seq_length])
        return np.array(sequences)

    X = create_sequences(data_scaled, timesteps)
    return X, scalers


def train_lstm_detect_anomalies(df, column_names=None, timesteps=10, threshold=0.06, epochs=10):
    X, scalers = preprocess_data(df, column_names, timesteps)
    input_size = X.shape[2]

    # model = LSTMModel(input_size=input_size, hidden_size=128, num_layers=1)
    model = LSTMModel(seq_length=timesteps, n_features=input_size, hidden_size=128, dropout_rate=0.2)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    # Convert to PyTorch tensor
    X_tensor = torch.FloatTensor(X)

    # Create a TensorDataset and DataLoader
    dataset = TensorDataset(X_tensor)
    batch_size = 32  # Define your batch size
    data_loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    # Training the model
    for epoch in range(epochs):
        model.train()
        for batch in data_loader:
            X_batch = batch[0]  # Get the input data from the batch
            optimizer.zero_grad()
            outputs = model(X_batch)
            loss = criterion(outputs[:, -1, :], X_batch[:, -1, :])
            loss.backward()
            optimizer.step()

    # Save the model
    torch.save(model.state_dict(), "LSTMmodel.pth")

    # Evaluation
    model.eval()
    with torch.no_grad():
        X_pred = model(X_tensor).numpy()

    return model


def evaluate_lstm_detect_anomalies(df, log_dir, column_names=None, timesteps=10, threshold=0.06):
    # from torch.utils.tensorboard import SummaryWriter
    from tensorboardX import SummaryWriter
    import os

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        print("here the directory is created.")
    writer = SummaryWriter(log_dir=log_dir)

    # Preprocess data
    X, scalers = preprocess_data(df, column_names, timesteps)
    input_size = X.shape[2]

    # Load trained model
    model = LSTMModel(seq_length=timesteps, n_features=input_size, hidden_size=128, dropout_rate=0.2)
    model.load_state_dict(torch.load("LSTMmodel.pth"))
    model.eval()

    # Prepare TensorBoard
    # writer = SummaryWriter(log_dir=log_dir)

    # Convert to PyTorch tensors
    X_tensor = torch.FloatTensor(X)
    with torch.no_grad():
        X_pred = model(X_tensor).numpy()

    # Calculate reconstruction loss
    mse = np.mean(np.power(X[:, -1, :] - X_pred[:, -1, :], 2), axis=1)

    # Log reconstruction loss and anomalies
    for i, loss in enumerate(mse):
        writer.add_scalar("Reconstruction Loss", loss, i)

    anomalies = mse > threshold
    writer.close()

    # Create a DataFrame to return results
    df_anomalies = pd.DataFrame(index=df.index[timesteps - 1 :])
    df_anomalies["reconstruction_loss"] = mse
    df_anomalies["anomaly"] = anomalies

    return df_anomalies
