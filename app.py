from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, join_room, leave_room, send, emit
from flask_cors import CORS
import random
import string

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configurations
app.config['SECRET_KEY'] = 'your_secret_key'

# Session and SocketIO setup
socketio = SocketIO(app, cors_allowed_origins="*")

rooms = {}
colors = ['#FF5733', '#33FF57', '#3357FF', '#FF33A8', '#33FFF3', '#F3FF33', '#A833FF', '#FF8333']

def generate_room_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create_room', methods=['POST'])
def create_room():
    username = request.form['username']
    room_id = generate_room_id()
    rooms[room_id] = {'users': [], 'typing': []}
    session['username'] = username
    session['room_id'] = room_id
    return redirect(url_for('chat'))

@app.route('/join_room', methods=['POST'])
def join_room_route():
    username = request.form['username']
    room_id = request.form['room_id']
    if room_id in rooms:
        session['username'] = username
        session['room_id'] = room_id
        return redirect(url_for('chat'))
    else:
        return 'Böyle bir oda yok kanka :D', 404

@app.route('/chat')
def chat():
    if 'username' in session and 'room_id' in session:
        return render_template('chat.html', username=session['username'], room_id=session['room_id'])
    else:
        return redirect(url_for('index'))

@socketio.on('join')
def on_join(data):
    username = data['username']
    room_id = data['room']
    color = random.choice(colors)
    join_room(room_id)
    rooms[room_id]['users'].append({'username': username, 'color': color})
    send({'msg': f'{username} odaya katıldı.', 'username': 'Sistem', 'color': '#000000'}, room=room_id)
    emit('user_color', {'username': username, 'color': color}, room=request.sid)

@socketio.on('message')
def on_message(data):
    room_id = session['room_id']
    username = session['username']
    color = None
    for user in rooms[room_id]['users']:
        if user['username'] == username:
            color = user['color']
            break
    send({'msg': data.get('msg', ''), 'username': username, 'color': color, 'image': data.get('image', ''), 'video': data.get('video', '')}, room=room_id)
    if username in rooms[room_id]['typing']:
        rooms[room_id]['typing'].remove(username)
        emit('stop typing', {'username': username}, room=room_id)

@socketio.on('typing')
def on_typing(data):
    room_id = session['room_id']
    username = session['username']
    if username not in rooms[room_id]['typing']:
        rooms[room_id]['typing'].append(username)
    emit('typing', {'usernames': rooms[room_id]['typing']}, room=room_id)

@socketio.on('stop typing')
def on_stop_typing(data):
    room_id = session['room_id']
    username = session['username']
    if username in rooms[room_id]['typing']:
        rooms[room_id]['typing'].remove(username)
    emit('typing', {'usernames': rooms[room_id]['typing']}, room=room_id)

@socketio.on('leave')
def on_leave(data):
    username = session['username']
    room_id = session['room_id']
    leave_room(room_id)
    for user in rooms[room_id]['users']:
        if user['username'] == username:
            rooms[room_id]['users'].remove(user)
            break
    send({'msg': f'{username} has left the room.', 'username': 'Sistem', 'color': '#000000'}, room=room_id)
    if len(rooms[room_id]['users']) == 0:
        del rooms[room_id]

@socketio.on('disconnect')
def on_disconnect():
    username = session.get('username')
    room_id = session.get('room_id')
    if username and room_id and room_id in rooms:
        leave_room(room_id)
        for user in rooms[room_id]['users']:
            if user['username'] == username:
                rooms[room_id]['users'].remove(user)
                break
        send({'msg': f'{username} odadan ayrıldı.', 'username': 'System', 'color': '#000000'}, room=room_id)
        if len(rooms[room_id]['users']) == 0:
            del rooms[room_id]

if __name__ == '__main__':
    socketio.run(app, debug=True)
