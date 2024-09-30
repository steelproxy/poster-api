from flask import Flask, jsonify, request
import time
import random
from functools import wraps

app = Flask(__name__)

# Function to read the secret key from a keyfile
def read_secret_key(file_path):
    with open(file_path, 'r') as file:
        return file.read().strip()

# Load the secret key from the key file
SECRET_KEY = read_secret_key('keyfile.txt')

# In-memory data structure to store bot statuses
bots = {}

# Decorator to require secret key for all requests
def require_secret_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        secret_key = request.json.get("secret_key")
        if secret_key != SECRET_KEY:
            return jsonify({"error": "Invalid secret key"}), 403
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/bots/register', methods=['POST'])
@require_secret_key
def register_bot():
    """Register a new bot."""
    bot_id = request.json.get("bot_id")
    
    if bot_id in bots:
        return jsonify({"error": "Bot already registered"}), 400
    
    bots[bot_id] = {
        "status": "running",
        "last_active": time.time(),
        "errors": None,
        "post_count": 0,
        "last_post_time": None
    }
    return jsonify({bot_id: bots[bot_id]}), 201

@app.route('/api/bots', methods=['GET'])
@require_secret_key
def get_bots():
    """Return the status of all bots."""
    return jsonify(bots)

@app.route('/api/bots/<bot_id>', methods=['GET'])
@require_secret_key
def get_bot_status(bot_id):
    """Return the status of a specific bot."""
    bot_status = bots.get(bot_id)
    if bot_status is not None:
        # Calculate post rate if applicable
        if bot_status['post_count'] > 0 and bot_status['last_post_time']:
            elapsed_time = time.time() - bot_status['last_post_time']
            bot_status['post_rate'] = bot_status['post_count'] / elapsed_time
        else:
            bot_status['post_rate'] = 0
        return jsonify({bot_id: bot_status})
    else:
        return jsonify({"error": "Bot not found"}), 404

@app.route('/api/bots/<bot_id>', methods=['PUT'])
@require_secret_key
def update_bot_status(bot_id):
    """Update the status of a specific bot."""
    data = request.json
    if bot_id in bots:
        bots[bot_id]["status"] = data.get("status", bots[bot_id]["status"])
        bots[bot_id]["last_active"] = time.time()
        bots[bot_id]["errors"] = data.get("errors", bots[bot_id]["errors"])
        return jsonify({bot_id: bots[bot_id]})
    else:
        return jsonify({"error": "Bot not found"}), 404

@app.route('/api/bots/<bot_id>/post', methods=['POST'])
@require_secret_key
def post_activity(bot_id):
    """Record a new post made by a specific bot."""
    if bot_id in bots:
        bots[bot_id]["post_count"] += 1
        bots[bot_id]["last_post_time"] = time.time()
        bots[bot_id]["status"] = "running"  # Assume bot is running after posting
        bots[bot_id]["last_active"] = time.time()  # Update last active time
        return jsonify({bot_id: bots[bot_id]})
    else:
        return jsonify({"error": "Bot not found"}), 404

@app.route('/api/bots/simulate_activity', methods=['POST'])
@require_secret_key
def simulate_activity():
    """Simulate bot activity for demonstration purposes."""
    bot_id = request.json.get("bot_id")
    if bot_id in bots:
        bots[bot_id]["status"] = random.choice(["running", "stopped"])
        bots[bot_id]["last_active"] = time.time()
        bots[bot_id]["errors"] = None if bots[bot_id]["status"] == "running" else "Random error occurred"
        return jsonify({bot_id: bots[bot_id]})
    else:
        return jsonify({"error": "Bot not found"}), 404

if __name__ == '__main__':
    app.run(debug=True)
