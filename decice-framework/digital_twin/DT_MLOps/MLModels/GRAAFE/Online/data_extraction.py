from examon.examon import Examon, ExamonQL
import pytz
import pandas as pd
import datetime
import asyncio
  

def examon_client(KAIROSDB_SERVER, KAIROSDB_PORT, USER, PWD):
    ex = Examon(KAIROSDB_SERVER, port=KAIROSDB_PORT, user=USER, password=PWD, verbose=False, proxy=True)
    sq = ExamonQL(ex)
    return sq



async def dxt(sq, diff, rack_name, metric): 
    if rack_name == 'all':
        # print('All Racks of Marconi100')
        df = sq.SELECT('node')\
            .FROM(metric)\
            .WHERE(cluster='marconi100', plugin='ipmi_pub')\
            .TSTART(int(diff), 'seconds')\
            .execute().df_table
    else:
        # print(f'Rack {rack_name}') 
        nodes = f'{rack_name}n01,{rack_name}n02,{rack_name}n03,{rack_name}n04,{rack_name}n05,'\
            +f'{rack_name}n06,{rack_name}n07,{rack_name}n08,{rack_name}n09,{rack_name}n10,'\
            +f'{rack_name}n11,{rack_name}n12,{rack_name}n13,{rack_name}n14,{rack_name}n15,'\
            +f'{rack_name}n16,{rack_name}n17,{rack_name}n18,{rack_name}n19,{rack_name}n20'
        
        df = sq.SELECT('node')\
            .FROM(metric)\
            .WHERE(cluster='marconi100', plugin='ipmi_pub', node=nodes)\
            .TSTART(int(diff), 'seconds')\
            .execute().df_table
    return df

async def run_queries(sq, diff, rack_name, metrics):
    tasks = [asyncio.create_task(dxt(sq, diff, rack_name, metric)) for metric in metrics] 
    results = await asyncio.gather(*tasks)
    final_result =  pd.concat(results) 
    if 'timestamp' in final_result.columns:
        final_result.set_index('timestamp', inplace=True)
    return final_result


metrics = pd.read_csv('metrics').metrics.values.tolist()

def run_dxt(sq, diff, rack_name, metrics=metrics): 
    result = asyncio.run(run_queries(sq, diff, rack_name, metrics)) 
    return result


def append_cutoff_df_raw(df_raw_old, df_raw): 
    df_raw = pd.concat([df_raw, df_raw_old])
    
    
    df_raw.reset_index(inplace=True)
    df_raw = df_raw.drop_duplicates()
    if 'timestamp' in df_raw.columns:
        df_raw.set_index('timestamp', inplace=True)
    
    
    max_index = df_raw.index.max()
    cutoff_index = max_index - datetime.timedelta(seconds=15*60)
    # filter the dataframe to keep rows after the cutoff index
    df_raw = df_raw.loc[df_raw.index > cutoff_index]
    return df_raw

    


def DIFF_minutes(df_raw):
    try:
        LAST_INDEX = df_raw.index.max()
        NOW = datetime.datetime.now(pytz.timezone('Europe/Rome')) 
        DIFF = NOW - LAST_INDEX
        DIFF =  int((1 + DIFF.total_seconds()))
        DIFF = min([DIFF, 15*60])
        print(f'Data of Last {DIFF} Seconds Are Donwloading! - Now : {NOW} - Last Index of Cached Data : {LAST_INDEX}')
        return DIFF
    except Exception as e:
        print(f'error DIFF_minutes(df_raw) ==> {e}')        
        return 15*60
    

    