from flask import Flask, jsonify
from collect import collect_all

app = Flask(__name__)

@app.route("/api/news")
def news():
    return jsonify(collect_all())

@app.route("/api/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
