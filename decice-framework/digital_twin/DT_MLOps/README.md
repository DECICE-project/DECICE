# Digital Twins Machine Learning Modules

## Machine Learning Operations

MLOps (Machine Learning Operations) is a set of practices that aims to streamline and automate the processes involved in developing, deploying, and maintaining machine learning models in production. MLOps integrates machine learning workflows with DevOps principles to create a seamless end-to-end pipeline. The goal is to enhance collaboration between data scientists and operations teams, ensure reproducibility, and enable scalable model management.

To implement MLOps for this project, we are using [Kubeflow](https://www.kubeflow.org/).

### Kubeflow

Kubeflow is an open-source platform designed to facilitate the deployment, orchestration, and management of machine learning workflows on Kubernetes. Originally developed by Google, Kubeflow provides a unified toolkit for managing the entire machine learning lifecycle, from data preprocessing and training to deployment and monitoring. Its Kubernetes-based infrastructure allows for easy scaling and efficient resource management, making it ideal for production-grade machine learning operations.

With Kubeflow, we can:

- Automate complex ML workflows and pipelines
- Scale training and deployment across multiple nodes
- Streamline collaboration across teams with reproducible and reusable components

By leveraging Kubeflow, we enhance the robustness and scalability of our MLOps implementation, ensuring that models are efficiently deployed and managed in a production environment.

For more information on Kubeflow, visit the [official Kubeflow website](https://www.kubeflow.org/).

## DTMLOps

DTMLOps is an enhanced MLOps solution that integrates MLOps with the DECICE Digital Twins and monitoring system. DECICE Digital Twins are virtual replicas of physical devices or systems that provide real-time insights into their operations and performance.
With DTMLOps, we aim to develop and deploy machine learning models that detect/predict anomalies or specific behaviors in DECICE monitoring signals, such as temperature, CPU, Memory fluctuations, energy consumption spikes, and performance degradation.

By leveraging both Kubeflow and DECICE Digital Twins, DTMLOps enables us to:

- Automate the end-to-end machine learning pipeline on DECICE computing continuum
- Use real-time monitoring data to train and fine-tune models continuously
- Detect and predict potential issues in computing continuum operations, helping improve system reliability and performance

This integration of MLOps and Digital Twins, provides a powerful solution for predictive monitoring and proactive maintenance in computing continuum environments, ensuring optimized performance and efficient resource utilization.



## Machine Learning Models:
- [Computing Continuum Nodes Anomaly Detection](./MLModels/Node_Anomaly_Detection/)
- [Carbon Intensity Prediction](./MLModels/Green_Computing/)
- [UoPC: A User-Based Online Framework to Predict Job Power Consumption in HPC Systems](./MLModels/UoPC/)
- [GRAAFE: GRaph Anomaly Anticipation Framework for Exascale HPC systems](./MLModels/GRAAFE/)

### Kubeflow Pipeline Template
- [Kubeflow Pipeline Template](./kubeflow-pipeline-template/)

The Kubeflow Pipeline Template is an example designed to simplify the creation and management of machine learning pipelines using Kubeflow. It includes customizable functions for dataset creation, preprocessing, model training, and inference, allowing users to tailor each step to their specific needs. The template also provides detailed instructions on modifying the code, defining pipeline structure, and deploying the pipeline on Kubeflow. By leveraging this template, users can efficiently automate and scale their ML workflows, ensuring robust and reproducible model deployment in production environments. For more details, refer to the Kubeflow Pipeline Template README.

## Citation
If you find the tools or code in this repository useful for your research or work, please consider citing our paper:

```bibtex
@article{graafe,
  title={GRAAFE: GRaph anomaly anticipation framework for exascale HPC systems},
  author={Molan, Martin and Ardebili, Mohsen Seyedkazemi and Khan, Junaid Ahmed and Beneventi, Francesco and Cesarini, Daniele and Borghesi, Andrea and Bartolini, Andrea},
  journal={Future Generation Computer Systems},
  year={2024},
  publisher={Elsevier}
}
```

<!-- Thank you for supporting our work! If you have any questions or suggestions, feel free to reach out through the repository's Issues section or contact us directly. -->