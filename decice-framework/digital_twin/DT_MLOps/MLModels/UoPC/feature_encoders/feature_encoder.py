import pandas as pd 
from typing import List

class FeatureEncoder:
    """
    Base class for feature encoders.
    """

    def encode_dataframe(self, df: pd.DataFrame) -> List:
        """
        Encodes the entire DataFrame.
        
        :param df: DataFrame containing job data.
        :return: List of encoded features.
        """
        pass
    
    def encode_job(self, x: list) -> list:
        """
        Encodes the job data.
        
        :param x: List of job data.
        :return: List of encoded features.
        """
        pass
    