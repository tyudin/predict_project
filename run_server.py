import json
import dill
import pandas as pd
from logging.config import dictConfig
from flask import Flask, make_response, jsonify, request, abort, render_template, send_from_directory
from flask_cors import CORS

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(name)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

# read pipeline
with open('model/model.dill', 'rb') as f:
    MODEL = dill.load(f)

app = Flask(__name__)
cors = CORS(app)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
logger = app.logger


def validate(data: dict) -> tuple[bool, str]:
    """ Валидация полученного словаря """
    error_lst = []
    mask = ['age', 'hypertension', 'heart_disease', 'smoking_history', 'bmi', 'HbA1c_level', 'blood_glucose_level']

    # проверим наличие всех нужных ключей словаря
    if not all([x in data.keys() for x in mask]):
        return False, "В словаре отсутствуют необходимые ключи!"

    # проверим age
    if isinstance(data['age'], str) or data['age'] < 0 or data['age'] > 120:
        error_lst.append("[age] должен быть в интервале [0: 120] и числовым типом")

    # проверим hypertension
    if isinstance(data['hypertension'], str) or data['hypertension'] < 0 or data['hypertension'] > 1:
        error_lst.append("[hypertension] должен быть в интервале [0: 1] и числовым типом")

    # проверим heart_disease
    if isinstance(data['heart_disease'], str) or data['heart_disease'] < 0 or data['heart_disease'] > 1:
        error_lst.append("[heart_disease] должен быть в интервале [0: 1] и числовым типом")

    # проверим smoking_history
    if isinstance(data['smoking_history'], str) or data['smoking_history'] < -1 or data['smoking_history'] > 4:
        error_lst.append("[smoking_history] должен быть в интервале [-1: 4] и числовым типом")

    # проверим bmi
    if isinstance(data['bmi'], str) or data['bmi'] < 0 or data['bmi'] > 200:
        error_lst.append("[bmi] должен быть в интервале [0: 200] и числовым типом")

    # проверим HbA1c_level
    if isinstance(data['HbA1c_level'], str) or data['HbA1c_level'] < 0 or data['HbA1c_level'] > 50:
        error_lst.append("[HbA1c_level] должен быть в интервале [0: 50] и числовым типом")

    # проверим blood_glucose_level
    if isinstance(data['blood_glucose_level'], str) or data['blood_glucose_level'] < 0 or data['blood_glucose_level'] > 1000:
        error_lst.append("[blood_glucose_level] должен быть в интервале [0: 1000] и числовым типом")

    if len(error_lst) == 0:
        # ошибок нет
        return True, ""

    # ошибки есть
    return False, " ".join(error_lst)


def make_dataframe_from_data(data: str|dict) -> tuple[pd.DataFrame | None, str]:
    if isinstance(data, str):
        data_dict = json.loads(data)
    elif isinstance(data, dict):
        data_dict = data
    else:
        return None, "Unknown incoming data"
    
    isvalid, errors = validate(data_dict)
    if not isvalid:
        logger.error(errors)
        return None, errors

    df = pd.DataFrame(data_dict, index=[0])
    return df, ""


def classify_data(df: pd.DataFrame) -> pd.DataFrame:
    preds_proba = MODEL.predict_proba(df)[:, 1]
    preds = preds_proba > MODEL.my_thresholds_level
    df = pd.DataFrame({'predict': preds, 'predict_proba': preds_proba}, index=[0], dtype='float')
    return df


@app.route('/')
def index():
    return make_response(jsonify({'info': 'Hello from server!'}), 200)


@app.route('/static/<path:name>', methods=['GET'])
def send_static(name):
    return send_from_directory('static', name)


@app.route('/predict', methods=['GET'])
def predict_form():
    return make_response(render_template('predict.html', ), 200)


@app.route("/predict", methods=['POST'])
def predict():
    data_json = request.get_json(silent=True, force=True)
    logger.info(f"predict: data={data_json}")
    
    if not data_json:
        logger.error(f"Bad request: {request.data}")
        return make_response(jsonify({'error': 'JSON data incompatible!'}), 416)
    
    df, errors = make_dataframe_from_data(data_json)
    
    if df is None:
        return make_response(jsonify({'error': errors}), 416)

    result = classify_data(df)
    result_json = result.to_json(orient='records', lines=False)
    return make_response(jsonify({'predictions': result_json}), 200)


if __name__ == "__main__":
    app.run(debug=True)
    logger.info('Сервер остановлен')
