# Deployment (Streamlit Cloud)

## 1) GitHub
- Committe niemals Service-Account JSON Keys.
- Diese Dateien sind bereits in `.gitignore` abgedeckt: `*.json`, `.streamlit/secrets.toml`.

## 2) requirements.txt
Dieses Repo enthält eine `requirements.txt` im Projekt-Root. Streamlit Cloud installiert diese automatisch.

## 3) Streamlit Cloud Settings
- Repository: dein GitHub Repo
- Branch: z.B. `main` oder ein Feature-Branch
- Main file path: `app.py`

## 4) Secrets (Google Sheets Export)
In Streamlit Cloud -> Settings -> Secrets:
- Inhalte aus `secrets_template.toml` kopieren und befüllen.

Die App liest die Credentials über:
`st.secrets["gcp_service_account"]`

## 5) Häufige Fehler
- `ModuleNotFoundError`: fehlt ein Paket in `requirements.txt` oder ein `__init__.py` in einem Ordner.
- `KeyError: 'gcp_service_account'`: Secrets fehlen oder falsch benannt.
