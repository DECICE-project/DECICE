FROM ubuntu:latest
RUN apt-get update && apt-get install -y python3.10 python3-pip vim
RUN pip install pandas
RUN pip install numpy
RUN pip install scikit-learn
RUN pip install pytz 
RUN pip install cachetools 
RUN pip install diskcache==5.2.1
RUN pip install "dask[complete]" 
RUN pip install paho-mqtt
RUN pip install torch
RUN pip install torch-geometric
RUN pip install --upgrade torch
# RUN pip install minio


COPY ./ /hpc_gnn_mlops/
WORKDIR /hpc_gnn_mlops/

