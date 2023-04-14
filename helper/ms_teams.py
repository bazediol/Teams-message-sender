import json
import requests


def get_token(refresh_token):
    url = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
    payload = \
        'grant_type=refresh_token&' + \
        'refresh_token=' + f'{refresh_token}&' + \
        'redirect_uri=https%3A%2F%2Flogin.microsoftonline.com%2Fcommon%2Foauth2%2Fnativeclient&' + \
        'client_id=219c5844-32c4-4b60-a1b3-7cad9b1cd9ca'
    request = requests.post(url, data=payload)
    return request.json()['access_token']


def post_message_in_channel(team_id, channel_id, message, refresh_token):
    url = f'https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages'
    headers = {
        "Authorization": "Bearer " + get_token(refresh_token),
        "Content-Type": "application/json"
    }
    payload = {
        "body": {
            "contentType": "html",
            "content": message
        }
    }
    requests.post(url, headers=headers, data=json.dumps(payload))
    return 0


def post_message_in_chat(chat_id, message, refresh_token):
    url = f'https://graph.microsoft.com/v1.0/chats/{chat_id}/messages'
    headers = {
      "Authorization": "Bearer " + get_token(refresh_token),
      "Content-Type": "application/json"
    }
    payload = {
        "body": {
          "contentType": "html",
          "content": message
        }
    }
    requests.post(url, headers=headers, data=json.dumps(payload))
    return 0
