# -*- coding: utf-8 -*-
# This script contains the main source code, which is executed by Python's interpretator for a Flask app.
# This is an API implementation code.
# PEP 8 formatting is kept.
# Last update: 28.08.2019
# -------------------------------------------------------------------------------------------------------
# Import modules needed.
from flask import Flask, jsonify
from flask import make_response
from flask import request
from insta_scrape import loginning, profile_data, get_direct_messages

# Create a Flask (WSGI) application as an instance of Flask class.
app = Flask(__name__)  # __name__ says Flask, that we need to look for additional files (i.e. templates folder).
api = loginning()  # Log in to Instagram profile.


# This function is used to return JSON dictionary in case of an error. It's called by other functions.
def error_respond(issue, code):
    return make_response(jsonify({'error': issue, 'code': code}), code)


# This function activates, when a user tries to get to an unexisting page. It handles 404 server error.
@app.errorhandler(404)
def not_found(error):
    return error_respond('Page not found. Wrong URL', 404)


@app.errorhandler(500)
def server_error(error):
    return error_respond("Error occurred from the server's side", 500)


# @app.route() connects URL address (parameter) and function. When you go to this URL, Flask calls the function.
@app.route('/api/v1.0/users')
def get_user_data():
    # Check if a username was provided as part of the URL.
    if 'username' not in request.args:
        return error_respond('No username parameter provided. Please specify a username', 400)

    username = str(request.args['username'])
    user_data = profile_data(api, username)
    if type(user_data) is str:  # It means that we received a string with an error.
        return error_respond(user_data, 400)

    return jsonify(user_data)


# This function works with direct messags. It takes creds and interlocutor's name. Returns json with all the messages.
@app.route('/api/v1.0/messages')
def direct_messages():
    parameters = ['login', 'password', 'user']
    # Check if all the arguments were provided as a part of the URL. Declare all the params needed.
    for param in parameters:
        if param not in request.args:
            return error_respond('No {0} parameter provided. Please specify a {0}'.format(param), 400)
    login = str(request.args['login'])
    password = str(request.args['password'])
    user = str(request.args['user'])

    respond = get_direct_messages(user, login, password)
    if type(respond) == str:   # It means that we received a string with an error.
        return error_respond(respond, 400)

    return jsonify(respond)


if __name__ == '__main__':
    app.config['JSON_AS_ASCII'] = False  # To show correctly cyrillic symbols.
    app.run(debug=False, host='0.0.0.0')
