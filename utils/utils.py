import pickle
import time
import numpy as np
import pandas as pd
import warnings
import uuid
import os
import jwt
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')

import json

def format_json(json_obj):
    formatted_str = json.dumps(json_obj, indent=4)
    return formatted_str

def loadpickles(filename):
    with open(filename, 'rb') as f:
        model = pickle.load(f)
    return model


def create_refresh_token(user_id):
    refresh_token_payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=10)  # Refresh token expires in 10 days
    }
    refresh_token = jwt.encode(refresh_token_payload, app.config['SECRET_KEY'], algorithm='HS256')
    return refresh_token

def getSeason():
    month = time.strftime("%m")
    seasons = {'WET     ': ['6','7', '8', '9', '10','11'],
               'DRY     ': ['12', '1', '2','3', '4','5']
    }
    season = ""
    for key, value in seasons.items():
        for val in value:
            if(val == str(int(month))):
                season = key
                break
    return season

