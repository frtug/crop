import json
from flask import Flask, request, Response, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
import uuid
from numpy.core.numeric import full
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta
from functools import wraps
import numpy as np
import pandas as pd
from flask_cors import CORS, cross_origin
from api import weatherApi
from utils import utils
from dotenv import load_dotenv
import os
# from googleapiclient.discovery import build
# from google.oauth2 import service_account
from scheduledEmail import schedule_send_email

load_dotenv()

database_key = os.getenv('DATABASE_KEY')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_host = os.getenv('DB_HOST')
db_port = int(os.getenv('DB_PORT'))
db_name = os.getenv('DB_NAME')

db_connection_string = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

app = Flask(__name__)
app.config['SECRET_KEY'] = '0123456789'
app.config['SQLALCHEMY_DATABASE_URI'] = db_connection_string

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)
CORS(app, support_credentials=True)

load_dotenv()
def create_refresh_token(user_id):
    refresh_token_payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=10)  # Refresh token expires in 10 days
    }
    refresh_token = jwt.encode(refresh_token_payload, app.config['SECRET_KEY'], algorithm='HS256')
    return refresh_token 

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(50), unique=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(256))
    full_name = db.Column(db.String(80))
    state_name = db.Column(db.String(50))
    district_name = db.Column(db.String(50))
    area = db.Column(db.Integer)
    soil_type = db.Column(db.String(60))
    mobile = db.Column(db.String(60))


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
            print(token)
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            print(data)
            current_user = User.query.filter_by(public_id=data['public_id']).first()
            print(current_user.username)
        except jwt.exceptions.ExpiredSignatureError:
            return make_response(jsonify({"message": "Refresh token has expired"}), 401)
        except jwt.InvalidTokenError:
            return make_response(jsonify({"message": "Invalid refresh token"}), 401)
        except Exception as e:
            return make_response(jsonify({"message": "Token is invalid"}), 401)

        # except Exception as e:
        #         current_user = None
        #         print(str(e))
        # except:
        #     data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        #     print(data)
        #     return jsonify({
        #         'message': 'Token is invalid'
        #     }), 401
        return f(current_user, *args, **kwargs)

    return decorated

@app.route('/api', methods=['GET'])
def getHeathCheck():
    return ({"msg":"Server is up and running '/'"})


@app.route('/api/user', methods=['GET'])
@token_required
def getUserProfile(current_user):
    return make_response(
        jsonify({"username": current_user.username, "password": current_user.password, "full_name": current_user.full_name, "state_name": current_user.state_name, "district_name": current_user.district_name, "area": current_user.area, "soil_type": current_user.soil_type, "mobile": current_user.mobile}),
        200,
        {'WWW-Authenticate': 'Basic realm ="User Fetched"'}
    )




@app.route('/api/user/update', methods=['PUT'])
@token_required
def updateUserProfile(current_user):
    updateUser = request.json
    user = User.query.filter_by(id=current_user.id).first()
    userUsername = User.query.filter_by(
        username=updateUser.get('username')).first()
    if current_user.username != updateUser.get('username'):
        if not userUsername:
            user.username = updateUser.get('username')
        else:
            return make_response(jsonify({"message": "Username already taken."}), 400)
    user.full_name = updateUser.get('full_name')
    user.state_name = updateUser.get('state_name')
    user.district_name = updateUser.get('district_name')
    user.area = updateUser.get('area')
    user.soil_type = updateUser.get('soil_type')
    user.mobile = updateUser.get('mobile')
    db.session.commit()
    return jsonify({"message": "User Profile updated successfully"})

