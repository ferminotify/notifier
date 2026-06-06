# Fermi Notify — Notifier

Servizio di notifica periodico di Fermi Notify. Ogni 5 minuti controlla le variazioni dell'orario dal calendario Google, le confronta con le keyword degli utenti e invia notifiche via email e/o Telegram.

## Tecnologie

- Python 3.11
- psycopg2 (PostgreSQL)
- telepot (Telegram Bot API)
- smtplib (email SMTP)
- Jinja2 (template email)
- requests (Google Sheets CSV)

## Development con Docker

### Prerequisiti

- Docker + Docker Compose v2
- La repo [backend](https://github.com/ferminotify/backend) avviata prima — fornisce il DB postgres e MailPit sulla rete `ferminotify-dev`

### Avvio

```bash
# Prima: avviare il backend compose (crea la rete ferminotify-dev e il DB)
# cd ../Fermi\ Notify\ backend && docker compose -f docker-compose.dev.yml up -d

docker compose -f docker-compose.dev.yml up --build -d
```

### Rebuild dopo modifiche al codice

```bash
docker compose -f docker-compose.dev.yml up --build -d
```

### Stop

```bash
docker compose -f docker-compose.dev.yml down
```

### Log in tempo reale

```bash
docker compose -f docker-compose.dev.yml logs -f notifier
```

---

### Email in development

Le email di notifica vengono inviate a **MailPit** (avviato dal backend compose).  
Interfaccia web: `http://localhost:8025`

MailPit non richiede autenticazione SMTP e non usa STARTTLS — il compose imposta `EMAIL_STARTTLS=false` per disabilitarlo nel client.

---

### Telegram in development

Con `TELEGRAM_API_KEY=""` il bot non si connette. Al primo ciclo viene loggato un errore da `getUpdates()`, poi il notifier continua normalmente saltando la registrazione Telegram.

Per testare Telegram impostare una chiave reale:

```yaml
TELEGRAM_API_KEY: "123456:AAF..."
```

---

### Variabili d'ambiente principali

| Variabile | Dev default | Descrizione |
|-----------|-------------|-------------|
| `DB_HOST` | `db` | Hostname postgres (interno Docker, fornito dal backend compose) |
| `DB_NAME` | `fn-test-db` | Nome DB |
| `DB_USER` | `fn-test-user` | Utente DB |
| `DB_PASSWORD` | `test` | Password DB |
| `DB_PORT` | `5432` | Porta DB |
| `TELEGRAM_API_KEY` | *(vuota)* | Lasciare vuota in dev per skippare Telegram |
| `EMAIL_STARTTLS` | `false` | `false` per MailPit, `true` (default) in produzione |
| `EMAIL_SERVICE_URL` | `mailpit` | Hostname SMTP |
| `EMAIL_SERVICE_PORT` | `1025` | Porta SMTP MailPit |
| `ENVIROMENT` | `development` | Usato nei log |
| `LOG_LEVEL` | `DEBUG` | Livello di log |
| `TZ` | `Europe/Rome` | Fuso orario per orari notifiche |

---

### Ciclo di esecuzione

Il notifier esegue in loop con sleep di 5 minuti tra ogni ciclo:

1. Legge tutti gli iscritti dal DB
2. Registra nuovi utenti Telegram (se `TELEGRAM_API_KEY` è impostata)
3. Scarica gli eventi dal calendario Google Sheets
4. Per ogni utente filtra gli eventi per keyword (e keyword simili se abilitato)
5. Rimuove gli eventi già notificati
6. Invia notifiche (email e/o Telegram) in base alle preferenze
7. Salva gli eventi notificati nel DB

### Logica orari notifiche

- **Daily Notification**: inviata nella finestra `notification_time ÷ notification_time + 15min` dell'utente
- **Last Minute Notification**: inviata fuori dalla finestra daily per eventi appena pubblicati

### Fuzzy matching keyword

Se l'utente ha `include_similar_tags = true`, il notifier cerca classi simili nel DB via `pg_trgm` (similarità > 0.3) e include anche quegli eventi nelle notifiche, marcandoli come "probabili".

---

## Avvio locale senza Docker

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# creare .env con le variabili necessarie
python main.py
```

## Licenza

GNU AFFERO GENERAL PUBLIC LICENSE
