from flask import Flask, request
import os

app = Flask(__name__)

@app.route('/alert', methods=['POST'])
def alert():
    data = request.get_json()
    ts = data.get("time", "").replace(":", "-")
    os.makedirs("error_reports", exist_ok=True)
    fname = f"error_reports/alert_{ts}.txt"
    with open(fname, "w") as f:
        f.write(f"Time: {data.get('time')}\n")
        f.write(f"Type: {data.get('event')}\n")
        f.write(f"Description: {data.get('description')}\n")
    return {"status": "alert saved"}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
