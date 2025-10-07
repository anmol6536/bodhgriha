(() => {
    const listEl = document.getElementById('chat');
    const inputEl = document.getElementById('msg');
    const sendBtn = document.getElementById('send-btn');

    if (!listEl || !inputEl || !sendBtn) {
        return;
    }

    const receiverId = Number(inputEl.dataset.receiverId || sendBtn.dataset.receiverId || 2);
    const currentUser = (listEl.dataset.currentUser || '').toLowerCase();

    const socket = io({
        transports: ['websocket', 'polling'],
        path: '/socket.io',
        withCredentials: true,
    });

    const chatState = {
        connected: false,
    };

    function setConnectionIndicator() {
        sendBtn.disabled = !chatState.connected;
    }

    setConnectionIndicator();

    function sanitize(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function renderTimestamp(isoString) {
        if (!isoString) return '';
        const date = new Date(isoString);
        if (Number.isNaN(date.getTime())) return '';
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    function appendMessage({ sender, content, timestamp }) {
        const safeSender = sender || 'Unknown';
        const safeContent = sanitize(content || '');
        if (!safeContent) return;

        const isSelf = currentUser && safeSender.toLowerCase() === currentUser;
        const li = document.createElement('li');
        li.className = `flex w-full ${isSelf ? 'justify-end' : 'justify-start'}`;

        const bubble = document.createElement('div');
        bubble.className = [
            'max-w-[70%]',
            'px-4',
            'py-3',
            'rounded-2xl',
            'shadow-sm',
            isSelf
                ? 'bg-emerald-500 text-white rounded-br-md'
                : 'bg-white text-slate-800 border border-slate-200 rounded-bl-md'
        ].join(' ');

        const header = document.createElement('div');
        header.className = `flex items-center ${isSelf ? 'justify-end' : 'justify-start'} gap-2 mb-1`;

        const name = document.createElement('span');
        name.className = `text-xs font-semibold ${isSelf ? 'text-white/80' : 'text-emerald-600'}`;
        name.textContent = isSelf ? 'You' : safeSender;

        const time = document.createElement('span');
        time.className = `text-[10px] uppercase tracking-wide ${isSelf ? 'text-white/60' : 'text-slate-400'}`;
        time.textContent = renderTimestamp(timestamp);

        header.appendChild(name);
        if (time.textContent) {
            header.appendChild(time);
        }

        const body = document.createElement('p');
        body.className = 'leading-relaxed';
        body.innerHTML = safeContent.replace(/\n/g, '<br>');

        bubble.appendChild(header);
        bubble.appendChild(body);

        li.appendChild(bubble);
        listEl.appendChild(li);
        listEl.scrollTo({ top: listEl.scrollHeight, behavior: 'smooth' });
    }

    socket.on('connect', () => {
        chatState.connected = true;
        setConnectionIndicator();
    });

    socket.on('disconnect', () => {
        chatState.connected = false;
        setConnectionIndicator();
    });

    socket.on('connect_error', (error) => {
        console.warn('Socket connection error', error);
        chatState.connected = false;
        setConnectionIndicator();
    });

    socket.on('receive_message', (data) => {
        appendMessage(data ?? {});
    });

    function send() {
        const content = inputEl.value;
        if (!chatState.connected || !content.trim()) {
            return;
        }
        socket.emit('send_message', { receiver_id: receiverId, content });
        inputEl.value = '';
        autoResize();
        inputEl.focus();
    }

    sendBtn.addEventListener('click', send);
    inputEl.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            send();
        }
    });

    function autoResize() {
        inputEl.style.height = 'auto';
        const newHeight = Math.min(inputEl.scrollHeight, 160);
        inputEl.style.height = `${newHeight}px`;
    }

    inputEl.addEventListener('input', autoResize);
    autoResize();
})();
