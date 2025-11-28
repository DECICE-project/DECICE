# WATMON Service
Service will run in compute plane(k8s) ,will pull the node information from Prometheus , will serve VertexPool information to WATMON Network Exporters , DECICE Admin should have direct access to this services API to PATCH Vertexpools.  

## Install
requires:   
- python >3.10
- make  

to install:  
```sh
make install
```
## Run REST API
```
make run_api
```