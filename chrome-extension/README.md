# Solve Scraper — Extensão Chrome

Extensão de orquestração visual para o motor de prospecção da Solvefy.

## Instalação (modo desenvolvedor)

1. Abra o Chrome e vá em `chrome://extensions`
2. Ative o **Modo de desenvolvedor** (canto superior direito)
3. Clique em **Carregar sem compactação**
4. Selecione a pasta `chrome-extension/` deste projeto
5. A extensão aparecerá com ícone na barra do Chrome

> **Importante:** gere os PNGs dos ícones antes (ver `icons/README.md`). Sem eles, o Chrome usa ícone genérico mas a extensão funciona.

## Pré-requisito: servidor local rodando

A extensão fala com o servidor FastAPI local. Antes de usar:

```bash
cd "solve scraper - linked in"
make setup
make server
```

O servidor sobe em `http://127.0.0.1:8765` por padrão.

## Configuração

1. Clique no ícone da extensão
2. Vá na aba **⚙ Configurações**
3. Confirme a URL do servidor (default `http://127.0.0.1:8765`)
4. Cole o **Token da API** (mesmo valor do `.env` do servidor)

## Como usar

### Aba 1 — Dashboard
- **Disparar coleta:** escolha a vertical e clique em ▶
- **Acompanhar jobs:** lista jobs em andamento e concluídos
- **Ver outputs:** lista CSVs gerados

### Aba 2 — LinkedIn
1. Navegue até uma busca no Sales Navigator ou perfil/empresa
2. Clique em **📥 Capturar página atual**
3. A extensão extrai os leads visíveis e envia ao servidor
4. Claude classifica + pontua + personaliza automaticamente
5. CSV é gerado em `data/output/`

### Aba 3 — Configurações
- URL e token da API
- Persistência local (`chrome.storage`)

## Onde funciona

- ✅ LinkedIn Sales Navigator (busca pessoas/empresas)
- ✅ LinkedIn busca pública (`/search/results/people`)
- ✅ Perfil de pessoa (`/in/...`)
- ✅ Página de empresa (`/company/...`)

## Limites

- A extensão **não faz scraping em massa** — captura só o que está visível
- LinkedIn pode mudar seletores; manter `content.js` atualizado
- Para uso em volume seguro, intercalar capturas manuais com navegação normal

## Troubleshooting

**"Offline" no badge:**
- Servidor não está rodando. Rode `make server`.
- Token errado: confira `.env` do servidor.

**"Nenhum lead encontrado":**
- Seletores do LinkedIn mudaram. Atualize `content.js`.
- Aguarde a página carregar completamente antes de capturar.

**Extensão não carrega:**
- Verifique se `manifest.json` é válido (sem trailing commas)
- Verifique permissões: precisa de `activeTab`, `scripting`, `storage`
