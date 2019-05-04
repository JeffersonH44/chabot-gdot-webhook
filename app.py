import os
import pandas as pd

from flask import Flask, request, jsonify
from df_response_lib import telegram_response, fulfillment_response
from pprint import pprint

telegram = telegram_response()
message = fulfillment_response()

app = Flask(__name__)

def get_user_info(req):
    return req['originalDetectIntentRequest']['payload']['data']['message']['chat']

def get_user_firstname(req):
    return get_user_info(req)['first_name']

def get_username(req):
    return get_user_info(req)['username']

def is_database_created(username):
    file_exists = os.path.isfile("./{}.csv".format(username))
    database = pd.DataFrame(columns=["username", "date", "cause", "spent"])
    
    database.to_csv()
    return not file_exists

def welcome_intent(req):
    name = get_user_firstname(req)
    pprint(req)
    message = "Hola {}, soy tu ayudante financiero! \n¿En que puedo ayudarlo?".format(name) 
    return message

def house_loan(req):
    name = get_user_firstname(req)
    message = "Claro que sí {}. Recuerda que Cuando solicitas un préstamo te estás comprometiendo a pagar no sólo el monto que solicitas sino también los intereses que te cobrará la entidad.".format(name)
    return message

actions_map = {
    'WelcomeIntent': welcome_intent,
    'HouseLoan': house_loan
}

def results():
    req = request.get_json(force=True)
    action = actions_map[req['queryResult']['intent']['displayName']]

    # return a fulfillment response
    return message.fulfillment_text(action(req))

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    print("hello")
    fulfillment_text = results()
    return jsonify(message.main_response(fulfillment_text))

if __name__ == "__main__":
    app.run(debug=True)