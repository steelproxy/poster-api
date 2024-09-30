import logging
import asyncio
from flask import Flask, jsonify, request, render_template
from functools import wraps
from threading import Thread
from datetime import datetime

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Dummy token for demonstration purposes
API_TOKEN = 'your_secure_token_here'

# Store bots
bots = [
    {
        'name': 'bot1',
        'wait': 3600,
        'groups': ['test', 'test2'],
        'current_posts': 0,
        'total_posts': 0,
        'last_report': None,
        'last_ping': None,
        'last_ip': None,
        'job_requests': []  # New field to store job requests
    },
]

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if token != f"Bearer {API_TOKEN}":
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

def is_positive_integer(value):
    try:
        return int(value) > 0
    except (ValueError, TypeError):
        return False

def validate_json(required_fields):
    if not request.json:
        return {"error": "Bad Request: JSON body is required"}, 400
    
    for field in required_fields:
        if field not in request.json:
            return {"error": f"Bad Request: '{field}' is required"}, 400

    return None

async def update_bot_wait(bot):
    while True:
        await asyncio.sleep(1)
        if bot['wait'] > 0:
            bot['wait'] -= 1
            if bot['wait'] == 0:
                logging.info(f"Bot '{bot['name']}' wait time has completed.")

def start_bot_wait_update(bot):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(update_bot_wait(bot))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/bots', methods=['GET'])
@require_auth
def get_bots():
    return jsonify(bots)

@app.route('/create-bot', methods=['POST'])
@require_auth
def create_bot():
    required_fields = ['name', 'wait', 'groups', 'total_posts']
    error_response = validate_json(required_fields)
    if error_response:
        return error_response

    bot = {
        'name': request.json['name'],
        'wait': int(request.json['wait']),
        'groups': request.json['groups'],
        'current_posts': 0,
        'total_posts': int(request.json['total_posts']),
        'last_report': None,
        'last_ping': None,
        'last_ip': None,
        'job_requests': []  # Initialize job requests list
    }

    bots.append(bot)
    Thread(target=start_bot_wait_update, args=(bot,)).start()
    return jsonify({"message": "Bot created successfully", "bot": bot}), 201

@app.route('/bots/<string:name>', methods=['DELETE'])
@require_auth
def delete_bot(name):
    global bots
    bots = [bot for bot in bots if bot['name'] != name]
    return jsonify({"message": f"Bot '{name}' deleted successfully."}), 200

@app.route('/bots/<bot_name>/report', methods=['POST'])
@require_auth
def report_post(bot_name):
    required_fields = ['content', 'group', 'wait']
    error_response = validate_json(required_fields)
    if error_response:
        return error_response

    content = request.json['content']
    if not content:
        return jsonify({"error": "Bad Request: 'content' cannot be empty"}), 400

    group = request.json['group']
    wait = request.json['wait']

    for bot in bots:
        if bot['name'] == bot_name:
            if group not in bot['groups']:
                return jsonify({"error": f"Bad Request: Group '{group}' not found in bot's groups"}), 400

            bot['current_posts'] += 1
            bot['last_report'] = {
                'content': content,
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'group': group
            }
            bot['last_ip'] = request.remote_addr  # Update last_ip
            bot['wait'] = wait
            logging.info(f"Bot '{bot_name}' reported: {content} to group: {group}")
            logging.info(f"Current posts: {bot['current_posts']}, Total posts: {bot['total_posts']}")

            return jsonify({"message": "Post reported successfully", "content": content}), 201

    return jsonify({"error": "Bot not found"}), 404

@app.route('/bots/<bot_name>/ping', methods=['POST'])
@require_auth
def ping_bot(bot_name):
    for bot in bots:
        if bot['name'] == bot_name:
            bot['last_ping'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            bot['last_ip'] = request.remote_addr
            logging.info(f"Bot '{bot_name}' pinged. IP: {bot['last_ip']}, Time: {bot['last_ping']}")
            return jsonify({"message": "Ping received", "ip": bot['last_ip'], "time": bot['last_ping']}), 200

    return jsonify({"error": "Bot not found"}), 404

@app.route('/bots/job', methods=['POST'])
@require_auth
def submit_job():
    required_fields = ['groups', 'posts']
    error_response = validate_json(required_fields)
    if error_response:
        return error_response

    groups = request.json['groups']
    posts = request.json['posts']

    if not isinstance(groups, list) or not isinstance(posts, list):
        return jsonify({"error": "Bad Request: 'groups' and 'posts' must be lists"}), 400

    job_request = {
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'groups': groups,
        'posts': posts
    }

    # Find the relevant bots and add the job request
    for bot in bots:
        if set(groups).intersection(set(bot['groups'])):  # Check if bot is part of any submitted group
            bot['job_requests'].append(job_request)
            logging.info(f"Job request added to bot '{bot['name']}': {job_request}")

    return jsonify({"message": "Job request submitted successfully", "job": job_request}), 201

if __name__ == '__main__':
    app.run(debug=True)
