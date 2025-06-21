from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Hello! I'm alive!"

def run():
    app.run(host='0.0.0.0', port=8080) # Hoặc port 10000 hoặc port mà Render yêu cầu

def keep_alive():
    t = Thread(target=run)
    t.start()
