import pandas as pd
import json

def file_parser(fp, keyword = "#PJM", delimiter = "="):
    lines = filter(lambda l: l.startswith(keyword), open(fp).readlines())
    return list(map(lambda l: l.split(delimiter)[-1].replace('"', "").replace("'", "").strip(), lines))

def read_user_dataset(fp):
    if fp.endswith(".csv"):
        return pd.read_csv(fp)
    if fp.endswith(".parquet"):
        return pd.read_parquet(fp)
    if fp.endswith(".json"):
        return pd.DataFrame.from_dict(json.load(open(fp, "rb")))

def save_user_dataset(udf, fp):
    if fp.endswith(".csv"):
        udf.to_csv(fp, index=False)
    elif fp.endswith(".parquet"):
        udf.to_parquet(fp, index=False)
    elif fp.endswith(".json"):
        with open(fp, "w") as f:
            json.dump(udf.to_dict(orient="records"), f, indent=4)
    else:
        raise ValueError("Unsupported file format. Use .csv, .parquet or .json.")

def load_json_config(fp):
    with open(fp, "r") as f:
        return json.load(f)
    
    