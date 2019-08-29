# -*- coding: utf-8 -*-
# This script is a part of a bigger API script. It's connected with app.py script.
# It is needed to log into a separate Instagram API and get profiles' data.
# You can change login and password in creds.py file, which is located in the same folder.
# PEP 8 formatting is kept.
# Last update: 28.08.2019.
# ----------------------------------------------------------------------------------------
# Import libraries amd modules needed.
import creds
import time
import json
import re
import requests

from InstagramAPI import InstagramAPI
from bs4 import BeautifulSoup

# Fields we don't want to be shown in a response.
INVALID_FIELDS = [
    'external_lynx_url',
    'is_favorite',
    'has_chaining',
    'hd_profile_pic_versions',
    'mutual_followers_count',
    'profile_context',
    'profile_context_links_with_user_ids',
    'should_show_category',
    'should_show_public_contacts'
]
USER_AGENT = 'Mozilla/5.0 (Linux; Android 4.4.2; Nexus 4 Build/KOT49H) AppleWebKit/537.36 (KHTML, like Gecko) ' \
             'Chrome/34.0.1847.114 Mobile Safari/537.36'
BASE_URL = 'https://www.instagram.com/accounts/login/'
LOGIN_URL = BASE_URL + 'ajax/'
MAX_MESSAGES = 5000  # How many maximal messages should be returned.
MAX_DIALOGS = 2000  # How many maximal last conversations should be checked to find the one needed.


# Exclude unneeded keys from a dictionary.
def without_keys(d, keys):
    return {x: d[x] for x in d if x not in keys}


# Returns a substring between 2 elements in a string.
def between_markers(text: str, begin: str, end: str) -> str:
    start = text.find(begin) + len(begin) if begin in text else None
    stop = text[start:].find(end) if end in text else None
    return text[start:start+stop]


# Login to the account. We do it only once, when the API launches. This function returns api object.
def loginning() -> object:
    login = creds.login
    password = creds.password

    # Initializing process.
    api = InstagramAPI(login, password)  # Put our username and password into an API object.
    api.login()
    if api.LastResponse.status_code == 400:  # If an error occurs while loginning, the program will be finished.
        print(api.LastJson)
        time.sleep(5)
        exit(2)

    return api


# This function receives Instagram's username and logged in api object. It returns profile's data in a Python dict.
def profile_data(api, username: str):
    # Receiving data needed for a username.
    api.searchUsername(username)
    response = api.LastJson

    # Error processing
    if response['status'] == 'fail':
        if response['message'] == 'User not found':
            response = 'Username not found. Please, check the spelling.'
        else:
            response = 'Unknown error occurred. Try again later.'
    else:
        response = response['user']
        response = without_keys(response, INVALID_FIELDS)

    return response


