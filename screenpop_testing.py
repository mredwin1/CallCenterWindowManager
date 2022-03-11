import asyncio
import requests
import win32gui
import tkinter as tk
import json
import websockets
import re
import win32com.client

from google_auth_oauthlib.flow import InstalledAppFlow

CALLER_INFO_WINDOW_NAME = 'Caller Information'
CALLER_INFO_WINDOW_WIDTH = 300
CALLER_INFO_WINDOW_HEIGHT = 500


class App(tk.Tk):
    def __init__(self, loop, interval=0.05):
        super().__init__()
        self.loop = loop
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.tasks = []
        self.tasks.append(loop.create_task(self.call_handler()))
        self.tasks.append(loop.create_task(self.updater(interval)))
        self.google_chrome_hwnd = None
        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.winfo_screenheight()

        x = self.screen_width - CALLER_INFO_WINDOW_WIDTH
        y = 0

        self.geometry('%dx%d+%d+%d' % (CALLER_INFO_WINDOW_WIDTH, CALLER_INFO_WINDOW_HEIGHT, x, y))

        self.title(CALLER_INFO_WINDOW_NAME)
        self.frame = tk.Frame(self, width=CALLER_INFO_WINDOW_WIDTH, height=CALLER_INFO_WINDOW_HEIGHT)
        self.text_box = tk.Text(self)
        self.text_box.insert(tk.END, 'Waiting for call...')

        self.frame.pack()
        self.text_box.place(x=0, y=0, width=CALLER_INFO_WINDOW_WIDTH, height=CALLER_INFO_WINDOW_HEIGHT)

        self.ringing_windows = [
            [['Caller Information'], self.screen_width - CALLER_INFO_WINDOW_WIDTH, 0, CALLER_INFO_WINDOW_WIDTH,
             CALLER_INFO_WINDOW_HEIGHT, True]
        ]

        self.answered_windows = [
            [[CALLER_INFO_WINDOW_NAME], self.screen_width - CALLER_INFO_WINDOW_WIDTH, 0, CALLER_INFO_WINDOW_WIDTH,
             CALLER_INFO_WINDOW_HEIGHT, True],
            [['LOCRA1.mvbachman.pri', 'Workstation'], 0, 0, self.screen_width - CALLER_INFO_WINDOW_WIDTH,
             self.screen_height, True]
        ]

    def connect_goto(self):
        flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', scopes=['users.v1.lines.read'])
        InstalledAppFlow.redirect_uri = 'http://127.0.0.1:8080'  # Need to do this so the redirect uri is not urlencoded in the url

        flow.run_local_server(host='localhost', port=8080, prompt='consent')

        goto_credentials = json.loads(flow.credentials.to_json())

        session_url = 'https://realtime.jive.com/v2/session'
        line_url = 'https://api.jive.com/users/v1/lines'
        headers = {
            'Authorization': f'Bearer {goto_credentials["token"]}'
        }
        subscription_headers = headers
        subscription_headers['Content-Type'] = 'application/json'

        line_response = requests.get(line_url, headers=headers).json()['items']
        self.session_response = requests.post(session_url, headers=headers).json()

        subscription_data = [{
            'id': 'linesubscription',
            'type': 'dialog',
            'entity': {
                'account': line_response[0]['organization']['id'],
                'type': 'line.v2',
                'id': line_response[0]['id']
            }
        }]
        subscription_response = requests.post(self.session_response['subscriptions'], headers=subscription_headers,
                                              data=json.dumps(subscription_data))

    @staticmethod
    def move_handler(hwnd, ctx):
        search_criteria, x, y, width, height, redraw = ctx
        if win32gui.IsWindow(hwnd) and win32gui.IsWindowEnabled(hwnd) and win32gui.IsWindowVisible(hwnd):
            pattern = re.compile(r' | '.join(search_criteria), flags=re.I | re.X)
            words_found = set(pattern.findall(win32gui.GetWindowText(hwnd)))
            if len(search_criteria) == 1 and search_criteria[0] in win32gui.GetWindowText(hwnd):
                shell = win32com.client.Dispatch("WScript.Shell")
                shell.SendKeys('%')
                win32gui.SetForegroundWindow(hwnd)
                win32gui.ShowWindow(hwnd, True)
                win32gui.MoveWindow(hwnd, x - 7, y, width, height, redraw)
            elif 1 < len(search_criteria) == len(words_found):
                shell = win32com.client.Dispatch("WScript.Shell")
                shell.SendKeys('%')
                win32gui.SetForegroundWindow(hwnd)
                win32gui.ShowWindow(hwnd, True)
                win32gui.MoveWindow(hwnd, x - 7, y, width, height, redraw)

    async def move_windows(self, windows: list):
        for window in windows:
            context = window
            win32gui.EnumWindows(self.move_handler, context)

    async def call_handler(self):
        async with websockets.connect(self.session_response['ws']) as websocket:
            while True:
                response = await websocket.recv()
                message = json.loads(response)
                try:
                    message_type = message['type']
                    if message_type != 'keepalive':
                        data = message['data']
                        state = data['state']

                        print(state)
                        if state == 'ANSWERED':
                            self.text_box.delete("1.0", tk.END)
                            caller_name = data['caller']['name']
                            caller_number = data['caller']['number']
                            dialed_number = data['ani'].split(' ')[0]

                            message = f'\n**Call Answered**\nCaller Name: {caller_name}\nCaller Number: {caller_number}\nNumber Dialed: {dialed_number}'
                            self.text_box.insert(tk.END, message)

                            self.loop.create_task(self.move_windows(self.answered_windows))

                        elif state == 'RINGING':
                            self.text_box.delete("1.0", tk.END)
                            caller_name = data['caller']['name']
                            caller_number = data['caller']['number']
                            dialed_number = data['ani'].split(' ')[0]

                            message = f'\n**Call Incoming**\nCaller Name: {caller_name}\nCaller Number: {caller_number}\nNumber Dialed: {dialed_number}'
                            self.text_box.insert(tk.END, message)
                            self.loop.create_task(self.move_windows(self.ringing_windows))

                        elif state == 'HUNGUP':
                            self.text_box.delete("1.0", tk.END)
                            self.text_box.insert(tk.END, 'Waiting for call...')

                except KeyError:
                    print('Key error')

    async def updater(self, interval):
        while True:
            self.update()
            await asyncio.sleep(interval)

    def close(self):
        for task in self.tasks:
            task.cancel()
        self.loop.stop()
        self.destroy()


loop = asyncio.get_event_loop()
app = App(loop)
app.connect_goto()
loop.run_forever()
loop.close()
