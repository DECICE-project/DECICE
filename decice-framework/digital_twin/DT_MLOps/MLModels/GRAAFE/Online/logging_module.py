import logging
import os
import time, datetime
import pytz
rome_timezone = pytz.timezone('Europe/Rome')


def check_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path)
        print(path+" ==> CREATED.")





loggin_path = './log/'

check_dir(loggin_path)
log_file_name = 'log' + '-' + datetime.datetime.strftime(datetime.datetime.now(pytz.timezone('Europe/Rome')), '%Y-%m-%d').replace(':','-').replace(' ','-')+'.log'

formatter = '%(levelname)s:%(lineno)d:%(process)d:%(processName)s:%(thread)d:%(threadName)s:%(asctime)s:%(message)s'

logging.basicConfig(filename=os.path.join(loggin_path,log_file_name),
                    level=logging.INFO,
                    format=formatter)

def start_time(title, logging):    
    time_format = "%Y-%m-%d-%H-%M-%S.%f"
    start_time = time.time()
    formatted_start_time = datetime.datetime.fromtimestamp(start_time).astimezone(rome_timezone).strftime(time_format)
    print(f"{title} start time: {formatted_start_time}")
    logging.info(f"{title} Start time: {formatted_start_time}")
    return start_time
    
def end_time(title, logging, start_time):  
    time_format = "%Y-%m-%d-%H-%M-%S.%f"
    end_time = time.time()
    formatted_end_time = datetime.datetime.fromtimestamp(end_time).astimezone(rome_timezone).strftime(time_format)
    print(f"{title} End time: {formatted_end_time}")
    logging.info(f"{title} End time: {formatted_end_time}")
    print(f"{title} Time taken: {end_time - start_time} seconds")
    logging.info(f"{title} Time taken: {end_time - start_time} seconds")
    return end_time - start_time