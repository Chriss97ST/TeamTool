# TeamTool

TeamTool ist ein internes Web-Tool fuer Arbeitsteams mit:

- Privat- und Gruppenchats
- Aufgabenplanung (eigene und gemeinsame Auftraege)
- Wochenplan mit taeglichen Auftragsstunden je User
- Freigaben, damit andere User Worklog-Eintraege pflegen koennen
- Private und gemeinsame Notizbloecke

## Tech-Stack (Startversion)

- Backend: FastAPI (Python)
- ORM: SQLAlchemy 2
- Datenbank: SQLite lokal, PostgreSQL optional fuer produktiven Betrieb
- Auth: JWT (Access Token)
- Frontend: Moderne Single-Page-App (HTML/CSS/JS)

## Schnellstart

1. Python 3.11+ nutzen.
2. Im Ordner `backend` virtuelle Umgebung einrichten.
3. Pakete installieren:
   - `pip install -r requirements.txt`
4. `.env.example` nach `.env` kopieren und Werte anpassen.
5. API starten:
   - `uvicorn app.main:app --reload`

Hinweis zur Datenbank:

- Lokal startet das Projekt standardmaessig mit SQLite (`teamtool.db`).
- Wenn `DATABASE_URL` auf PostgreSQL zeigt, aber kein Postgres-Server laeuft, faellt die App lokal automatisch auf SQLite zurueck.
- Fuer einen echten PostgreSQL-Betrieb muss ein Server auf der konfigurierten URL erreichbar sein.

OpenAPI liegt dann unter:

- http://127.0.0.1:8000/docs

## Frontend Start

1. In den Ordner `frontend` wechseln.
2. Statischen Server starten:
   - `/opt/homebrew/bin/python3 -m http.server 5173`
3. Frontend oeffnen:
   - http://127.0.0.1:5173

Hinweis:

- API-Basis ist standardmaessig `http://127.0.0.1:8000/api` und kann in der App angepasst werden.

## Naechste Schritte

- Alembic-Migrationen einfuehren
- Rollen/Rechte ausbauen (Team-Admin, Bereichsrechte)
- Realtime-Chat mit WebSockets ergaenzen
