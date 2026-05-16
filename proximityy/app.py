import os
from datetime import datetime

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NESTED_DIR = os.path.join(BASE_DIR, "proximityy")

template_folder = "templates"
static_folder = "static"

if not os.path.exists(os.path.join(BASE_DIR, template_folder, "index.html")):
    nested_template = os.path.join(NESTED_DIR, "templates")
    nested_static = os.path.join(NESTED_DIR, "static")
    if os.path.exists(os.path.join(nested_template, "index.html")):
        template_folder = nested_template
        static_folder = nested_static


app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "proximity-dev-secret")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

rooms = {}


def room_users(room_id):
    return sorted(rooms.get(room_id, {}).values(), key=str.lower)


def timestamp():
    return datetime.now().strftime("%H:%M")


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("join")
def handle_join(data):
    room_id = str(data.get("room", "")).strip()
    username = str(data.get("username", "")).strip()

    if not room_id or not username:
        emit("error_message", {"message": "Room and username are required."})
        return

    rooms.setdefault(room_id, {})[request.sid] = username
    join_room(room_id)

    emit(
        "joined",
        {
            "room": room_id,
            "username": username,
            "users": room_users(room_id),
            "time": timestamp(),
        },
    )
    emit(
        "system_message",
        {"message": f"{username} joined the room.", "users": room_users(room_id), "time": timestamp()},
        to=room_id,
        include_self=False,
    )


@socketio.on("chat_message")
def handle_chat_message(data):
    room_id = str(data.get("room", "")).strip()
    message = str(data.get("message", "")).strip()
    username = rooms.get(room_id, {}).get(request.sid)

    if not room_id or not username or not message:
        return

    emit(
        "chat_message",
        {"username": username, "message": message, "time": timestamp()},
        to=room_id,
    )


@socketio.on("attachment")
def handle_attachment(data):
    room_id = str(data.get("room", "")).strip()
    username = rooms.get(room_id, {}).get(request.sid)
    filename = str(data.get("filename", "attachment")).strip()
    filetype = str(data.get("filetype", "application/octet-stream")).strip()
    content = str(data.get("content", "")).strip()

    if not room_id or not username or not content:
        return

    emit(
        "attachment",
        {
            "username": username,
            "filename": filename,
            "filetype": filetype,
            "content": content,
            "time": timestamp(),
        },
        to=room_id,
    )


@socketio.on("leave")
def handle_leave(data):
    room_id = str(data.get("room", "")).strip()
    leave_user(room_id)


@socketio.on("disconnect")
def handle_disconnect():
    for room_id in list(rooms.keys()):
        if request.sid in rooms.get(room_id, {}):
            leave_user(room_id)
            break


def leave_user(room_id):
    username = rooms.get(room_id, {}).pop(request.sid, None)
    if not username:
        return

    leave_room(room_id)
    if not rooms.get(room_id):
        rooms.pop(room_id, None)
        return

    emit(
        "system_message",
        {"message": f"{username} left the room.", "users": room_users(room_id), "time": timestamp()},
        to=room_id,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=True, allow_unsafe_werkzeug=True)