# This function receives username, login, password and returns final json with all the messages.
def get_direct_messages(username, login, password):
    # Create Session object from requests library and add some parameters in its header.
    session = requests.Session()
    session.headers = {'user-agent': USER_AGENT}
    session.headers.update({'Referer': BASE_URL})

    # Get parts of source of a page.
    response = session.get(BASE_URL)
    page = BeautifulSoup(response.content, 'html.parser')  # html source code.
    body = page.find('body')  # <body> element source code.

    # Take script with data needed.
    pattern = re.compile('window._sharedData')
    script = body.find("script", text=pattern)
    script = script.get_text().replace('window._sharedData = ', '')[:-1]
    data = json.loads(script)

    # Send special parameters and loggining to Instagram.
    login_data = {'username': login, 'password': password}
    csrf = data['config'].get('csrf_token')
    session.headers.update({'X-CSRFToken': csrf})
    session.post(LOGIN_URL, data=login_data, allow_redirects=True)

    # Receive all the dialogs (usernames + id).
    raw_dialogs = session.get('https://www.instagram.com/direct_v2/web/inbox/?limit={0}'.format(MAX_DIALOGS))
    if 'no-js not-logged-in' in str(raw_dialogs.content):
        return 'Wrong credentials. Please, write correct login and password'
    dialogs = {}
    conversations = json.loads(raw_dialogs.content.decode('utf-8'))['inbox']['threads']
    # Fill dictionary with keys as username and values with conversations' ids.
    for i in range(len(conversations)):
        name = conversations[i]['thread_title']
        user_id = conversations[i]['thread_id']
        dialogs[name] = user_id
    if username not in dialogs:
        return 'No user found in your conversations list, please enter correct username'
    me = json.loads(raw_dialogs.content.decode('utf-8'))['viewer']['username']  # Username of an API's client.
    me_id = json.loads(raw_dialogs.content.decode('utf-8'))['viewer']['pk']  # ID of an API's client.

    # Receive raw json file with all the messages from the conversation with the username needed.
    thread_resp = session.get(
        'https://www.instagram.com/direct_v2/web/threads/{0}/?limit={1}'.format(dialogs[username], MAX_MESSAGES))
    thread_resp = json.loads(thread_resp.content.decode('utf-8'))
    items = thread_resp['thread']['items']  # All the raw messages.
    # A list with all the usernames in the conversation.
    participants_list = [thread_resp['thread']['users'][idx]['username'] for idx
                         in range(len(thread_resp['thread']['users']))]
    participants_list.append(me)

    # Create dictionary with usernames and their IDs from the conversation.
    participants_keys = dict()
    participants_keys[me_id] = me
    for user in thread_resp['thread']['users']:
        participants_keys[user['pk']] = user['username']

    # Parse raw json with messages and create an appropriate response and final return.
    final_response = dict()
    final_response['users'] = participants_list
    final_response['message_number'] = len(items)
    final_response['messages'] = []

    # Process all the items (messages).
    for idx in range(len(items)):
        curr_type = items[idx]['item_type']
        if curr_type == 'text':
            sender = participants_keys[items[idx]['user_id']]
            mes_type = curr_type
            text = items[idx]['text']
            final_dict = {'sender': sender, 'type': mes_type, 'text': text}
            final_response['messages'].append(final_dict)
        elif curr_type == 'reel_share':
            sender = participants_keys[items[idx]['user_id']]
            mes_type = 'story_reply'
            text = items[idx]['reel_share']['text']
            subtype = items[idx]['reel_share']['type']
            final_dict = {'sender': sender, 'type': mes_type, 'subtype': subtype, 'text': text}
            final_response['messages'].append(final_dict)
        elif curr_type == 'media_share':
            sender = participants_keys[items[idx]['user_id']]
            mes_type = 'post_share'
            try:
                owner = items[idx]['media_share']['user']['username']
                source = 'https://www.instagram.com/p/' + items[idx]['media_share']['code']
            except:
                owner = items[idx]['direct_media_share']['media']['user']['username']
                source = 'https://www.instagram.com/p/' + items[idx]['direct_media_share']['media']['code']
            final_dict = {'sender': sender, 'type': mes_type, 'owner': owner, 'source': source}
            final_response['messages'].append(final_dict)
        elif curr_type == 'story_share':
            sender = participants_keys[items[idx]['user_id']]
            mes_type = curr_type
            if items[idx]['story_share'].get('message') and \
                    items[idx]['story_share']['message'] == 'No longer available':
                owner = items[idx]['story_share']['title'][6:-8]
            elif items[idx]['story_share'].get('message') and 'This story is hid' \
                    in items[idx]['story_share']['message']:
                owner = between_markers(items[idx]['story_share']['message'], 'n because ', ' has a p')
            elif items[idx]['story_share'].get('message') and \
                    items[idx]['story_share']['message'] == 'This story is unavailable':
                owner = 'Unknown'
            else:
                owner = items[idx]['story_share']['media']['user']['username']
            final_dict = {'sender': sender, 'type': mes_type, 'owner': owner}
            final_response['messages'].append(final_dict)
        elif curr_type == 'voice_media':
            sender = participants_keys[items[idx]['user_id']]
            mes_type = curr_type
            source = items[idx]['voice_media']['media']['audio']['audio_src']
            if len(str(items[idx]['voice_media']['media']['audio']['duration'])) == 5:
                duration = str(items[idx]['voice_media']['media']['audio']['duration'])[:2]
            else:
                duration = str(items[idx]['voice_media']['media']['audio']['duration'])[:1]
            final_dict = {'sender': sender, 'type': mes_type, 'source': source, 'duration': duration}
            final_response['messages'].append(final_dict)
        elif curr_type == 'raven_media':
            sender = participants_keys[items[idx]['user_id']]
            mes_type = 'media_sent'
            if items[idx]['raven_media']['media_type'] == 2:
                subtype = 'Video'
            else:
                subtype = 'Picture'
            view_mode = items[idx]['view_mode']
            final_dict = {'sender': sender, 'type': mes_type, 'subtype': subtype, 'view_mode': view_mode}
            if items[idx]['view_mode'] == 'permanent':
                if items[idx]['raven_media']['media_type'] == 1:
                    source = items[idx]['raven_media']['image_versions2']['candidates'][0]['url']
                    final_dict['source'] = source
                else:
                    source = items[idx]['raven_media']['video_versions'][0]['url']
                    final_dict['source'] = source
            final_response['messages'].append(final_dict)
        elif curr_type == 'media':
            sender = participants_keys[items[idx]['user_id']]
            mes_type = curr_type
            if items[idx]['media']['media_type'] == 2:
                subtype = 'Video'
                source = items[idx]['media']['video_versions'][0]['url']
            else:
                subtype = 'Picture'
                source = items[idx]['media']['image_versions2']['candidates'][0]['url']
            final_dict = {'sender': sender, 'type': mes_type, 'subtype': subtype, 'source': source}
            final_response['messages'].append(final_dict)
        elif curr_type == 'placeholder':
            sender = participants_keys[items[idx]['user_id']]
            mes_type = 'deleted_post'
            final_dict = {'sender': sender, 'type': mes_type}
            final_response['messages'].append(final_dict)
        elif curr_type == 'profile':
            sender = participants_keys[items[idx]['user_id']]
            mes_type = curr_type
            username = items[idx]['profile']['username']
            final_dict = {'sender': sender, 'type': mes_type, 'username': username}
            final_response['messages'].append(final_dict)
        else:
            final_dict = {'type': 'unknown_type'}
            final_response['messages'].append(final_dict)

    return final_response
