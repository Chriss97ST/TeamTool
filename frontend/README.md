# TeamTool Frontend

Dieses Frontend ist eine schnelle, moderne SPA ohne Build-Tooling.

## Start

1. Backend starten (FastAPI):
   - `cd ../backend`
   - `uvicorn app.main:app --reload`
2. Frontend statisch ausliefern:
   - `cd ../frontend`
   - `/opt/homebrew/bin/python3 -m http.server 5173`
3. Öffnen:
   - `http://127.0.0.1:5173`

## Hinweise

- API-Basis ist standardmäßig `http://127.0.0.1:8000/api`.
- API-URL kann oben rechts in der App angepasst werden.
- Token und API-URL werden im Browser `localStorage` gespeichert.

## Bereiche

- Dashboard: Kennzahlen zu Tasks, Stunden, Chats
- Chats: Privat- und Gruppenchats, Nachrichten
- Task Ablauf: Schneller Kanban-Flow (`planned` -> `in_progress` -> `done`)
- Wochenplan: Tagesbezogene Stunden-Logs inkl. Berechtigungen
- Notizen: Private/gemeinsame Notizen und Freigaben
- User: Teamübersicht mit IDs
