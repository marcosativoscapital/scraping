# Features v0.2 — Solve Scraper

Cinco features adicionadas em 28/05 sobre o MVP. Todas operáveis via dashboard web ou via API.

---

## 1. Dashboard web (Solvefy Design System · brand-cpaas)

**Acesso:** `http://127.0.0.1:8765/dashboard/` depois de `make server`

**Abas:**
- **Overview** — métricas-chave, distribuição por score, ranking por vertical, últimos leads
- **Leads** — tabela paginável com filtro por vertical, score mínimo e busca textual + export CSV
- **Monitor** — disparar verificação de mudança em qualquer das 4 verticais
- **Outbound** — selecionar lead (score ≥ 60) e gerar SMS + e-mail + LinkedIn com Gemini
- **Eventos** — feed de tudo que aconteceu (coletas, re-scores, alertas, intercom push)
- **Configurações** — API URL/token, controle do scheduler, re-score manual

**Visual:** tokens 1:1 do Solvefy Design System com brand `.brand-cpaas` (violet `#9c7bff`). Inter como typeface, cards 32px padding, radii xl, shadow-xs.

---

## 2. Monitor de mudanças regulatórias

**O que faz:** compara a lista atual da fonte oficial com o último snapshot armazenado, detecta:
- 🆕 Empresas novas (nova bet autorizada, nova IP Bacen)
- ⚠️ Empresas que saíram (licença suspensa)
- 🔄 Mudanças de status

**Como dispara:**
- Manual: dashboard → aba Monitor → clica na vertical
- CLI: `make monitor-bets` ou `make monitor-ips`
- Programático: `from src.jobs.monitor import run_monitor; run_monitor('betting')`
- Automático: scheduler (a cada 6h por padrão)

**Notifica via:** Slack webhook (se `SLACK_WEBHOOK_URL` configurado no `.env`)

**Armazena:** snapshots no SQLite (`data/solve_scraper.db`) para diff futuros.

---

## 3. Re-scoring periódico

**O que faz:** re-pontua leads com score entre 40 e 70 que não são atualizados há > 7 dias. Se o novo score subir acima de 70, promove para `ativar_outbound` e notifica time.

**Como dispara:**
- Manual: dashboard → Configurações → "Rodar re-score agora"
- CLI: `make rescore`
- Programático: `from src.jobs.rescore import run_rescore`
- Automático: scheduler (a cada 24h)

**Por que importa:** leads que estavam frios podem aquecer com novos sinais (nova licença, lançamento de produto, gatilho de mercado). Sem re-score, leads bons morrem no backlog.

---

## 4. Outbound multicanal automatizado

**O que faz:** para cada lead qualificado, gera **5 ativos** prontos com Gemini:
- **SMS** (≤ 160 chars)
- **E-mail subject** + **e-mail body** (3 parágrafos)
- **LinkedIn connection request** (≤ 300 chars)
- **LinkedIn follow-up** (≤ 700 chars)

Tudo personalizado pelo gatilho da empresa e mensagem central da vertical.

**Como dispara:**
- Dashboard → aba Outbound → escolhe lead → "Gerar mensagens"
- Dashboard → Leads → ação "Outbound" na linha (score ≥ 60)
- API: `POST /outbound/generate/{lead_id}`

**Armazena:** todas as mensagens em `outbound_messages` (SQLite) com status `rascunho`/`aprovado`/`enviado`. Auditável.

---

## 5. Integração com Intercom (CRM)

**O que faz:** empurra leads qualificados (score ≥ 60) para o Intercom como contatos com:
- Nome + e-mail + external_id estável (`solve-<cnpj>-<email>`)
- Custom attributes: empresa, vertical, segmento, porte, decisor cargo/linkedin, score ICP, gatilho personalizado
- Tags automáticas: `vertical-<x>`, `hot-lead` (se score ≥ 80)

**Como dispara:**
- Lead único: `POST /intercom/push/{lead_id}`
- Lote: `POST /intercom/push_batch?min_score=70`

**Pré-requisito:** `INTERCOM_ACCESS_TOKEN` no `.env`.

**Sem token configurado:** ignora silenciosamente (não quebra o fluxo).

---

## 6. Banco de dados local

Adicionalmente, foi introduzido um **SQLite** (`data/solve_scraper.db`) que substitui a operação só-em-CSV. Schemas:

- `leads` — fingerprint único + payload completo
- `outbound_messages` — mensagens geradas por canal
- `snapshots` — listas históricas por vertical (para diff)
- `events` — log de tudo (coletas, re-scores, monitor, intercom)

CSVs continuam sendo gerados como antes — o DB é complementar.

---

## 7. Scheduler interno

Loop em thread separada que roda:
- **Monitor** a cada 6h para `betting` e `pagamentos`
- **Re-score** a cada 24h

**Controles:**
- Dashboard → Configurações → Iniciar/Parar
- API: `POST /scheduler/start`, `POST /scheduler/stop`, `GET /scheduler/status`

---

## API endpoints novos

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/stats` | Estatísticas para overview |
| GET | `/db/leads` | Lista leads (filtros) |
| GET | `/db/leads/{id}` | Detalhe de lead |
| GET | `/db/export.csv` | Export CSV filtrado |
| GET | `/events` | Eventos recentes |
| POST | `/monitor/{vertical}` | Roda monitor |
| POST | `/rescore` | Roda re-score |
| POST | `/scheduler/start` · `/stop` | Controla scheduler |
| GET | `/scheduler/status` | Status |
| POST | `/outbound/generate/{lead_id}` | Gera mensagens |
| POST | `/intercom/push/{lead_id}` | Push individual |
| POST | `/intercom/push_batch` | Push em lote |

Todos exigem header `X-API-Token`.

---

## Quickstart das novas features

```bash
# 1. Subir o servidor (já com tudo configurado)
make server

# 2. Abrir o dashboard
open http://127.0.0.1:8765/dashboard/

# 3. Token padrão (dev): solve-scraper-dev-token
#    Configurar em "⚙ Configurações" no dashboard
```

A partir daí, tudo é clicável.
