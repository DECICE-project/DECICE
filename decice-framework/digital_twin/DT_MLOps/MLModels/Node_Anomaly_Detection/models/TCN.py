import torch
import torch.nn as nn
import numpy as np
import pandas as pd
import torch.optim as optim
from sklearn.metrics import mean_squared_error

# Define ResidualBlock and TCN classes (these remain the same as in your code)

class ResidualBlock(nn.Module):
    def __init__(self, input_channels, output_channels, kernel_size, dilation_rate, dropout_rate):
        super(ResidualBlock, self).__init__()
        self.conv1 = nn.Conv1d(input_channels, output_channels, kernel_size, dilation=dilation_rate, padding=(kernel_size - 1) * dilation_rate // 2)
        self.conv2 = nn.Conv1d(output_channels, output_channels, kernel_size, dilation=dilation_rate, padding=(kernel_size - 1) * dilation_rate // 2)
        self.dropout = nn.Dropout(dropout_rate)
        self.skip_connection = nn.Conv1d(input_channels, output_channels, kernel_size=1) if input_channels != output_channels else None

    def forward(self, x):
        res = x
        out = self.conv1(x)
        out = self.dropout(out)
        out = self.conv2(out)
        out += self.skip_connection(res) if self.skip_connection else res
        out = torch.relu(out)
        return out

class TCN(nn.Module):
    def __init__(self, input_channels, num_blocks, filters, kernel_size, dilation_rates, dropout_rate, sequence_length, output_size):
        super(TCN, self).__init__()
        self.blocks = nn.ModuleList()
        self.blocks.append(ResidualBlock(input_channels, filters, kernel_size, dilation_rates[0], dropout_rate))
        
        for i in range(1, num_blocks):
            self.blocks.append(ResidualBlock(filters, filters, kernel_size, dilation_rates[i], dropout_rate))

        # Output layer to map to output_size
        self.fc = nn.Linear(filters * sequence_length, output_size)

    def forward(self, x):
        for block in self.blocks:
            x = block(x)
        x = x.view(x.size(0), -1)  # Flatten: (batch_size, filters * sequence_length)
        x = self.fc(x)  # Final output: (batch_size, output_size)
        return x

# Utility function to create sequences
def create_sequences(data, sequence_length):
    data = (data - data.mean()) / data.std()
    sequences = []
    for i in range(len(data) - sequence_length):
        sequences.append(data[i:i + sequence_length])
    return np.array(sequences)

# Training function
def train_tcn(df, column_names, time_steps=10, epochs=20, model_save_path='modelTCN.pth'):
    df = df.astype(np.float32)
    if df.isnull().values.any():
        df = df.dropna()

    # Create sequences for training
    train = create_sequences(df.to_numpy(), time_steps)
    train_tensor = torch.tensor(train).permute(0, 2, 1)

    # Model parameters
    input_channels = train_tensor.shape[1]
    output_size = len(column_names)
    model = TCN(input_channels, num_blocks=1, filters=64, kernel_size=3, dilation_rates=[1, 2, 4], dropout_rate=0.2, sequence_length=time_steps, output_size=output_size)
    
    # Training setup
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()
        predictions = model(train_tensor)
        loss = criterion(predictions, train_tensor[:, :, -1])
        loss.backward()
        optimizer.step()
        print(f"Epoch {epoch + 1}/{epochs}, Loss: {loss.item()}")

    # Save the model
    torch.save(model.state_dict(), model_save_path)
    print("Model trained and saved.")

# Testing function
def test_tcn(df, column_names, time_steps=10, model_save_path='modelTCN.pth'):
    df = df.astype(np.float32)
    if df.isnull().values.any():
        df = df.dropna()

    # Create sequences for testing
    test = create_sequences(df.to_numpy(), time_steps)
    test_tensor = torch.tensor(test).permute(0, 2, 1)

    # Load the trained model
    input_channels = test_tensor.shape[1]
    output_size = len(column_names)
    model = TCN(input_channels, num_blocks=1, filters=64, kernel_size=3, dilation_rates=[1, 2, 4], dropout_rate=0.2, sequence_length=time_steps, output_size=output_size)
    model.load_state_dict(torch.load(model_save_path, weights_only=True))
    model.eval()

    # Predict and calculate reconstruction error
    with torch.no_grad():
        predictions = model(test_tensor)
    
    # Calculate reconstruction error
    reconstruction_error = torch.mean(torch.abs(predictions - test_tensor[:, :, -1]), axis=1).numpy()
    
    # Set threshold for anomaly detection
    threshold_value = np.mean(reconstruction_error) + np.std(reconstruction_error)
    anomalies = reconstruction_error > threshold_value
    
    # Output anomaly results
    df_anomalies = pd.DataFrame(index=df.index[time_steps:])
    df_anomalies['reconstruction_error'] = reconstruction_error
    df_anomalies['anomaly'] = anomalies

    return df_anomalies['anomaly']
