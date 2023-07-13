import pickle
import time
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')


def loadpickles(filename):
    with open(filename, 'rb') as f:
        model = pickle.load(f)
    return model


def getSeason():
    month = time.strftime("%m")
    seasons = {'Wet     ': ['6','7', '8', '9', '10','11'],
               'Dry     ': ['12', '1', '2','3', '4','5']
    }
    season = ""
    for key, value in seasons.items():
        for val in value:
            if(val == str(int(month))):
                season = key
                break
    return season

