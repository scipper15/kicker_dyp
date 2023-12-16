# Dyp ranking app for Kickerkiste

## Running instructions for Windows in PowerShell

1. Clone repository.
2. Change to project folder: `cd kicker_dyp`.
3. Create a virtual environment: `python.exe -m venv .venv`.
4. Activate: `.\.venv\Scripts\Activate.ps1`.
5. Install requirements: `pip install -r requirements.txt`.
6. Make subdomains work in development by adding domains to hosts-file at `C:\Windows\System32\drivers\etc\hosts` in a new line: `127.0.0.1 dyp.tablesoccer.rocks`.
7. Initialize database: `flask init-db`.
8. Create User: `flask create-standard-user`.
9. Spin up development server: `flask run --debug`.
10. Open Browser at `dyp.tablesoccer.rocks:5000`.
11. Login at `dyp.tablesoccer.rocks:5000/auth/login` / Register at `dyp.tablesoccer.rocks:5000/auth/register`.

## Running instructions hosting / production:

1. Don't use the development server in production. Use a `WSGI` server like `Gunicorn`.
2. To make it work in production: Generate a secret key: `python -c 'import secrets; print(secrets.token_hex())'`.
3. Create a `.env`-file and add `SECRET_KEY=your_secret_key`.
4. The only allowed user name is `info@mitkickzentrale.de`. Use a strong password in production.
5. Replace values at settings (`/admin/settings`) to your needs. When starting a new dyp-round: Re-Initialize database.
