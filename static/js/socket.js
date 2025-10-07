(() => {
    let socket = null;
    const chatState = { connected: false };
    let ui = {
        listEl: null,
        inputEl: null,
        sendBtn: null,
        currentUser: '',
        receiverId: null,
    };

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

    function scrollToLatest() {
        if (!ui.listEl) return;
        ui.listEl.scrollTo({ top: ui.listEl.scrollHeight, behavior: 'smooth' });
    }

    function appendMessage({ sender, content, timestamp }) {
        if (!ui.listEl) return;

        const safeSender = sender || 'Unknown';
        const safeContent = sanitize(content || '');
        if (!safeContent) return;

        const isSelf = ui.currentUser && safeSender.toLowerCase() === ui.currentUser;
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
                : 'bg-white text-slate-800 border border-slate-200 rounded-bl-md',
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
        ui.listEl.appendChild(li);
        scrollToLatest();
    }

    function updateSendState() {
        if (!ui.sendBtn) return;
        ui.sendBtn.disabled = !chatState.connected;
    }

    function ensureSocket() {
        if (socket) {
            return socket;
        }

        socket = io({
            transports: ['websocket', 'polling'],
            path: '/socket.io',
            withCredentials: true,
        });

        socket.on('connect', () => {
            chatState.connected = true;
            updateSendState();
        });

        socket.on('disconnect', () => {
            chatState.connected = false;
            updateSendState();
        });

        socket.on('connect_error', (error) => {
            console.warn('Socket connection error', error);
            chatState.connected = false;
            updateSendState();
        });

        socket.on('receive_message', (data) => {
            appendMessage(data ?? {});
        });

        return socket;
    }

    function preloadHistory() {
        if (!ui.listEl) return;
        ui.listEl.innerHTML = '';
        const initial = ui.listEl.dataset.initial;
        if (!initial) return;
        try {
            JSON.parse(initial).forEach((msg) => appendMessage(msg));
        } catch (err) {
            console.warn('Unable to parse initial chat history', err);
        } finally {
            ui.listEl.dataset.initial = '';
        }
    }

    function autoResize() {
        if (!ui.inputEl) return;
        ui.inputEl.style.height = 'auto';
        const newHeight = Math.min(ui.inputEl.scrollHeight, 160);
        ui.inputEl.style.height = `${newHeight}px`;
    }

    function send() {
        if (!ui.inputEl) return;
        const content = ui.inputEl.value;
        if (!chatState.connected || !content.trim()) {
            return;
        }
        ensureSocket().emit('send_message', { receiver_id: ui.receiverId, content });
        ui.inputEl.value = '';
        autoResize();
        ui.inputEl.focus();
    }

    function bindUi(root) {
        const scope = root && typeof root.querySelector === 'function' ? root : document;
        const listEl = scope.querySelector('#chat');
        const inputEl = scope.querySelector('#msg');
        const sendBtn = scope.querySelector('#send-btn');

        if (!listEl || listEl.dataset.bound === 'true' || !inputEl || !sendBtn) {
            return;
        }

        listEl.dataset.bound = 'true';

        ui = {
            listEl,
            inputEl,
            sendBtn,
            currentUser: (listEl.dataset.currentUser || '').toLowerCase(),
            receiverId: Number(inputEl.dataset.receiverId || sendBtn.dataset.receiverId || 0),
        };

        ensureSocket();
        updateSendState();
        preloadHistory();
        autoResize();

        sendBtn.addEventListener('click', send);
        inputEl.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                send();
            }
        });
        inputEl.addEventListener('input', autoResize);
    }

    document.addEventListener('DOMContentLoaded', () => {
        bindUi(document);
    });

    document.addEventListener('htmx:afterSwap', (event) => {
        if (event.target && event.target.id === 'chat-panel') {
            bindUi(event.target);
        }
    });
})();
