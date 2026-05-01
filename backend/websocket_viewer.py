import websocket, json

def on_message(ws, msg):
    data = json.loads(msg)
    print(f"{data['type']:40} {json.dumps(data['payload'])}")

def on_error(ws, err):
    print('Error:', err)

def on_open(ws):
    print('Connected')

ws = websocket.WebSocketApp(
    'ws://localhost:5000/ws',
    on_message=on_message,
    on_error=on_error,
    on_open=on_open,
)
ws.run_forever()

