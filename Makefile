.PHONY: server

server:
	source .env && source .venv/bin/activate && python -m app 