from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def home():
        return "Hello OMMAE!"

@app.route('/generate-video')
def generate():
        # fake pipeline
        return {"videoId": "fake-001", "url": "https://drive.google.com/fake"}

if __name__ == '__main__':
        port = int(os.getenv('PORT', 8080))
        app.run(host='0.0.0.0', port=port)
