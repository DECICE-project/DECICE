# UoPC: A User-Based Online Framework to Predict Job Power Consumption in HPC Systems

UoPC is a user-based online framework for predicting job power consumption in HPC systems. UoPC leverages ML-based predictive models tailored for individual users, eliminating the need for voluminous data and training. It offers a user-friendly Python implementation suitable for both end-user usage and integration into workload management systems.
It achieves only a 10% prediction error on more than 700k job data extracted from Supercomputer Fugaku, with minimal overhead on the system operations. 

Our approach can predict average and maximum job power consumption, and it can be used to estimate the whole system power consumption with an error of only 4%.  
By employing a k-nearest neighbours (KNN) prediction model augmented with Natural Language Processing, UoPC streamlines prediction processes for newly submitted jobs. It requires only limited historical data, making it practical for diverse high-performance computing environments and workloads.

## How to use

### Installation

1. (Optional) Create and activate a Python virtual environment.
2. Install the required dependencies by running:

   ```sh
   bash install.sh
   ```

### Configuration: Setting up `config.json`

Before running predictions, you need to configure the `config.json` file. This file contains important settings for feature selection, dataset paths, and model parameters.

#### Example `config.json`

```json
{
    "theta":50,
    "k":5,
    "user_dataset":"data/user_data.csv",
    "job_features":[
        "job_name",
        "num_cores",
        "num_nodes",
        "frequency"
    ],
    "order_by":"end_time",
    "target_feature":"avgpcon",
    "encoding":"SBEncoding"
}
```

#### Key Fields

- **job_features**:  
  List of job features (column names) to be used for training and prediction. The order must match the order of values you provide with the `-v` argument.

- **target_feature**:  
  The name of the feature you want to predict (e.g., `"avgpcon"`).

- **user_dataset**:  
  Default path to your user dataset file (CSV, Parquet, or JSON). This can be overridden with the `-d` argument.

- **theta**:  
  Parameter for the prediction algorithm, namely the number of last job executions data to use.

- **k**:
  Parameter for the prediction algorithm, namely the number of neighbors for the KNN.

- **order_by**:
  The feature to use to order the job data in the user dataset.
- **encoding**:
  The encoding technique to use.

#### Tips

- Ensure all feature names in `job_features` and `target_feature` match the column names in your dataset.
- If you change the structure of your dataset, update `config.json` accordingly.
- Use the `config.json` to change the prediction algorithm's parameters.
- You can maintain multiple configuration files for different users or workloads and specify which one to use 

### Usage

Run the prediction script with the required arguments:

```sh
python3 predict.py -v "<comma-separated job feature values>" 
```

- `-v` or `--values`: **(required)** Comma-separated values for the job features as specified in your `config.json` under `"job_features"`.
- `-c` or `--congig`: **(optional)** Path to the configuration file, defaults to `config.json`.
- `-d` or `--user-dataset`: **(optional)** Path to your user dataset file (CSV, Parquet, or JSON). If not provided, the path in `config.json` will be used.
- `-od` or `--override-dataset`: **(optional)** Set to `True` to override and save the encoding for the user dataset.

#### Example

Suppose your job features are: `job_name,num_cores,num_nodes,frequency`. To predict for a new job, run:

```sh
python3 predict.py -v "testcase,256,8,2200"
```

This will print the predicted value for the target feature specified in your configuration.

---

