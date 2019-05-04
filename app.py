import os
import pandas as pd
import requests

from flask import Flask, request, jsonify
from df_response_lib import telegram_response, fulfillment_response
from tensorflow.python.lib.io.file_io import FileIO
from pprint import pprint
from google.cloud import storage

telegram = telegram_response()
message_text = fulfillment_response()

BUCKET_NAME = "jarvis-transactions"
DATABASES = {}

app = Flask(__name__)

def exists_in_gcp(filename):   
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    stats = storage.Blob(bucket=bucket, name=filename).exists(storage_client)
    return stats

def get_user_info(req):
    return req['originalDetectIntentRequest']['payload']['data']['message']['chat']

def get_user_firstname(req):
    return get_user_info(req)['first_name']

def get_username(req):
    return get_user_info(req)['username']

def is_database_created(username):
    filename = "{}.csv".format(username)
    file_exists = exists_in_gcp(filename)
    if file_exists:
        with FileIO(os.path.join("gs://", BUCKET_NAME, filename), 'r') as f:
            DATABASES[username] = pd.read_csv(f)
    else:
        DATABASES[username] = pd.DataFrame(columns=["username", "date", "cause", "spent"])
        with FileIO(os.path.join("gs://", BUCKET_NAME, filename), 'w') as f:
            DATABASES[username].to_csv(f)
    return not file_exists

def welcome_intent(req):
    name = get_user_firstname(req)
    username = get_username(req)
    was_created = is_database_created(username)
    if was_created:
        part_message = "Eres nuevo! Bienvenido {}, soy el servicio de ayuda financiera Jarvis".format(name) 
    else:
        part_message = "Bienvenido de nuevo {}".format(name)
    
    message = "{} ¿En que te puedo ayudar?".format(part_message)

    possibilities = ["Crédito de vivienda", "Crédito de carro", 'Crédito de estudios']

    return (None, 
    message_text.fulfillment_messages([telegram.quick_replies(message, [possibilities])]), 
    None, 
    None)

def get_credit(req):
    kind = req['queryResult']['outputContexts'][0]['parameters']['CreditTypes']
    print(kind)
    requests.get('https://grupo3-hckton-1.appspot.com/activate_product/reset_products')
    requests.get('https://grupo3-hckton-1.appspot.com/activate_product/:{}'.format(kind.lower()))
    return None, None, None, None

def check_best_rate(reg):
    rates = requests.get('https://grupo3-hckton-1.appspot.com/tasas').json()
    best = min(rates, key=lambda val: min(val['tasaVariable'], val['tasaFija']))
    best_rate, best_type = (best['tasaVariable'], 'tasa variable') if best['tasaVariable'] < best['tasaFija'] else (best['tasa fija'], 'tasa fija')
    best_entity = best['entidad']
    message = "Ahorita mismo {} está ofreciendo un {}% de {}.".format(best_entity, best_rate, best_type)
    return message_text.fulfillment_text(message), None, None, None

actions_map = {
    'WelcomeIntent': welcome_intent,
    'Rate1': check_best_rate,
    'AskCredit': get_credit
}

def results():
    req = request.get_json(force=True)
    action = actions_map[req['queryResult']['intent']['displayName']]
    return action(req)

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    fulfillment_text, fulfillment_messages, output_contexts, followup_event_input = results()
    return jsonify(
        message_text.main_response(
            fulfillment_text=fulfillment_text, 
            fulfillment_messages=fulfillment_messages, 
            output_contexts=output_contexts, 
            followup_event_input=followup_event_input
            )
        )

if __name__ == "__main__":
    app.run(debug=True)