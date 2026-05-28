# Arquitetura técnica — Solve Scraper

## Visão geral

Sistema modular Python que orquestra **scrapers locais** + **Gemini API** + **enrichers externos** + **saída CSV**, com **servidor FastAPI** para integração com **extensão Chrome**.

---

## Diagrama de arquitetura

```
                  ┌──────────────────────────┐
                  │   USUÁRIO (Marcos/time)  │
                  └─────────┬────────────────┘
                            │
              ┌─────────────┴──────────────┐
              ▼                            ▼
       ┌─────────────┐            ┌──────────────────┐
       │     CLI     │            │  Extensão Chrome │
       │  (terminal) │            │  (popup + LI)    │
       └──────┬──────┘            └────────┬─────────┘
              │                            │
              │              ┌─────────────┘
              ▼              ▼
      ┌──────────────────────────────────┐
      │  PIPELINE (src/pipeline.py)      │
      │  Orquestrador principal          │
      └────┬────────────┬────────────┬───┘
           │            │            │
           ▼            ▼            ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐
    │ Scrapers │  │  Gemini  │  │Enrichers │
    │          │  │  Agent   │  │          │
    └──────────┘  └──────────┘  └──────────┘
         │              │              │
         ▼              ▼              ▼
    ┌──────────────────────────────────┐
    │  FONTES EXTERNAS                 │
    │  • SPA/MF (gov.br)               │
    │  • Bacen                         │
    │  • oHub                          │
    │  • ABStartups                    │
    │  • Gemini API                 │
    │  • BrasilAPI                     │
    │  • Hunter.io (opcional)          │
    └──────────────────────────────────┘
                  │
                  ▼
         ┌──────────────────┐
         │   Output Layer   │
         │  CSV / Sheets    │
         └──────────────────┘
```

---

## Componentes

### 1. CLI (`src/main.py`)
Entry point principal via `argparse`. Carrega `.env`, configura logging com `rich`, chama o pipeline e formata a saída.

### 2. Pipeline (`src/pipeline.py`)
Orquestrador. Para cada vertical:
1. Instancia scraper
2. Coleta HTML/JSON
3. Envia para `Gemini.parser`
4. Para cada empresa: classifica → enriquece → pontua → personaliza
5. Acumula leads e retorna

### 3. Scrapers (`src/scrapers/`)
Cada scraper herda de `BaseScraper`:
- `bets_spa_mf.py` — SPA/MF lista oficial
- `ips_bacen.py` — Bacen IPs
- `cobranca_ohub.py` — oHub diretório
- `saas_abstartups.py` — ABStartups
- `linkedin.py` — Parser para dados vindos da extensão (não scrapeia direto)

Tecnologia: **Playwright** (renderiza JS, suporta sites modernos).

### 4. LLM Agent (`src/claude_agent/`)
> Nome do pacote preservado por compat. Backend agora é **Gemini** (google-genai SDK).

Wrapper com:
- **JSON mode nativo** (`response_mime_type=application/json`) força saída estruturada
- **JSON extraction** defensiva (lida com markdown code fences)
- Módulos especializados:
  - `parser.py` — HTML → empresas estruturadas
  - `classifier.py` — vertical + segmento + porte
  - `scorer.py` — score 0-100 com breakdown
  - `personalize.py` — frase de outbound única

### 5. Enrichers (`src/enrichers/`)
- `brasil_api.py` — CNPJ → razão social, porte, UF, CNAE
- `hunter.py` — Hunter.io (opcional, requer API key)
- `email_validator.py` — DNS MX records (gratuito, determinístico)

### 6. Output (`src/output/`)
- `csv_writer.py` — CSV padronizado (18 colunas)
- `csv_writer.py::write_apollo_csv` — formato Apollo
- Futuro: `sheets_writer.py` para Google Sheets

### 7. API Server (`src/api/server.py`)
FastAPI com endpoints:
| Endpoint | Método | Descrição |
|---|---|---|
| `/` | GET | Status |
| `/health` | GET | Health check |
| `/scrape` | POST | Dispara job de scraping |
| `/jobs/{id}` | GET | Status de um job |
| `/jobs` | GET | Lista jobs |
| `/outputs` | GET | Lista CSVs gerados |
| `/linkedin/ingest` | POST | Recebe leads da extensão Chrome |

Autenticação via `X-API-Token` header.

