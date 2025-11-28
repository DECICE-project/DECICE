from typing import List
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from feature_encoders.feature_encoder import FeatureEncoder

class SBEncoding(FeatureEncoder):
        
    def __init__(self, weights = "all-MiniLM-L6-v2") -> None:
       self._encoder = SentenceTransformer(weights)
    
    def encode_dataframe(self, df: pd.DataFrame) -> List:
        """
        Encodes the entire DataFrame.
        
        :param df: DataFrame containing job data.
        :return: List of encoded features.
        """
        # Encoding the job data
        encodings = np.zeros((len(df), 384))
        for i in range(len(df)):
            encodings[i] = self.encode_job(df.iloc[i])
        return encodings
       
    def encode_job(self, x:list) -> list:
        try:
            return self._encoder.encode(self._parse_job_data(x)) 
        except Exception as e:
            print(e)
            return []
    
    def _parse_job_data(self, features:list):
        return ",".join(map(str, features))    
