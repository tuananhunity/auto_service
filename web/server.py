"""
Flask + SocketIO backend server for Facebook Auto Comment Bot.
Provides REST API + WebSocket for web dashboard and mobile app.
"""
import os
import threading
import time
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS

from src.core.facebook_bot import FacebookBot
from src.core.browser import setup_chrome_driver
from src.utils.file_parser import load_lines_from_file

app = Flask(__name__)
app.config['SECRET_KEY'] = 'fb-bot-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ── Bot State ──────────────────────────────────────────────
bot_state = {
    'status': 'stopped',        # 'stopped' | 'running' | 'stopping'
    'comment_count': 0,
    'current_group': '',
    'total_groups': 0,
    'logs': [],
}

bot_instance = None
bot_thread = None
stop_event = threading.Event()


def bot_log_callback(message):
    """Push log messages to all connected clients via SocketIO."""
    bot_state['logs'].append(message)
    # Keep only last 500 logs in memory
    if len(bot_state['logs']) > 500:
        bot_state['logs'] = bot_state['logs'][-500:]
    socketio.emit('log_message', {'message': message})
    socketio.emit('status_update', get_status_dict())


def get_status_dict():
    return {
        'status': bot_state['status'],
        'comment_count': bot_state['comment_count'],
        'current_group': bot_state['current_group'],
        'total_groups': bot_state['total_groups'],
    }


def run_bot_worker(group_urls, comments_list, config):
    """Background worker thread for the bot."""
    global bot_instance
    try:
        bot_state['status'] = 'running'
        bot_state['comment_count'] = 0
        bot_state['total_groups'] = len(group_urls)
        socketio.emit('status_update', get_status_dict())

        bot_instance = FacebookBot(
            group_urls=group_urls,
            comments_list=comments_list,
            config=config,
            log_callback=bot_log_callback,
            stop_event=stop_event,
        )
        bot_instance.run()
    except Exception as e:
        bot_log_callback(f"❌ Bot error: {e}")
    finally:
        bot_state['status'] = 'stopped'
        bot_instance = None
        socketio.emit('status_update', get_status_dict())


# ── REST API ───────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/status', methods=['GET'])
def api_status():
    return jsonify(get_status_dict())


@app.route('/api/start', methods=['POST'])
def api_start():
    global bot_thread
    if bot_state['status'] == 'running':
        return jsonify({'error': 'Bot đang chạy rồi!'}), 400

    data = request.json or {}
    group_urls = data.get('group_urls', [])
    max_posts = data.get('max_posts', 5)
    delay = data.get('delay', 7)

    # If no URLs provided, try loading from groups.txt
    if not group_urls:
        group_urls = load_lines_from_file('groups.txt')

    if not group_urls:
        return jsonify({'error': 'Chưa có URL nhóm nào!'}), 400

    # Load comments
    comments_file = data.get('comments_file', 'comments.txt')
    comments_list = load_lines_from_file(comments_file)

    config = {
        'MAX_POSTS_PER_GROUP': int(max_posts),
        'DELAY': int(delay),
    }

    stop_event.clear()
    bot_state['logs'] = []

    bot_thread = threading.Thread(
        target=run_bot_worker,
        args=(group_urls, comments_list, config),
        daemon=True
    )
    bot_thread.start()

    return jsonify({'message': 'Bot đã khởi chạy!', 'groups': len(group_urls)})


@app.route('/api/stop', methods=['POST'])
def api_stop():
    global bot_instance
    if bot_state['status'] != 'running':
        return jsonify({'error': 'Bot không đang chạy.'}), 400

    bot_state['status'] = 'stopping'
    stop_event.set()

    if bot_instance and bot_instance.driver:
        try:
            bot_instance.driver.quit()
        except:
            pass

    bot_log_callback("⚠️ Đang dừng bot...")
    return jsonify({'message': 'Đã gửi lệnh dừng.'})


@app.route('/api/comments', methods=['GET'])
def api_get_comments():
    comments = load_lines_from_file('comments.txt')
    return jsonify({'comments': comments})


@app.route('/api/comments', methods=['POST'])
def api_save_comments():
    data = request.json or {}
    comments = data.get('comments', [])
    with open('comments.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(comments))
    return jsonify({'message': f'Đã lưu {len(comments)} comments.'})


@app.route('/api/groups', methods=['GET'])
def api_get_groups():
    groups = load_lines_from_file('groups.txt')
    return jsonify({'groups': groups})


@app.route('/api/groups', methods=['POST'])
def api_save_groups():
    data = request.json or {}
    groups = data.get('groups', [])
    with open('groups.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(groups))
    return jsonify({'message': f'Đã lưu {len(groups)} groups.'})


@app.route('/api/logs', methods=['GET'])
def api_get_logs():
    return jsonify({'logs': bot_state['logs'][-100:]})


# ── SocketIO Events ───────────────────────────────────────

@socketio.on('connect')
def handle_connect():
    socketio.emit('status_update', get_status_dict())
    # Send recent logs to newly connected client
    for log in bot_state['logs'][-50:]:
        socketio.emit('log_message', {'message': log})


if __name__ == '__main__':
    print("🌐 Server running at http://0.0.0.0:5000")
    print("📱 Mobile app can connect to this IP address")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
