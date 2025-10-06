.PHONY: server

server:
	gunicorn app:app --certfile=server.crt --keyfile=server.key --bind 0.0.0.0:5001 --workers 1 --reload