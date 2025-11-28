from sklearn.neighbors import KNeighborsClassifier

class KNN:
    
    name = "KNN"
    
    def __init__(self, k, **kwargs):
        self._model =  KNeighborsClassifier(n_neighbors=k, **kwargs)
    
    def train(self, x: list, y: list) -> bool:
        try:
            self._model = self._model.fit(x, y)
        except Exception as e:
            print(e)
            return False 
        else:
            return True
    
    def predict(self, x: list) -> list:
        try:
            return self._model.predict(x)
        except Exception as e:
            print(e)
            return []