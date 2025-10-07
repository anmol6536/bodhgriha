from flask_socketio import emit, join_room
from flask_login import current_user, login_required
from models.sql.chat import Message
from core.db import uow
from flask_socketio import SocketIO

socketio = SocketIO(cors_allowed_origins="*")  # configure CORS as needed


def _write_to_db(message: Message) -> Message:
    """Persist a chat message using the unit-of-work helper."""
    with uow() as session:
        session.add(message)
        session.flush()   # populate PK/server defaults before the UoW commits
        session.refresh(message)
        return message  # the outer context gets the managed instance

def register_chat(app):

    socketio.init_app(app)
    
    @socketio.on('connect')
    def handle_connect():
        if not current_user.is_authenticated:
            return False  # Reject unauthenticated connections
        join_room(current_user.id)
        emit('status', {'msg': f'{current_user.email} connected.'}, room=current_user.id)

    @socketio.on('send_message')
    @login_required
    def handle_message(data):
        receiver_id = data.get('receiver_id')
        content = data.get('content', '').strip()

        if not receiver_id or not content:
            return  # Ignore invalid messages

        # Store message in DB
        msg = Message(
            sender_id=current_user.id,
            receiver_id=receiver_id,
            content=content,
        )
        msg = _write_to_db(msg)

        payload = {
            'sender': current_user.email,
            'receiver_id': receiver_id,
            'content': content,
            'timestamp': msg.sent_at.isoformat() if msg.sent_at else None
        }

        # Emit message to receiver room
        emit('receive_message', payload, room=receiver_id)
        emit('receive_message', payload, room=current_user.id)  # Echo to sender

    @socketio.on('disconnect')
    def handle_disconnect():
        if current_user.is_authenticated:
            emit('status', {'msg': f'{current_user.first_name} disconnected.'}, room=current_user.id)
