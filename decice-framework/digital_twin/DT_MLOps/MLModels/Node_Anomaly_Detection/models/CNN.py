import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import pandas as pd

def create_sequences(data, sequence_length):
    # Normalize the data
    normalized_data = data.copy()  # Create a copy to avoid modifying the original data
    
    for column in normalized_data.columns:
        mean = normalized_data[column].mean()
        std = normalized_data[column].std()

        # Check if the standard deviation is zero to avoid NaN
        if std == 0:
            normalized_data[column] = normalized_data[column] - mean  # Center the data
        else:
            normalized_data[column] = (normalized_data[column] - mean) / std  # Standard normalization

    sequences = []
    for i in range(len(normalized_data) - sequence_length):
        sequences.append(normalized_data.iloc[i:i + sequence_length].values)  # Use .iloc to get the values as a NumPy array
    return np.array(sequences)


class CNNAnomalyModel(nn.Module):
    def __init__(self, time_steps, num_features):
        super(CNNAnomalyModel, self).__init__()
        
        # Define layers
        self.conv1 = nn.Conv1d(in_channels=num_features, out_channels=64, kernel_size=3)
        self.pool = nn.MaxPool1d(kernel_size=2)
        self.flatten = nn.Flatten()
        self.fc1 = nn.Linear(64 * ((time_steps - 2) // 2), 50)  # Adjust for pooling
        self.fc2 = nn.Linear(50, num_features)
        
    def forward(self, x):
        x = self.conv1(x)  # Shape: (batch_size, 64, (time_steps - 2))
        x = self.pool(x)   # Shape: (batch_size, 64, ((time_steps - 2) // 2))
        x = self.flatten(x)
        x = self.fc1(x)
        x = self.fc2(x)
        return x

def train_cnn_model(df, column_names, time_steps=10, epochs=10, lr=0.001):
    # if 'datetime' not in df.columns:
    #     raise ValueError("The 'datetime' column is missing from the DataFrame.")

    # # Preprocess data
    # df['datetime'] = pd.to_datetime(df['datetime'])
    # df.set_index(df['datetime'], inplace=True)
    # df = df.drop('datetime', axis=1)
    df = df.astype(np.float32)

    if df.isnull().values.any():
        df = df.dropna()

    train_data = create_sequences(df, time_steps)
    model = CNNAnomalyModel(time_steps, len(column_names))
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    # Convert train_data to PyTorch tensor (batch_size, num_features, time_steps)
    train_data = torch.tensor(train_data, dtype=torch.float32)

    # Reshape to (batch_size, num_features, time_steps)
    train_data = train_data.permute(0, 2, 1)  # Change shape to (batch_size, num_features, time_steps)

    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()
        outputs = model(train_data)  # Outputs shape: (batch_size, num_features)
      
        # Last timestep target for reconstruction
        loss = criterion(outputs, train_data[:, :, -1])  # Compare with last time step
        loss.backward()
        optimizer.step()
        print(f'Epoch [{epoch + 1}/{epochs}], Loss: {loss.item()}')

    # Save the model
    torch.save(model.state_dict(), 'cnn_model.pth')
    return model



def CNN_Anomaly_detect(df, column_names, time_steps=10, threshold_multiplier=2):

    df = df.astype(np.float32)

    if df.isnull().values.any():
        df = df.dropna()

    test_data = create_sequences(df, time_steps)
    model = CNNAnomalyModel(time_steps, len(column_names))
    model.load_state_dict(torch.load('cnn_model.pth', weights_only=True))
    model.eval()

    # Convert test_data to PyTorch tensor (batch_size, num_features, time_steps)
    test_data = torch.tensor(test_data, dtype=torch.float32)

    # Reshape to (batch_size, num_features, time_steps)
    test_data = test_data.permute(0, 2, 1)  # Change shape to (batch_size, num_features, time_steps)

    # Make predictions
    with torch.no_grad():
        predictions = model(test_data)

    # Calculate reconstruction error (Mean Absolute Error)
    reconstruction_error = torch.mean(torch.abs(predictions - test_data[:, :, -1]), axis=1).numpy()

    # Set threshold for anomaly detection
    threshold = np.mean(reconstruction_error) + threshold_multiplier * np.std(reconstruction_error)
    anomalies = reconstruction_error > threshold

    df_anomalies = pd.DataFrame(index=df.index[time_steps:])
    df_anomalies['reconstruction_error'] = reconstruction_error
    df_anomalies['anomaly'] = anomalies
    return df_anomalies['anomaly']
