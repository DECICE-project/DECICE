import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest

def detect_anomalies_isolation_forest(df, column_names=None, contamination=0.01, random_state=42):
    anomalies = pd.DataFrame(index=df.index)
    model = IsolationForest(contamination=contamination, n_estimators=100,random_state=random_state)
    
    for column_name in column_names:
        # Fit the model and predict outliers for each column
        df[column_name + '_anomaly'] = model.fit_predict(df[[column_name]])
        
        # Convert predictions to boolean (anomaly = -1 means outlier)
        df[column_name + '_anomaly'] = df[column_name + '_anomaly'] == -1
        
        # Append anomalies for the current column to the anomalies DataFrame
        anomalies[column_name + '_anomaly'] = df[column_name + '_anomaly']
    
    # Combine anomalies across all signals
    anomalies['combined_anomaly'] = anomalies.any(axis=1)
    
    # Add original columns back to the anomalies DataFrame
    for column_name in column_names:
        anomalies[column_name] = df[column_name]
    
    return anomalies['combined_anomaly']



