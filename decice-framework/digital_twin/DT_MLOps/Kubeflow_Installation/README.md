# Kubeflow Installation


## Prerequisites

### Kubernetes Cluster
We need a Kubernetes cluster, which can be created in various ways. Here are some of the ways to create a Kubernetes cluster:
#### [Creating a cluster with kubeadm](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/create-cluster-kubeadm/)

#### [Creating a local Kubernetes with MicroK8s](https://ubuntu.com/tutorials/install-a-local-kubernetes-with-microk8s#1-overview)

MicroK8s can be installed using snap as follows:

```bash
sudo snap install microk8s --channel=1.29/stable --classic
```
```bash
sudo usermod -a -G microk8s $USER
```

```bash
newgrp microk8s
```
Configure MicroK8s



```bash
sudo microk8s enable dns 
```
```bash
sudo microk8s enable hostpath-storage
```

You should enable metallb to provide a load balancer for your services, and you should update IP addresses to match your network configuration. 
For example in simple scenarios, you can use the static IP of your machine.

```bash
sudo microk8s enable metallb:10.64.140.43-10.64.140.49 
```

```bash
sudo microk8s enable rbac
```

## Kubeflow Installation with Juju

```bash
sudo snap install juju --channel=3.4/stable
```

```bash
sudo mkdir -p ~/.local/share
```

```bash
microk8s config | juju add-k8s my-k8s --client
```

```bash
juju bootstrap my-k8s uk8sx
```

```bash
sudo sysctl fs.inotify.max_user_instances=1280
sudo sysctl fs.inotify.max_user_watches=655360
```

If you want these commands to persist across machine restarts, add the following lines to /etc/sysctl.conf:

```bash
fs.inotify.max_user_instances=1280
fs.inotify.max_user_watches=655360
```

### Storage Class and Persistent Volumes

#### Kubeadm Kubernetes
Have a default storage class configured. 

If you don't have a default storage class, you can create one using the following command:

```bash
sudo mkdir -p /mnt/data1
sudo mkdir -p /mnt/data2
sudo mkdir -p /mnt/data3
sudo mkdir -p /mnt/data4
sudo mkdir -p /mnt/data5
 
kubectl apply -f storage-class.yaml
kubectl apply -f pv.yaml
```

#### MicroK8s Kubernetes

If you installed Kubernetes with charmed MicroK8s, you don't need to use the above steps. Instead, simply enable:

```bash
microk8s enable storage
```

### Kubeflow Model

Create the kubeflow model

```bash
juju add-model kubeflow
```

To deploy the most recent stable version, run:

```bash
juju deploy kubeflow --trust --channel=1.9/stable
```

```bash
watch -c juju status --color
```

Set credentials for a static user.
Configure dex-auth with a username and password:

```bash
juju config dex-auth static-username=<new username>
juju config dex-auth static-password=<new password>
```

Ref: [How to install Charmed Kubeflow on Kubernetes](https://charmed-kubeflow.io/docs/install-general)

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