from flask import Flask, request, render_template, jsonify
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

dialogue = []


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('update_dialogue', dialogue, broadcast=False)


@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')


@app.route('/add_message', methods=['POST'])
def add_message():
    data = request.json
    message = {
        'role': data.get('role'),
        'content': data.get('content'),
        'start_time': "",
        'end_time': "",
        'audio_file': "",
        'tts_file': "",
        'vad_status': ""
    }
    dialogue.append(message)
    # socketio.emit('update_dialogue', dialogue, broadcast=True)  # Push update to all clients
    socketio.emit('update_dialogue', dialogue)

    return jsonify({"status": "success"}), 200


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', debug=True, allow_unsafe_werkzeug=True)
