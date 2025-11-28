import argparse
import pandas as pd

from feature_encoders.sbert_encoder import SBEncoding
from feature_encoders.int_encoder import INTEncoder
from predictive_models.knn import KNN
from utils.utils import read_user_dataset, save_user_dataset, load_json_config

if __name__ == "__main__":

    # Load the configuration file
    config = load_json_config("config.json")
    
    # Add parser for the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--user-dataset", type=str, required=False, help="Path to the user dataset file")
    parser.add_argument("-c", "--config", type=str, required=False, default="config.json",
                        help="Path to the configuration file")
    parser.add_argument("-v", "--values", type=str, required=True, nargs='+',
                        help="Values of the job features to predict, e.g. -v 'feature1 value1' 'feature2 value2'")
    parser.add_argument("-od", "--override-dataset", type=bool, default=False, required=False,
                        help="Override the user dataset with the new one")
    
    args = parser.parse_args()

    dataset_path = config["user_dataset"]
    
    # If the user dataset is not provided the prediction cannot be performed
    if args.user_dataset:
        dataset_path = args.user_dataset
    if not(dataset_path):
        raise Exception("Please provide a user dataset file, either in the config.json file or via the -d argument.")
         
    # Init the components of the framework
    predictive_model = KNN(k = config["k"], n_jobs = -1)
    encoder = SBEncoding() if config["encoding"] == "SBEncoding" else INTEncoder()
    
    # Read the user data and build the predictive model
    udf = read_user_dataset(dataset_path).sort_values(by=config["order_by"], ascending=False).iloc[:config["theta"]]
    # Check if the encodings are already present in the user dataset
    if "encodings" not in udf.columns:
        # Encoding the job data
        encodings = encoder.encode_dataframe(udf[config["job_features"]])
    if args.override_dataset:
        # If the user dataset is overridden, we need to re-encode the job data
        udf["encodings"] = encodings
        save_user_dataset(udf, dataset_path)
    
    # Train the model with the user data
    predictive_model.train(x = encodings, y = udf[config["target_feature"]])
    
    # Retrieve the new job data
    job_features = args.values
    
    # Return the prediction
    new_jobs_encodings = [encoder.encode_job(jf) for jf in job_features]
    predicted_values = predictive_model.predict(new_jobs_encodings)
    for job_input, predcited_value in zip(job_features, predicted_values):
        print(f"Job: {job_input}, Predicted Value: {predcited_value}")
    
    