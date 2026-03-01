# Quick deploy — summary

What to do (owner):
- Add two DNS A records pointing to the server public IP:
  - `api.alto-ai.tech` → server IP
  - `logs.alto-ai.tech` → server IP

Commands your friend runs (exact):

```bash
git clone https://github.com/Nyvo2010/Alto-AI-Backend.git
cd Alto-AI-Backend && ./setup_mac.sh
```

Port forwarding (friend must configure):
- Forward external TCP 80 → Mac LAN IP port 80 and TCP 443 → Mac LAN IP port 443.
- If forwarding is not possible, use a tunnel service (ngrok / cloudflared) to expose the server.

Verification (after DNS):
- API health: https://api.alto-ai.tech/health
- Logs stream: https://logs.alto-ai.tech/logs/stream?token=THE_TOKEN (or via `X-Log-Token` header)

Files to check in the repo:
- `setup_mac.sh` — interactive installer and launcher
- `Caddyfile.example` — example Caddyfile for subdomains
