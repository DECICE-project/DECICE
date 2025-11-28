from typing import List
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from feature_encoders.feature_encoder import FeatureEncoder

class INTEncoder(FeatureEncoder):
        
    def __init__(self, weights = "all-MiniLM-L6-v2") -> None:
       self._encoder = LabelEncoder()
    
    def encode_dataframe(self, df: pd.DataFrame) -> List:
        """
        Encodes the entire DataFrame.
        
        :param df: DataFrame containing job data.
        :return: List of encoded features.
        """
        # Encoding the job data
        df["encodings"] = df.apply(lambda x: self.encode_job(x), axis=1)
       
    def encode_job(self, x:list) -> list:
        try:
            return self._encoder.fit_transform(x) 
        except Exception as e:
            print(e)
            return []
    

