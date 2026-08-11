from flask import Flask
import threading

app = Flask("keepalive")


@app.route("/")
def index():
    return "OK", 200


def run(host="0.0.0.0", port=8080):
    # Run Flask in a thread-safe way; caller should start this in a Thread
    app.run(host=host, port=port)


def start_background(host="0.0.0.0", port=8080):
    thread = threading.Thread(target=run, kwargs={"host": host, "port": port}, daemon=True)
    thread.start()
    return thread
