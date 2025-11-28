import pandas as pd
import numpy as np
from sklearn.svm import OneClassSVM
import pandas as pd
import numpy as np
from sklearn.svm import OneClassSVM

def detect_anomalies_one_class_svm(df, column_names=None, threshold=50,nu=0.1, kernel='rbf'):

    model = OneClassSVM(nu=nu, kernel=kernel)
    predictions = model.fit_predict(df[column_names]) # Fit the model and predict outliers for the specified columns
    anomaly_scores = model.decision_function(df[column_names])  # Get anomaly scores (distance from the hyperplane)
    anomalies=pd.DataFrame()
    anomalies['combined_anomaly_score'] = anomaly_scores
    anomalies = pd.DataFrame(index=df.index)    # Create an anomalies DataFrame to store results


    anomalies['combined_anomaly'] = anomaly_scores > threshold    # Store anomaly flags and scores in the DataFrame
    anomalies['combined_anomaly_score'] = anomaly_scores

    for column_name in column_names:
        anomalies[column_name] = df[column_name]

    return anomalies['combined_anomaly']
