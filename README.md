# Solve Scraper — Motor de Prospecção da Solvefy

> Agente de prospecção B2B que coleta, enriquece, qualifica e personaliza leads das 4 verticais-alvo do KR2 (CPaaS): **Betting · Instituições de Pagamento · Cobrança · SaaS B2B**.

Construído sobre **Gemini API + Playwright + Python**, com extensão Chrome para orquestração visual.

---

## ⚡ Início rápido

```bash
# 1. Instalar dependências
pip install -r requirements.txt
playwright install chromium

# 2. Configurar variáveis
cp .env.example .env
# edite .env com sua GEMINI_API_KEY

# 3. Rodar a primeira coleta (vertical Betting)
python -m src.main --vertical betting --limit 50

# 4. Output em data/output/leads_betting_<data>.csv
```

---

## 🎯 O que ele entrega

CSV padronizado por vertical com 18 colunas:

| Coluna | Descrição |
|---|---|
| `vertical` | betting / pagamentos / cobranca / saas_b2b |
| `empresa` | Nome comercial |
| `cnpj` | CNPJ formatado |
| `razao_social` | Razão social oficial |
| `site` | Site oficial |
| `status_licenca` | Status regulatório (quando aplicável) |
| `decisor_nome` | Nome do decisor identificado |
| `decisor_cargo` | Cargo |
| `decisor_linkedin` | URL do LinkedIn |
| `email_provavel` | E-mail inferido / encontrado |
| `email_validado` | Boolean — passou em MX check |
| `telefone` | Telefone se disponível |
| `porte_estimado` | pequeno / médio / grande |
| `gatilho_personalizado` | Frase pronta para outbound (Claude) |
| `score_icp` | 0–100 fit com ICP |
| `fonte` | URL/origem dos dados |
| `data_coleta` | Timestamp |
| `observacoes` | Notas adicionais (Claude) |

---

## 📂 Estrutura

```
solve scraper - linked in/
├── src/                          # Código Python
│   ├── scrapers/                 # 1 por fonte
│   ├── enrichers/                # CNPJ, e-mail, LinkedIn
│   ├── claude_agent/             # Integração Claude API
│   ├── output/                   # CSV, Sheets, formato Apollo
│   └── api/                      # FastAPI server (pra extensão Chrome)
├── chrome-extension/             # Extensão Chrome de orquestração
├── data/
│   ├── raw/                      # HTMLs/PDFs coletados
│   ├── processed/                # JSONs intermediários
│   └── output/                   # CSVs finais
├── docs/                         # Documentação completa
└── tests/
```

---

## 🧠 Como o Gemini entra

| Etapa | Quem faz |
|---|---|
| Renderizar HTML / baixar PDF | Playwright (código) |
| **Extrair dados de HTML "sujo"** | **Gemini** |
| **Classificar vertical e segmento** | **Gemini** |
| Buscar CNPJ na BrasilAPI | requests |
| **Inferir decisor (CTO, Head Produto)** | **Gemini** |
| Validar e-mail (MX records) | dnspython |
| **Pontuar fit com ICP** | **Gemini** |
| **Gerar gatilho de outbound personalizado** | **Gemini** |
| Exportar CSV / Sheets | pandas |

---

## 🧩 Extensão Chrome

Instalável em modo desenvolvedor para:
- **Disparar coletas direto do navegador**
- **Visualizar leads em tempo real**
- **Capturar dados do LinkedIn Sales Navigator** (quando navegando)
- **Exportar CSV direto da extensão**

Ver [`chrome-extension/README.md`](./chrome-extension/README.md).

---

## 📚 Documentação completa

- [`docs/APRESENTACAO.md`](./docs/APRESENTACAO.md) — Apresentação do produto
- [`docs/COMO_USAR.md`](./docs/COMO_USAR.md) — Guia operacional
- [`docs/FEATURES.md`](./docs/FEATURES.md) — **Features v0.2** (dashboard, monitor, rescore, outbound, Intercom)
- [`docs/ARQUITETURA.md`](./docs/ARQUITETURA.md) — Arquitetura técnica
- [`docs/POSSIBILIDADES.md`](./docs/POSSIBILIDADES.md) — Casos de uso e expansões
- [`docs/INSTALACAO.md`](./docs/INSTALACAO.md) — Setup detalhado

## 🖥️ Dashboard web

Depois de `make server`, acesse:

**http://127.0.0.1:8765/dashboard/**

Interface aplica o **Solvefy Design System** com brand CPaaS. Acessa overview, leads, monitor de mudanças, outbound multicanal, eventos e configurações.

---

## 💰 Custo de operação

| Item | Custo |
|---|---|
| Gemini API (gemini-2.5-flash) — ~10M tokens para 2.000 empresas | ~R$ 30–80 (uma vez) |
| BrasilAPI (CNPJ) | R$ 0 |
| Playwright + scraping local | R$ 0 |
| Hunter.io (opcional, e-mail enrichment) | R$ 0–250/mês |
| **TOTAL MÍNIMO** | **~R$ 30–80 únicos** |

---

## 📜 Licença e uso

Projeto interno Solvefy. Uso restrito ao time de Growth.
