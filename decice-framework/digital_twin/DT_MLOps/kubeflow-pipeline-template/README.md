# Simple kubeflow ML Pipeline Template

This template provides a simple example of a machine learning pipeline using Kubeflow Pipelines (KFP). It includes functions to:

- Create a dataset
- Preprocess the dataset
- Train a simple machine learning model
- Run inference using the trained model

The pipeline is designed to be customizable, allowing you to modify each function to fit your specific use case.

## Steps to Use the Template

### 1. Dataset Creation (`create_dataset`)
**Objective:** Create and save a dataset to a shared location.

**Modify the Code:** Customize the `create_dataset` function to fit your dataset creation process (e.g., loading from a file or generating synthetic data).

**Parameters:**
- `data_path`: Path to store the created dataset. Change this if needed.

**Action:** Once the function is modified, the dataset will be saved as a `.npy` file.

---

### 2. Data Preprocessing (`preprocess_data`)
**Objective:** Process the dataset created in the previous step. This can include tasks like normalization, feature engineering, or cleaning.

**Modify the Code:** Adjust the `preprocess_data` function to implement your preprocessing steps.

**Parameters:**
- `data_path`: Path to the dataset created in step 1.
- `processed_data_path`: Path to store the processed dataset. Change this if needed.

**Action:** The function will save the processed data to the specified path.

---

### 3. Model Training (`train_model`)
**Objective:** Train a machine learning model using the preprocessed dataset.

**Modify the Code:** Replace the simple linear model with your own model architecture and training process.

**Parameters:**
- `processed_data_path`: Path to the preprocessed data.
- `model_path`: Path to save the trained model.
- `log_dir`: Directory for TensorBoard logs (optional).

**Action:** After training, the model is saved in the `model_path` directory and logs are saved for TensorBoard.

---

### 4. Inference (`run_inference`)
**Objective:** Use the trained model to make predictions.

**Modify the Code:** Adjust the `run_inference` function to fit the input and output format of your model. For instance, modify the input data and the model prediction logic.

**Parameters:**
- `model_path`: Path to load the trained model.

**Action:** The model will be loaded, and predictions will be printed to the console.

---

### 5. Kubeflow Pipeline Structure (`simple_ml_pipeline`)
**Objective:** Define the sequence of steps in the machine learning pipeline.

**Modify the Code:**
- Link the components in the desired order. For example, the `train_model` task should follow the `preprocess_data` task.
- Define shared data volumes using Persistent Volume Claims (PVCs) to share data across components.

**Action:** The pipeline will execute the tasks in order, and each task will have access to the shared volume for reading/writing data.

---

### 6. Compile and Deploy the Pipeline  
**Objective:** Once the pipeline is defined, you need to compile it into a YAML or TAR file to upload to Kubeflow.  

**Action:**  
- Use `kfp.compiler.Compiler().compile()` to compile the pipeline into a `.yaml` file.  
- Upload the compiled `.yaml` file to your Kubeflow instance and run it as a pipeline.  
- **After uploading the pipeline**, create a **run** to execute the pipeline.  
- Ensure that a **Persistent Volume Claim (PVC)** is created with the same name as specified in the pipeline (e.g., `"shared-pvc"`) to provide shared storage for the pipeline components.  
- This PVC that you should craet manually will be assigned to the pipeline so that data can be shared across different steps.  

---

## Example Usage
1. Modify the functions (`create_dataset`, `preprocess_data`, `train_model`, `run_inference`) to suit your specific dataset, preprocessing steps, model architecture, and inference logic.
2. Customize the paths used for data storage (`data_path`, `processed_data_path`, `model_path`, etc.).
3. Define the pipeline structure by linking the components in the correct order using the `@dsl.pipeline` decorator.
4. Compile the pipeline and upload it to your Kubeflow instance to run.

---

## Requirements
Ensure the following Python packages are installed:

```bash
pip install kfp tensorflow numpy mlflow kubernetes boto3
```

This template should provide a good starting point for building machine learning pipelines in Kubeflow. Modify the dataset, model, and pipeline structure as needed to adapt to your specific use case.
