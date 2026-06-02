# Deploy & Login Google

Guia para colocar o Solve Scraper num servidor com **"Entrar com Google"** e multiusuário.

## 1. Criar o OAuth Client (Google Cloud) — 5 min

1. [console.cloud.google.com](https://console.cloud.google.com) → crie/selecione um projeto.
2. **APIs & Services → OAuth consent screen**: tipo **Internal** (se Workspace) ou **External**; preencha nome e e-mail de suporte.
3. **APIs & Services → Credentials → Create credentials → OAuth client ID** → tipo **Web application**.
   - **Authorized JavaScript origins**: a URL do dashboard, ex. `https://vendas.suaempresa.com` (e `http://localhost:8765` para testar local).
   - Crie e copie o **Client ID** (`...apps.googleusercontent.com`).
4. No `.env` do servidor:
   ```
   GOOGLE_CLIENT_ID=SEU_CLIENT_ID.apps.googleusercontent.com
   ALLOWED_EMAIL_DOMAIN=suaempresa.com   # opcional: trava por domínio
   API_TOKEN=<token-forte-aleatorio>     # ainda usado pela extensão Chrome
   ```

Sem `GOOGLE_CLIENT_ID`, o login Google fica **desligado** e o app usa o `API_TOKEN` (comportamento atual) — nada quebra.

## 2. Como funciona
- O dashboard chama `GET /auth/config`. Se Google estiver ligado e não houver sessão → mostra o **gate de login**.
- "Entrar com Google" → o backend **verifica o ID token** (`google-auth`), confere o domínio e cria uma **sessão** (tabela `sessions`, 30 dias). O token de sessão vira o `X-API-Token` das chamadas.
- Cada atividade criada é **carimbada com o e-mail do usuário** (`responsavel`).
- A extensão Chrome continua usando o `API_TOKEN`.

## 3. Subir o servidor
```bash
pip install -r requirements.txt && playwright install chromium
# .env preenchido (GEMINI_API_KEY, GOOGLE_CLIENT_ID, API_TOKEN, ...)
python -m src.api.server   # ou uvicorn src.api.server:app --host 0.0.0.0 --port 8765
```
- **HTTPS obrigatório** em produção (o GIS exige origem segura). Use um reverse proxy (Caddy/Nginx) terminando TLS e apontando para a porta do app.
- O SQLite já roda em **WAL** (suporta um time pequeno). Para muitos usuários simultâneos, migrar para **Postgres** é o próximo passo (não incluído).

## 4. Variáveis de envio (opcional, outbound real)
```
OUTBOUND_DRY_RUN=false
SMTP_HOST= SMTP_PORT=587 SMTP_USER= SMTP_PASS= SMTP_FROM=
```
Com `OUTBOUND_DRY_RUN=true` (padrão) nada é enviado de verdade.

> Segurança: credenciais (Google, SMTP, API_TOKEN) ficam **só no `.env`** do servidor, nunca no código nem no git (`.env` está no `.gitignore`).
