import asyncio
import json
import requests
import websockets

from google_auth_oauthlib.flow import InstalledAppFlow

if __name__ == "__main__":
    flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', scopes=['users.v1.lines.read'])
    InstalledAppFlow.redirect_uri = 'http://127.0.0.1:8080'  # Need to do this so the redirect uri is not urlencoded in the url

    flow.run_local_server(host='localhost', port=8080, prompt='consent')

    goto_credentials = json.loads(flow.credentials.to_json())

    subscription_url = ''
    session_url = 'https://realtime.jive.com/v2/session'
    line_url = 'https://api.jive.com/users/v1/lines'
    headers = {
        'Authorization': f'Bearer {goto_credentials["token"]}'
    }
    subscription_headers = headers
    subscription_headers['Content-Type'] = 'application/json'

    line_response = requests.get(line_url, headers=headers).json()['items']
    session_response = requests.post(session_url, headers=headers).json()

    subscription_data = [{
        'id': 'linesubscription',
        'type': 'dialog',
        'entity': {
            'account': line_response[0]['organization']['id'],
            'type': 'line.v2',
            'id': line_response[0]['id']
        }
    }]
    subscription_response = requests.post(session_response['subscriptions'], headers=subscription_headers, data=json.dumps(subscription_data))

    async def call_handler():
        async with websockets.connect(session_response['ws']) as websocket:
            while True:
                response = await websocket.recv()
                message = json.loads(response)
                print(message)

    asyncio.run(call_handler())
