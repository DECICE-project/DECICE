import data_extraction
import preprocessing
import inference
import publishing_results
import argparse
from logging_module import logging
import logging_module
import torch
import pandas as pd
import numpy as np
import datetime, pytz, time





map_rack_name = {'r205':0,'r206':1,'r207':2,'r208':3,'r209':4,'r210':5,'r211':6,'r212':7,'r213':8,'r214':9,
                 'r215':10,'r216':11,'r217':12,'r218':13,'r219':14,'r220':15,'r221':16,'r222':17,'r223':18,'r224':19,
                 'r225':20,'r226':21,'r227':22,'r228':23,'r229':24,'r231':25,'r232':26,'r233':27,'r234':28,'r236':29,
                 'r237':30,'r238':31,'r239':32,'r240':33,'r241':34,'r242':35,'r243':36,'r244':37,'r245':38,'r246':39,
                 'r247':40,'r248':41,'r249':42,'r250':43,'r251':44,'r253':45,'r254':46,'r255':47,'r256':48}
rack_name_list = map_rack_name.keys()


if __name__ == '__main__':
    print("-------------------------  __main__  -------------------------")
    parser = argparse.ArgumentParser(description='My script description')

    parser.add_argument('-ir', '--inference_rate', type=int, help='This shows the inference rate in seconds.',default=0)
    parser.add_argument('-r', '--rack_name', type=str, help='Rack Name, all mesans all racks of the M100 one by one in serial approach. ',default='r256')
    parser.add_argument('-ph', '--prediction_horizon', type=int, help='Prediction Horizon. ',default=24)
    
    # ExaMon
    parser.add_argument('-es', '--examon_server', type=str, help='KAIROSDB_SERVER = "examon.cineca.it"', default="examon.cineca.it")
    parser.add_argument('-ep', '--examon_port', type=str, help='KAIROSDB_PORT = "3000"',default="3000")
    parser.add_argument('-euser', '--examon_user', type=str, help='Examon Username')
    parser.add_argument('-epwd', '--examon_pwd', type=str, help='Examon Password')

    # Publishing Results 
    parser.add_argument('-bs', '--broker_address', type=str, help='broker_address = "192.168.0.35" or broker_address = "examon.cineca.it"', default="192.168.0.35")
    parser.add_argument('-bp', '--broker_port', type=int, help='broker_port = 1883', default=1883)


    args = parser.parse_args()


    inference_rate = args.inference_rate
    rack_name = args.rack_name
    prediction_horizon = args.prediction_horizon
    KAIROSDB_SERVER = args.examon_server
    KAIROSDB_PORT = args.examon_port
    USER = args.examon_user
    PWD = args.examon_pwd
    broker_address= args.broker_address
    broker_port= args.broker_port


    print('----------- Initiate ExaMon Client -----------')
    try:
        sq = data_extraction.examon_client(KAIROSDB_SERVER, KAIROSDB_PORT, USER, PWD)
    except Exception as e:
        print(e)
        logging_module.logging.info(f"Error :{e}")
    

    print('----------- Initiate MQTT -----------')
    try:
        client = publishing_results.gnn_mqtt_client_instance(broker_address=broker_address,broker_port=broker_port)
        client.on_publish = publishing_results.on_publish
        print('----------- Start MQTT Loop -----------')
        client.loop_start()
    except Exception as e:
        print('Your IP address is not valid for publishing the value to the Examon broker.')
        print(e)
        logging_module.logging.info(f"Error :{e}")
        
    
    
    # All Racks, One Pod 
    if rack_name == 'all':
        print('----------- All Racks in Serial -----------')
        print('----------- Start Loop -----------')
        # create DataFrame with one row and index in UTC
        df_raw = pd.DataFrame(index=[pd.to_datetime('2023-04-01 00:00:00')])
        df_raw.index.name = "timestamp" 
        # localize index to UTC timezone
        df_raw.index = df_raw.index.tz_localize('UTC')
        # convert index to Europe/Rome timezone
        df_raw.index = df_raw.index.tz_convert('Europe/Rome')


        while True:
            start_time_loop = logging_module.start_time(f'Loop Start ==> ',logging)
            try:
                print('----------- Data Extraction From ExaMon -----------')
                DIFF = data_extraction.DIFF_minutes(df_raw)
                start_time = logging_module.start_time(f'dxt start ==> ',logging)
                df_just_extracted = data_extraction.run_dxt(sq=sq, diff=DIFF, rack_name='all')
                logging_module.end_time(f'dxt End ==> ',logging, start_time)


                print('----------- Data Preprocessing Room -----------')
                start_time = logging_module.start_time(f'Room Start ==> first preprocessing {df_raw.shape}, {df_just_extracted.shape}',logging)     
                df_raw = data_extraction.append_cutoff_df_raw(df_raw, df_just_extracted)
                df_agg = preprocessing.agg_df_avg_min_max_std(df_raw)
                logging_module.end_time('Room End ==> (I) preprocessing Room',logging, start_time) 
                
                print('----------- Inference Room -----------')
                for i, rack_name in enumerate(set([i.split('n')[0] for i in pd.read_csv('node_names').node_name.values])):
                    try:
                        print('----------- II Preprocessing -----------')
                        start_time = logging_module.start_time(f'{i} - {rack_name} ==> (II) preprocessing_rack',logging)
                        df_rack = preprocessing.rack_df(df_agg, rack_name=rack_name)
                        dg_rack = preprocessing.convert_to_graph_data(df_rack)            
                        logging_module.end_time(f'{i} - {rack_name} ==> (II) preprocessing_rack',logging, start_time)


                        print('----------- Inference Rack -----------')
                        start_time = logging_module.start_time(f'{i} - {rack_name}  ==> start inference_rack',logging)
                        in_channels, out_channels = dg_rack.num_node_features, 16
                        # in_channels, out_channels = 417, 16 

                        model = inference.anomaly_anticipation(in_channels, out_channels)
                        
                        PATH = f'./models/{str(prediction_horizon)}/{map_rack_name[rack_name]}_{str(prediction_horizon)}.pth'

                        model.load_state_dict(torch.load(PATH, map_location=torch.device('cpu')))
                        model.eval()
                        inference_rack = inference.inference(model, dg_rack)
                        logging_module.end_time('One Rack End ==> inference_rack',logging, start_time)
                        print(f'{dg_rack}, rack inference {inference_rack.shape}')
                        logging_module.end_time(f'{i} - {rack_name} ==> end inference_rack',logging, start_time)
                    except Exception as e:
                        print(f'ERROR {i} - {rack_name} ==> {e}')
                        logging_module.logging.info(f'ERROR {i} - {rack_name} ==> {e}')
                        
                    print(f'----------- Inference Trans MQTT {rack_name} -----------')
                
                    start_time = logging_module.start_time(f'Rack {rack_name} Start ==> MQTT',logging)
                    for i in range(20):
                        try:
                            node_name = f"{rack_name}n{str(i+1).zfill(2)}"
                            topic = publishing_results.gnn_topic_creator(node_name)
                            pred = inference_rack[i].item()
                            publishing_results.gnn_pub(topic=topic, val=pred, client=client)
                        except Exception as e:
                            print('Your IP address is not valid for publishing the value to the Examon broker.')
                            print(f"ERROR :rack {rack_name} chassis {i+1} => {e}")
                            logging_module.logging.info(f"ERROR :rack {rack_name} chassis {i+1} => {e}")

                    logging_module.end_time(f'Rack {rack_name} End ==> MQTT',logging, start_time)

            except Exception as e:
                print(f"ERROR :{e}")
                logging_module.logging.info(f"ERROR :{e}")
            loop_taken_time = logging_module.end_time('Loop End ==> ',logging, start_time_loop)
            time.sleep(preprocessing.sleep_time(rate=args.inference_rate, loop_taken_time=loop_taken_time))
    

    # One Rack

    elif rack_name:
        print(f"-------------------------  {rack_name}  -------------------------")
        assert rack_name in rack_name_list, f"The rack_name should be chosen from the following list: {rack_name_list}"
        # create DataFrame with one row and index in UTC
        df_raw = pd.DataFrame(index=[pd.to_datetime('2023-01-01 00:00:00')])
        df_raw.index.name = "timestamp" 
        # localize index to UTC timezone
        df_raw.index = df_raw.index.tz_localize('UTC')

        # convert index to Europe/Rome timezone
        df_raw.index = df_raw.index.tz_convert('Europe/Rome')


        print('----------- Start Loop -----------')
        while True:
            start_time_loop = logging_module.start_time(f'Loop Start ==> ',logging)
            try:
                print('----------- Data Extraction From Examon -----------')
                DIFF = data_extraction.DIFF_minutes(df_raw)
                start_time = logging_module.start_time(f'{rack_name} dxt start ==> ',logging)
                df_just_extracted = data_extraction.run_dxt(sq=sq, diff=DIFF, rack_name=rack_name)
                logging_module.end_time(f'{rack_name} dxt End ==> ',logging, start_time)


                print('----------- Data Preprocessing Rack -----------')
                start_time = logging_module.start_time('One Rack Start ==> preprocessing',logging)     
                print(df_raw.shape, df_just_extracted.shape)
                df_raw = data_extraction.append_cutoff_df_raw(df_raw, df_just_extracted)
                # df_raw = df_just_extracted
                dg_rack = preprocessing.graph_rack(df_raw=df_raw, rack_name=rack_name)
                logging_module.end_time('One Rack End ==> preprocessing',logging, start_time)


                print('----------- Inference Rack -----------')
                start_time = logging_module.start_time('One Rack Start ==> inference',logging)
                in_channels, out_channels = dg_rack.num_node_features, 16
                # in_channels, out_channels = 417, 16 
                model = inference.anomaly_anticipation(in_channels, out_channels)
                
                PATH = f'./models/{str(prediction_horizon)}/{map_rack_name[rack_name]}_{str(prediction_horizon)}.pth'
                
                
                
                model.load_state_dict(torch.load(PATH, map_location=torch.device('cpu')))
                model.eval()
                inference_rack = inference.inference(model, dg_rack)
                logging_module.end_time('One Rack End ==> inference',logging, start_time)
                print(df_raw.shape, dg_rack, inference_rack.shape)

            except Exception as e:
                print(e)
                logging_module.logging.info(f"Error :{e}")
        
        
            print('----------- Inference Trans MQTT -----------')
            try:
                start_time = logging_module.start_time('One Rack Start ==> MQTT',logging)
                for i in range(20):
                    try:
                        node_name = f"{rack_name}n{str(i+1).zfill(2)}"
                        topic = publishing_results.gnn_topic_creator(node_name)
                        pred = inference_rack[i].item()
                        publishing_results.gnn_pub(topic=topic, val=pred, client=client)
                    except Exception as e:
                        print('Your IP address is not valid for publishing the value to the Examon broker.')
                        print(f"ERROR :rack {rack_name} chassis {i+1} => {e}")
                        logging_module.logging.info(f"ERROR :rack {rack_name} chassis {i+1} => {e}")
                        
                logging_module.end_time('One Rack End ==> MQTT',logging, start_time)
            except Exception as e:
                print(e)
                logging_module.logging.info(f"Error :{e}")
                
            loop_taken_time = logging_module.end_time('Loop End ==> ',logging, start_time_loop)
            time.sleep(preprocessing.sleep_time(rate=args.inference_rate, loop_taken_time=loop_taken_time))

    