@app.route('/api/refresh', methods=['POST'])
def refresh_token():
    refresh_token = request.json.get('refresh_token')

    try:
        refresh_token_payload = jwt.decode(refresh_token, app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = refresh_token_payload['user_id']
    except jwt.ExpiredSignatureError:
        return make_response(jsonify({"message": "Refresh token has expired"}), 401)
    except jwt.InvalidTokenError:
        return make_response(jsonify({"message": "Invalid refresh token"}), 401)

    # Check if the user still exists in the database (optional)
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return make_response(jsonify({"message": "User not found"}), 404)

    # Generate a new access token
    access_token = jwt.encode({
        'public_id': user.public_id,
        'exp': datetime.utcnow() + timedelta(minutes=30)  # New access token expires in 30 minutes
    }, app.config['SECRET_KEY'], algorithm='HS256')

    return jsonify({"access_token": access_token}), 200

@app.route('/api/login', methods=['POST'])
def login():
    auth = request.json

    if not auth or not auth.get('username') or not auth.get('password'):
        return make_response(
            jsonify({"message": "Could not verify"}),
            401,
            {'WWW-Authenticate': 'Basic realm ="Login required"'}
        )

    user = User.query.filter_by(username=auth.get('username')).first()

    if not user:
        return make_response(
            jsonify({"message": "Username doesn't exist"}),
            401,
            {'WWW-Authenticate': 'Basic realm ="User does not exist !!"'}
        )

    if check_password_hash(user.password, auth.get('password')):
        token = jwt.encode({
            'public_id': user.public_id,
            'exp': datetime.utcnow() + timedelta(minutes=30)
        }, app.config['SECRET_KEY'])
        refresh_token = create_refresh_token(user.id)
        return make_response(jsonify({"message": "Login Sucessful", 'token': str(token),'refresh_token':str(refresh_token)}), 201)
    return make_response(
        jsonify({"message": "Wrong username or password"}),
        403,
        {'WWW-Authenticate': 'Basic realm ="Wrong Password !!"'}
    )

@app.route('/api/scheduler',methods=['POST'])
@token_required
def scheduler(current_user):
    data = request.json
    cropInfo = data.get('data')
    date = data.get('date')
    recipient_email = data.get('email')
    
    try:
        schedule_send_email(cropInfo,recipient_email,date)
        return make_response(jsonify({"success": True, "message": f"Sucessfully Send Email"}), 201)

    except Exception as e:
        print('An error occurred while sending the email:', str(e))
        return make_response(jsonify({"success": False, "message": f"Failed to Set Scheduled on {date}"}), 401)




@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json

    username = data.get('username')
    password = data.get('password')
    full_name = data.get('full_name')

    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(
            public_id=str(uuid.uuid4()),
            username=username,
            password=generate_password_hash(password),
            full_name=full_name
        )
        db.session.add(user)
        db.session.commit()

        return make_response(jsonify({"success": True, "message": "Sucessfully Registered"}), 201)
    else:
        return make_response(jsonify({"success": False, "message": 'User already exists. Please Log in'}), 202)


@app.route("/api/A1/recommendCrop", methods=['GET'])
@token_required
def recommendCrop1(current_user):
    district = request.args.get("district")
    weather = np.array(weatherApi.getWeather(district)).reshape(1, -1)
    cropRecommendationApproach1 = utils.loadpickles(
        "pickledFiles/cropRecommendationA1.pkl")
    print(weather)
    crop = cropRecommendationApproach1.predict(X=weather)
    return jsonify({"crop": crop[0]})


@app.route("/api/A1/recommendNPK", methods=['POST'])
@token_required
def recommendNPK(current_user):
    NPKPrediction = pd.read_csv(
        "./preprocessedData/CropRecommentationApproach2.csv")
    NPKPrediction = NPKPrediction[NPKPrediction['N'] > 0 &
                                  NPKPrediction['P'] & NPKPrediction['K']].reset_index(drop=True)
    category = list(dict(
        enumerate(NPKPrediction['label'].astype('category').cat.categories)).values())

    data = request.json
    crop = category.index(data.get("crop").title())

    district = request.args.get("district")
    weather = weatherApi.getWeather(district)
    nitrogen = utils.loadpickles(
        "pickledFiles/predictNitrogen.pkl")
    nitrogen_input = np.array([*weather, crop]).reshape(1, -1)
    nitrogen_level = nitrogen.predict(nitrogen_input)
    print(nitrogen_input)
    phosphorus = utils.loadpickles(
        "pickledFiles/predictPhosphorus.pkl")
    phosphorus_input = np.array([*weather, crop]).reshape(1, -1)
    phosphorus_level = phosphorus.predict(phosphorus_input)

    potassium = utils.loadpickles(
        "pickledFiles/predictPotassium.pkl")
    potassium_input = np.array([*weather, crop]).reshape(1, -1)
    potassium_level = potassium.predict(potassium_input)

    return jsonify({"nitrogen": nitrogen_level[0], "phosphorus": phosphorus_level[0], "potassium": potassium_level[0]})


@app.route("/api/A1/recommendFertilizer", methods=['POST'])
@token_required
def recommendFertilizer(current_user):
    data = request.json

    NPKPrediction = pd.read_csv(
        "./data/FertilizerPrediction.csv")
    crop_category = list(dict(
        enumerate(NPKPrediction['Crop Type'].astype('category').cat.categories)).values())
    soil_category = list(dict(
        enumerate(NPKPrediction['Soil Type'].astype('category').cat.categories)).values())
    fertilizer_category = dict(
        enumerate(NPKPrediction['Fertilizer'].astype('category').cat.categories))

    soil = soil_category.index(data.get('soil'))
    crop = crop_category.index(data.get('crop'))
    nitrogen = data.get('nitrogen')
    potassium = data.get('potassium')
    phosphorus = data.get('phosphorus')

    district = request.args.get("district")
    weather = weatherApi.getWeather(district)[:2]
    print(weather)
    fertilizerRecommendation = utils.loadpickles(
        "pickledFiles/fertilizerRecommendation.pkl")
    fertilizer_input = np.array(
        [*weather,  soil, crop, nitrogen, potassium, phosphorus]).reshape(1, -1)
    fertilizer = fertilizerRecommendation.predict(fertilizer_input)
    fertilizer = fertilizer_category[fertilizer[0]]
    return jsonify({"fertilizer": fertilizer})


@app.route("/api/A2/recommendCrop", methods=['POST'])
@token_required
def recommendCrop2(current_user):
    data = request.json

    nitrogen = data.get('nitrogen')
    phosphorus = data.get('phosphorus')
    potassium = data.get('potassium')

    district = request.args.get("district")
    weather = weatherApi.getWeather(district)
    cropRecommendationApproach2 = utils.loadpickles(
        "pickledFiles/cropRecommendationA2.pkl")
    crop_input = np.array(
        [nitrogen, phosphorus, potassium, *weather]).reshape(1, -1)
    crop = cropRecommendationApproach2.predict(crop_input)
    return jsonify({"crop": crop[0]})


@app.route("/api/recommendCropYield", methods=['POST'])
@token_required
def recommendCropYield(current_user):
    data = request.json
    crop = data.get('crop')
    area = data.get('area')

    CropProduction = pd.read_csv(
        "./data/CropProductionMinified.csv")
    CropProduction = CropProduction[CropProduction['Production'] > 0].reset_index(
        drop=True)

    crop_category = list(dict(
        enumerate(CropProduction['Crop'].astype('category').cat.categories)).values())
    crop = crop_category.index(crop) 

    args = request.args
    state = args.get("state") # state -> Muncipality
    district = args.get("district").title() #district -> Province
    season = args.get("season").upper()
    season = season if season else utils.getSeason()

    state_category = list(dict(
        enumerate(CropProduction['State_Name'].astype('category').cat.categories)).values())
    district_category = list(dict(
        enumerate(CropProduction['District_Name'].astype('category').cat.categories)).values())
    season_category = ['DRY','WET']

    state = state_category.index(state)
    district = district_category.index(district)
    season = season_category.index(season)
    print(season)

    cropProduction = utils.loadpickles(
        "pickledFiles/cropProduction.pkl")
    yield_input = np.array(
        [state, district, season, crop, area]).reshape(1, -1)

    cropProductionScaler = utils.loadpickles(
        "pickledFiles/cropProductionScaler.sav")
    yield_input_scaler = cropProductionScaler.transform(yield_input)
    crop_yield = cropProduction.predict(yield_input_scaler)
    return jsonify({"yield": crop_yield[0]})


@app.route("/api/weedDetection", methods=['POST'])
def weedDetection():
    data = request.json
    imageURI = data.get('imageURI')
    pred_output = utils.detection(imageURI)
    pred_output = list(map(utils.convertToList, pred_output))
    return Response(json.dumps(pred_output),  mimetype='application/json')


@app.route("/api/states", methods=['GET'])
@token_required
def getStates(current_user):
    CropProduction = pd.read_csv(
        "./data/CropProductionMinified.csv")
    CropProduction = CropProduction[CropProduction['Production'] > 0].reset_index(
        drop=True)

    state_category = dict(
        enumerate(CropProduction['State_Name'].astype('category').cat.categories))
    return jsonify(state_category)


@app.route("/api/districts", methods=['GET'])
@token_required
def getDistricts(current_user):
    args = request.args
    state = args.get("state_name")
    print(state)
    CropProduction = pd.read_csv(
        "./data/CropProductionMinified.csv")
    CropProduction = CropProduction[CropProduction['Production'] > 0].reset_index(
        drop=True)

    district_category = dict(
        enumerate(CropProduction[CropProduction['State_Name'] == state]['District_Name'].astype('category').cat.categories))
    return jsonify(district_category)


@app.route("/api/crops", methods=['GET'])
def getCrops():
    CropProduction = pd.read_csv(
        "./data/CropProductionMinified.csv")
    CropProduction = CropProduction[CropProduction['Production'] > 0].reset_index(
        drop=True)

    crops_category = dict(
        enumerate(CropProduction['Crop'].astype('category').cat.categories))
    return jsonify(crops_category)


@app.route("/api/seasons", methods=['GET'])
@token_required
def getSeasons(current_user):
    CropProduction = pd.read_csv(
        "./data/CropProductionMinified.csv")
    CropProduction = CropProduction[CropProduction['Production'] > 0].reset_index(
        drop=True)

    season_category = dict(
        enumerate(CropProduction['Season'].astype('category').cat.categories))
    return jsonify(season_category)


@app.route("/api/soils", methods=['GET'])
@token_required
def getSoils(current_user):
    FertilizerPrediction = pd.read_csv(
        "./data/FertilizerPrediction.csv")
    soil_category = dict(
        enumerate(FertilizerPrediction['Soil Type'].astype('category').cat.categories))
    return jsonify(soil_category)


@app.route("/api/weather", methods=['GET'])
@token_required
def getWeather(current_user):
    args = request.args
    district = args.get("district_name")
    weather = np.array(weatherApi.getWeather(district))
    return jsonify({"temperature": weather[0], "humidity": weather[1], "rainfall": weather[2]})


@app.route("/api/getSeasonbyMonth", methods=['GET'])
@token_required
def getSeasonbyMonth(current_user):
    season = utils.getSeason()
    return jsonify(season)


if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0')
