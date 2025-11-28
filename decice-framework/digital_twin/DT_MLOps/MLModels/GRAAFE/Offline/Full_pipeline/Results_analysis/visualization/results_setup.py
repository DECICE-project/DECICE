import os
import shutil

model = '../Training_and_validation_of_ML_models/results'
os.mkdir(model)

for fw in [4,6,12,24,32,64,96,192,288]:
    os.mkdir("../Training_and_validation_of_ML_models/{}/{}".format(model,fw))

shutil.copy("roc_avg.py", "../Training_and_validation_of_ML_models/{}/roc_avg.py".format(model))

