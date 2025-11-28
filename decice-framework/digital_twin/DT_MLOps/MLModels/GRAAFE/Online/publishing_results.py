from logging_module import logging
import datetime, pytz, time
import paho.mqtt.client as mqtt
import numpy as np
import pandas as pd



def gnn_topic_creator(node_name):
    topic = f"org/cineca/cluster/marconi100/node/{node_name}/room/f/plugin/examon-ai_pub/chnl/data/config/debug/gnn"
    return topic 

def gnn_mqtt_client_instance(broker_address,broker_port):
    print('----------- Create an MQTT Client Instance -----------')
    # create an MQTT client instance
    client = mqtt.Client()

    # set the connection parameters for the broker
    client.connect(broker_address, broker_port)

    return client

def on_publish(client, userdata, result):
    # print("Data published to MQTT")
    pass

def gnn_pub(topic, val, client): 
    try:
        (result, mid) = client.publish(topic, '{0};{1}'.format(val, time.time()))
        if result == mqtt.MQTT_ERR_SUCCESS:
            print(f"Data published successfully. message ID:{mid}")
        elif result == mqtt.MQTT_ERR_NO_CONN:
            print(f"Error: Connection refused or network error. message ID:{mid}")
        elif result == mqtt.MQTT_ERR_QUEUE_SIZE:
            print(f"Error: Publish queue is full. message ID:{mid}")
        elif result == mqtt.MQTT_ERR_PAYLOAD_SIZE:
            print(f"Error: Payload size exceeded the maximum allowed limit. message ID:{mid}")
        else:
            print(f"Error: Unknown error occurred. message ID:{mid}")
    except Exception as e:
        print(e) 


