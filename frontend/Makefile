.PHONY: dev-backend dev-frontend build deploy install-backend install-frontend

# ── Development ───────────────────────────────────────────────────────────────

dev-backend:
	cd backend && flask --app app run --host=0.0.0.0 --port=5000 --debug

dev-frontend:
	cd frontend && npm run dev

# ── Build ─────────────────────────────────────────────────────────────────────

install-frontend:
	cd frontend && npm install

install-backend:
	pip install -r backend/requirements.txt --break-system-packages

install: install-frontend install-backend

build: install-frontend
	cd frontend && npm run build

# ── Deploy (Pi) ───────────────────────────────────────────────────────────────
# Run 'make build' on dev machine first, then 'make deploy' on Pi
# or run 'make deploy' on Pi after git pull

deploy: build
	sudo systemctl restart VisionGrabberWeb.service
	sudo systemctl restart VisionGrabberLauncher.service
	@echo "Deployed. Check status with: sudo systemctl status VisionGrabberWeb.service"

# ── Logs ─────────────────────────────────────────────────────────────────────

logs-web:
	sudo journalctl -u VisionGrabberWeb.service -f

logs-launcher:
	sudo journalctl -u VisionGrabberLauncher.service -f
