# **GRAAFE: GRaph Anomaly Anticipation Framework for Exascale HPC systems**

### Authors: Martin Molan, Mohsen Seyedkazemi Ardebili, Junaid Ahmed Khan, Francesco Beneventi, Daniele Cesarini, Andrea Borghesi, Andrea Bartolini



![Screenshot from 2023-04-13 11-08-35](https://user-images.githubusercontent.com/13011878/231729695-fb6b5e87-b932-49df-859f-b87156e1b994.png)

To reproduce the results of Deployment Evaluation of Monitoring and MLOps frameworks in HPC, you need three main requirements. First, a datacenter monitoring system that collects online datacenter metrics such as power and CPU frequency. Second, GNN models which well-trained on historical data. Third, a cloud system with Kubernetes and Kubeflow installed. For small-scale tests, you can even use your laptop for the last requirement.  

This repository includes eight sets of artifacts. In the following, we provided more detailed information about them 

## ExaMon

The folder `examon` contains the libraries required to extract data from the monitoring system. For more information about the monitoring system, refer to [this repository](https://github.com/EEESlab/examon/tree/develop/docker) and [this paper](https://doi.org/10.1145/3339186.3339215).



## Models

The `models` folder contains trained GNN models, including their weights and parameters, for the CINECA Marconi100 HPC system..

## Python Scripts

The python `*.py` files in general contain scripts provided that provide necessary scripts for doing anomaly prediction. 

`data_extraction.py`: This Python script uses the libraries in the `examon` folder to extract monitoring data of the compute nodes from the monitoring system. The `node_names` file contains the list of compute nodes for the CINECA Marconi100 HPC system, and the `metrics` file contains the list of metrics from which we need to extract data. To connect and extract data from ExaMon, you need an account on this monitoring system.

`preprocessing.py` : This Python script provides some functions that are needed to convert the raw data extracted from ExaMon to the data format that is useful for the GNN models. With function `agg_df_avg_min_max_std(df: Pandas.DataFrame)` computes the new features (std, min, max, mean) for the `metrics` and then the function `convert_to_graph_data(df: Pandas.DataFrame)` converts the Pandas.DataFrame to the graph using `torch_geometric.data` class of torch which is a format the GNN model receives input data.    

`inference.py`: This Python file contains scripts that create a GNN model with PyTorch.  

`publishing_results.py`: This Python file contains scripts that sned (publish) the results of predictions to the monitoring system using the MQTT protocol.   

`logging_module.py`: This Python file contains scripts for creating a logging system for necessary parameters.  

`main.py`: This Python file contains all the scripts needed to use the functions defined in other Python files for (I) data extraction, (II) preprocessing, (III) inference, and finally (IV) sending the prediction results to the monitoring system.   

## Dockerfile

A `Dockerfile` is a recipe for creating a Docker image.

## Other Files

The `requirements.txt` file lists the software package requirements for Python scripts. `node_names` is a list of names of compute nodes, and `metrics` is a list of metrics from which we need to extract data from the monitoring system.

## GitHub Actions

The `github_action_config.yaml` file provides configuration scripts for automating the build and push of a Docker image to Docker Hub using [GitHub Actions](https://docs.github.com/en/actions). Here's a quick summary of the steps involved:

1. In your repository, go to Settings → Secrets and variables → Actions → New repository secret, and create two new secrets for your Docker Hub username and password.
2. In your GitHub repository, go to Actions → New workflow → Suggested for this repository, or set up the workflow yourself.
3. Copy and paste the scripts provided in `github_action_config.yaml` into the workflow file. Make sure to use the correct secret names for the username and password. In "docker build" and "docker push", specify the name of the Docker image you prefer. In this case, we used "gnnexamon".
4. Push the commit to trigger the workflow.

For more detailed instructions, refer to the [official GitHub Actions documentation](https://docs.github.com/en/actions).

**Note:** For reproducing all steps in the way that we did, you need to have a [docker hub](https://www.notion.so/Docker-d5fcbd6532e64a80af7125a9d6bc5912) and [GitHub](https://github.com/) accounts. But these are not mandatory since you can just download the [docker image](https://hub.docker.com/repository/docker/kazemi/gnnexamon/general) that we create, and you can find it in [this link.](https://hub.docker.com/repository/docker/kazemi/gnnexamon/general) 

## Kubeflow

Kubeflow is an open-source machine-learning tool that is built on top of Kubernetes. As such, it requires Kubernetes to be installed. Here is a useful [link](https://charmed-kubeflow.io/docs/get-started-with-charmed-kubeflow) to a tutorial that provides step-by-step instructions on how to install Microk8s - a lightweight version of Kubernetes that can even be installed on your laptop. Additionally, the tutorial provides guidance on how to install and use Kubeflow. Microk8s is a great option for those who are new to Kubernetes and want to get started with Kubeflow quickly and easily. Once you have installed Microk8s, you can follow the tutorial to install and use Kubeflow. With Kubeflow, you can easily develop and deploy machine learning models at scale.

## Kubeflow Pipeline

The `gnn_pipelines.ipynb` is a Jupyter notebook that contains scripts for creating and running Kubeflow pipelines. Kubeflow Pipelines (kfp) is a platform for building and deploying portable, scalable machine learning (ML) workflows based on Docker containers. [Here in this link, you can find more information about the kfp.](https://www.kubeflow.org/docs/components/pipelines/v1/introduction/)

The Kubeflow Pipelines SDK provides a set of Python packages that you can use to specify and run your machine learning (ML) workflows. A pipeline is a description of an ML workflow, including all of the components that make up the steps in the workflow and how the components interact with each other.

Like the following scripts, to create the Kubeflow pipeline, first, we create a component of the pipeline using the component package and the class `components.load_component_from_text()`, which loads components from text and creates a task factory function. We then create components from the Docker image by pulling the image from `docker.io/kazemi/gnnexamon`. Next, we execute `main.py` from the directory `/hpc_gnn_mlops/` inside the Docker container, defining the correct values for arguments such as the examon username and password, the name of the rack and broker server, and the inference rate.   

```python
gnn= components.load_component_from_text("""
name: Online Prediction
description: A pipeline that performs anomaly prediction on a Tier-0 supercomputer.

implementation:
  container:
    image: kazemi/gnnexamon
    command: [
    "/bin/sh",
    "-c",
    "cd /hpc_gnn_mlops/ && python3 main.py -euser 'XYZ' -epwd 'XYZ' -r 'r256'  -bs '192.168.0.35' -ir 0"
    ]
""")
```

List of the main arguments 

```
-ir, --inference_rate, type=int, help=This shows the inference rate in seconds.,default=0
-r, --rack_name, type=str, help=Rack Name, all mesans all racks of the M100 one by one in serial approach. ,default='r256'
-ph, --prediction_horizon, type=int, help=Prediction Horizon. ,default=24
# ExaMon
-es, --examon_server, type=str, help=KAIROSDB_SERVER = "examon.cineca.it", default="examon.cineca.it"
-ep, --examon_port, type=str, help=KAIROSDB_PORT = "3000",default="3000"
-euser, --examon_user, type=str, help=Examon Username
-epwd, --examon_pwd, type=str, help=Examon Password
# Publishing Results 
-bs, --broker_address, type=str, help=broker_address = "192.168.0.35" or broker_address = "examon.cineca.it", default="192.168.0.35"
-bp, --broker_port, type=int, help=broker_port = 1883, default=1883
```

After creating this component, we should define the pipeline. Finally, we can create and run a Kubeflow run - experiment.


This notebook contains six different experiments that we conducted on paper.


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

Thank you for supporting our work! If you have any questions or suggestions, feel free to reach out through the repository's Issues section or contact us directly.
