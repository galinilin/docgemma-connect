# Quick Demo Sharing Guide

Expose the DocGemma app temporarily for a friend to access using Cloudflare Tunnel.

## Prerequisites

- Backend running on `localhost:8000`
- Frontend running on `localhost:3000`
- RunPod/vLLM endpoint is up

## Setup

### 1. Install cloudflared

```bash
# Linux (Debian/Ubuntu)
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
chmod +x cloudflared
sudo mv cloudflared /usr/local/bin/

# macOS
brew install cloudflared

# Windows
scoop install cloudflared
```

### 2. Start the backend tunnel

```bash
cloudflared tunnel --url http://localhost:8000
```

This outputs a public URL like: `https://random-words.trycloudflare.com`

**Copy this URL.**

### 3. Update frontend environment

Edit `/home/gali/docgemma/docgemma-frontend/.env.local`:

```bash
VITE_API_URL=https://random-words.trycloudflare.com/api
VITE_WS_URL=wss://random-words.trycloudflare.com/api
```

Note: Use `wss://` (secure WebSocket) since cloudflared provides HTTPS.

### 4. Restart frontend and tunnel it

```bash
# Restart frontend with new env vars
cd /home/gali/docgemma/docgemma-frontend
npm run dev

# In another terminal, tunnel the frontend
cloudflared tunnel --url http://localhost:3000
```

### 5. Share the frontend URL

Send your friend the frontend tunnel URL (e.g., `https://other-random-words.trycloudflare.com`)

## Full Startup Sequence

```bash
# Terminal 1: Backend
cd /home/gali/docgemma/docgemma-connect
uv run docgemma-serve

# Terminal 2: Backend tunnel
cloudflared tunnel --url http://localhost:8000
# Copy the URL, update frontend .env.local

# Terminal 3: Frontend
cd /home/gali/docgemma/docgemma-frontend
npm run dev

# Terminal 4: Frontend tunnel
cloudflared tunnel --url http://localhost:3000
# Share this URL with your friend
```

## Alternative: ngrok

```bash
# Install (requires free account)
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok

# Auth (one-time)
ngrok config add-authtoken YOUR_TOKEN

# Tunnel backend
ngrok http 8000

# Tunnel frontend (separate terminal)
ngrok http 3000
```

## Notes

- **Tunnels are temporary** - URLs change each time you restart
- **Keep terminals open** - Both tunnels must stay running
- **Test first** - Open the frontend URL in incognito before sharing
