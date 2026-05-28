# Instalação — Solve Scraper

Guia passo a passo para colocar o scraper rodando do zero. **Tempo estimado: 15 minutos.**

---

## Pré-requisitos

- **macOS / Linux** (Windows funciona via WSL)
- **Python 3.10+** instalado
- **Chrome** (para a extensão)
- **Chave da Gemini API** (https://aistudio.google.com/app/apikey)

Verificar versões:
```bash
python3 --version  # >= 3.10
pip --version
```

---

## Passo 1 — Clonar / acessar a pasta

```bash
cd "/Users/marcoscarvalho/Library/CloudStorage/Dropbox/_solvefy/solve scraper - linked in"
```

## Passo 2 — Criar ambiente virtual (recomendado)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## Passo 3 — Instalar dependências

```bash
make install
```

Ou manualmente:
```bash
pip install -r requirements.txt
playwright install chromium
```

## Passo 4 — Configurar variáveis

```bash
cp .env.example .env
```

Edite `.env` no seu editor favorito e configure:

```env
GEMINI_API_KEY=AIzaSy_sua_chave_aqui
```

(Opcional — só se quiser enrichment de e-mail)
```env
HUNTER_API_KEY=sua-chave-hunter
```

## Passo 5 — Primeira execução

Teste com uma vertical pequena primeiro:

```bash
make run-betting
```

Você verá:
```
▶ BETTING
  • Coletando bets da fonte SPA/MF...
  • Parseando HTML com Claude...
  • 188 empresas extraídas
  • Processando betting: 100%|████████| 188/188
  • 188 leads processados em betting
✓ CSV: data/output/leads_betting_2026-05-28_1430.csv
```

Pronto. Abre o CSV em `data/output/` e confere.

---

## Passo 6 — Instalar a extensão Chrome (opcional)

### 6.1 Gerar os ícones PNG
Se ainda não foram gerados:
```bash
cd chrome-extension/icons
# macOS:
sips -s format png --resampleHeightWidth 16 16 icon.svg --out icon16.png
sips -s format png --resampleHeightWidth 48 48 icon.svg --out icon48.png
sips -s format png --resampleHeightWidth 128 128 icon.svg --out icon128.png
```

### 6.2 Subir o servidor
Em um terminal separado:
```bash
make server
```
O servidor sobe em `http://127.0.0.1:8765`.

### 6.3 Instalar a extensão
1. Abra `chrome://extensions` no Chrome
2. Ative **Modo de desenvolvedor**
3. Clique em **Carregar sem compactação**
4. Selecione a pasta `chrome-extension/` do projeto
5. Pin a extensão na barra

### 6.4 Configurar a extensão
1. Clique no ícone da extensão
2. Vá em **⚙ Configurações**
3. Cole o **API Token** (deve coincidir com `API_TOKEN` no `.env`)
4. Salvar

Teste a conexão: o badge deve mostrar "● Online".

---

## Comandos úteis

```bash
make install         # instala deps
make run             # roda todas as verticais
make run-betting     # só betting
make run-pagamentos  # só IPs Bacen
make run-cobranca    # só cobrança
make run-saas        # só SaaS B2B
make server          # sobe o servidor para a extensão
make test            # roda testes
make clean           # limpa raw/processed
make format          # formata código com black + ruff
```

---

## Estrutura de pastas após instalação

```
solve scraper - linked in/
├── .env                   # ← suas chaves (não commitar)
├── .venv/                 # ← venv local
├── data/
│   ├── raw/               # HTMLs baixados
│   ├── processed/         # JSONs intermediários
│   └── output/            # ← CSVs prontos pra usar
├── src/                   # código
└── chrome-extension/      # extensão
```

---

## Troubleshooting

### "GEMINI_API_KEY não definida"
Edite `.env` com sua chave válida.

### "playwright not installed"
```bash
playwright install chromium
```

### Página retorna 403/blocked
A página oficial mudou ou está com proteção. Verifique `data/raw/<vertical>_*.html` para inspecionar o que foi baixado.

### Custo do Gemini muito alto
- Use `--limit 50` para testar antes
- Verifique `stats` no final da execução
- O modelo padrão é `gemini-2.5-flash` (rápido e barato). Para tarefas mais complexas, troque para `gemini-2.5-pro` no `.env`

### Extensão "Offline"
- Servidor não está rodando (`make server`)
- Token errado: confira `.env` vs configurações da extensão
- Firewall bloqueando 127.0.0.1:8765