### 8. Extensão Chrome (`chrome-extension/`)
Manifest V3 com:
- **Popup** (`popup.html` + `popup.js` + `popup.css`) — UI principal
- **Background** (`background.js`) — service worker
- **Content** (`content.js` + `content.css`) — roda no LinkedIn
- **Options** (`options.html` + `options.js`) — config persistente

---

## Decisões técnicas

### Por que Playwright e não requests+BS4?
- LinkedIn, oHub, e ABStartups são SPAs com JS pesado
- Playwright renderiza JS direito
- Para fontes estáticas (Bacen), Playwright é overkill mas funciona

### Por que LLM para parsing?
HTML do governo brasileiro é **inconsistente** (tables, divs, listas mistas). Regex/XPath quebra a cada mudança visual. Um LLM lida com qualquer layout.

### Por que Gemini 2.5 Flash?
- **Latência baixa** — fundamental quando processamos 2.000 empresas em loop
- **Custo agressivo** — gemini-2.5-flash é ~10× mais barato que modelos pro
- **Context window 1M tokens** — cabe HTML inteiro sem truncar
- **JSON mode nativo** — saída garantidamente estruturada via `response_mime_type`
- **Free tier generoso** — 15 req/min, 1.500 req/dia (gemini-2.5-flash)

### Por que FastAPI?
Comunicação com extensão Chrome precisa de CORS + auth + async background jobs. FastAPI faz tudo isso com 50 linhas.

### Por que extensão Chrome e não automação Playwright do LinkedIn?
- LinkedIn detecta automação headless e bane contas
- Usuário navegar normalmente + extensão extrair = experiência humana real
- ToS-friendly (só captura o que está visível na sessão do próprio usuário)

---

## Fluxo de dados

```
1. SCRAPE
   ↓
   raw HTML salvo em data/raw/<vertical>_*.html

2. PARSE (Gemini)
   ↓
   lista de empresas em memória: [{empresa, cnpj, site, ...}, ...]

3. CLASSIFY (Gemini)
   ↓
   cada empresa ganha: vertical, segmento, porte_estimado

4. ENRICH (BrasilAPI + opcional Hunter)
   ↓
   cada empresa ganha: razao_social, capital_social, uf, atividade, email_provavel

5. SCORE (Gemini)
   ↓
   cada empresa ganha: score_icp (0-100), breakdown, recomendacao

6. PERSONALIZE (Gemini) — só se score ≥ 50
   ↓
   cada empresa ganha: gatilho_personalizado

7. OUTPUT
   ↓
   CSV em data/output/leads_<vertical>_<timestamp>.csv
```

---

## Custo de execução

Para 2.000 empresas (todas as 4 verticais):

| Etapa | Tokens médios | Custo Gemini (2.5 Flash) |
|---|---|---|
| Parse HTML (1 call por fonte = 4) | 50k in / 5k out × 4 | ~R$ 6 |
| Classify (2.000 calls) | 500 in / 200 out × 2.000 | ~R$ 25 |
| Score (2.000 calls) | 600 in / 200 out × 2.000 | ~R$ 30 |
| Personalize (1.000 calls, só score ≥ 50) | 500 in / 100 out × 1.000 | ~R$ 12 |
| **TOTAL** | — | **~R$ 75 por run completa** |

Com cache de prompt ativo:
- Primeira run da semana: ~R$ 75
- Runs subsequentes (mesma semana): ~R$ 15

---

## Limitações conhecidas

1. **Seletores LinkedIn mudam** — atualizar `content.js` quando quebrar
2. **Hunter.io tem free tier limitado** (50 buscas/mês) — usar com parcimônia
3. **BrasilAPI** pode rate-limitar — adicionar `time.sleep(0.2)` entre chamadas se necessário
4. **Gemini pode hallucinar e-mails** — só confiar em `email_validado=True`
5. **Sem retry inteligente** — implementar exponential backoff numa próxima versão

---

## Extensões futuras

- [ ] `src/scrapers/crunchbase.py` — API Crunchbase
- [ ] `src/output/sheets_writer.py` — push direto pra Google Sheets
- [ ] `src/output/intercom.py` — cria contato direto no CRM
- [ ] `src/jobs/scheduler.py` — agenda runs periódicos com APScheduler
- [ ] `src/jobs/monitor.py` — detecta novas bets/IPs e notifica via Slack
- [ ] `src/dashboard/` — dashboard web simples com Streamlit ou Next.js
