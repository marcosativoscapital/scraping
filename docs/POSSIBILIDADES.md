# Possibilidades de uso — Solve Scraper

> Roadmap de evolução, casos de uso adicionais e ideias de expansão.

---

## 🎯 Casos de uso imediatos (já entregues)

### 1. Lista qualificada por vertical
Geração das 4 listas de lead-gen do KR2:
- 188 bets autorizadas
- 174 IPs Bacen
- 200+ cobrança
- 1.430 SaaS B2B

### 2. Captura LinkedIn semi-manual
Extensão Chrome captura leads do Sales Navigator durante a navegação normal do time, sem risco de banimento.

### 3. Lead scoring com IA
Cada empresa ganha score 0-100 com breakdown explicado.

### 4. Outbound personalizado de fábrica
Cada lead já chega com frase de abordagem única gerada pelo Gemini.

---

## 🚀 Possibilidades de curto prazo (próximas 2 semanas)

### 5. Integração com Intercom (CRM)
Lead com score ≥ 70 → cria contato automaticamente no Intercom, atribui ao SDR responsável pela vertical, envia notificação no Slack.

**Como:** webhook do servidor → API Intercom → channel Slack `#growth-novos-leads`

### 6. Monitor de mudanças regulatórias
Cron diário roda `make run-betting`. Compara lista atual com snapshot anterior:
- Nova bet autorizada → alerta Slack + e-mail
- Bet com licença suspensa → idem
- Mesma lógica para Bacen

**Como:** diff de CNPJs entre runs + notificações via webhook Slack.

### 7. Re-scoring periódico
Empresas com score 40–69 são re-pontuadas semanalmente. Se gatilho novo for detectado (notícia, IPO, novo produto), sobem para "ativar_outbound".

**Como:** módulo adicional em `src/jobs/rescore.py` + agendador `cron` ou `APScheduler`.

### 8. Operação Indicação automatizada
Para usar a base Brasilfone:
- CSV da base → pipeline cruza com lista das 4 verticais
- Identifica clientes que são exatamente da vertical-alvo (high fit para pedir indicação)
- Gera mensagem personalizada de pedido de indicação
- Dispara via EDS (SMS + WhatsApp se houver consent)

**Como:** `src/operations/indicacao.py` + integração EDS.

---

## 🌟 Possibilidades de médio prazo (1–3 meses)

### 9. Outbound multicanal automatizado
Cada lead recebe 3 mensagens diferentes geradas pelo Gemini:
- **SMS** (curto, 1 frase)
- **E-mail** (5 toques de cadência)
- **LinkedIn** (3 toques, peer-to-peer)

Cadeia integrada: SMS → e-mail (se sem resposta) → LinkedIn (se sem resposta).

**Como:** `src/outbound/orchestrator.py` orquestra envios via:
- SMS: EDS interno
- E-mail: Smartlead/Instantly via API ou diretamente SMTP
- LinkedIn: Heyreach via API ou extensão

### 10. Sales co-pilot — IA responde leads
Quando lead responde no e-mail/LinkedIn, Gemini:
1. Lê a resposta
2. Identifica intenção (interessado, objeção, fora de fit)
3. Gera próxima mensagem com tom Solvefy
4. SDR só aprova/edita antes de enviar

**Como:** integrar webhook do CRM com pipeline de resposta + interface de aprovação.

### 11. Análise competitiva contínua
Identifica:
- Quais empresas estão consumindo Twilio (via job postings, blog posts, cases)
- Quais estão consumindo Zenvia
- Quais estão insatisfeitas (via reviews em sites tipo G2, Trustpilot)

**Como:** scrapers especializados + monitoramento RSS + análise sentimentos via Gemini.

### 12. Dashboard interno
Interface visual no Chrome (página `chrome-extension://...`) ou Streamlit local:
- KPIs do KR2 em tempo real
- Funil por vertical
- Score distribution
- CAC calculado
- Heatmap de respostas

**Como:** `src/dashboard/` com Streamlit + queries no DB SQLite local.

### 13. Banco de dados local
Migrar de CSVs para SQLite/PostgreSQL local:
- Histórico de toda interação
- Re-runs incrementais (não duplica empresas já processadas)
- Queries complexas

**Como:** adicionar `src/db/` com SQLAlchemy + scripts de migration.

---

## 🔮 Possibilidades de longo prazo (3–6 meses)

### 14. Reuso para KR3 (Ads/agências)
Trocando a fonte (de SPA/MF para diretórios de agências) e o ICP (de CTO para sócio de agência), o mesmo motor entrega leads de KR3.

**Mínimo necessário:**
- Novo scraper: `src/scrapers/agencias_abradi.py` ou similar
- Novo bloco em `config.yaml` para vertical "agencias_marketing"

### 15. Plataforma SaaS interna
Tudo via extensão Chrome:
- Não precisa abrir terminal
- Time inteiro opera só pelo browser
- Marcos/Ítalo aprovam, time executa

**Como:** evoluir popup da extensão pra SPA completa (React/Svelte) + API server.

### 16. Marketplace de listas entre verticais
- Time de Cobrança quer prospectar IPs Bacen (que precisam de SaaS de cobrança)
- Time de Ads quer prospectar SaaS B2B (que precisam de gestão de paid)
- Sistema permite cross-pollination de listas entre KRs

### 17. Modelo treinado em cases reais
Fine-tunar um modelo (via Google ou OpenAI) com:
- 1.000+ exemplos de leads que fecharam
- 1.000+ exemplos de leads que não fecharam
- Features: vertical, porte, decisor, gatilho

Score deixa de ser heurístico e vira **probabilidade de fechamento real**.

**Como:** treinar fine-tune model ou usar embedding similarity para scoring.

### 18. Produto comercializável
A Solvefy poderia oferecer o motor de prospecção como **produto** para clientes:
- Cliente CPaaS quer prospectar X
- Solvefy provê o scraper white-labeled
- Cross-sell natural pro próprio CPaaS

---

## 💡 Possibilidades transversais

### 19. Webhook universal
Qualquer trigger externo (form do site, anúncio LinkedIn, resposta de e-mail) → webhook → pipeline → CRM atualizado → SDR notificado.

### 20. Auditoria LGPD
Painel que mostra:
- Onde cada lead foi coletado (fonte pública identificada)
- Quando foi opt-in
- Histórico de comunicação
- Botão de opt-out automático

### 21. AI compliance check
Antes de enviar qualquer cold message, Gemini valida:
- LGPD compliance (consentimento claro)
- Anatel (se for SMS)
- CAN-SPAM (se for internacional)
- Termos de uso do canal

Bloqueia envio se houver violação.

### 22. Multi-idioma
Mesmo motor expandido para LATAM:
- Argentina (CNV, BCRA, etc)
- México (CNBV, CONDUSEF)
- Colômbia (Superfinanciera)

Só substituir as fontes públicas locais.

### 23. Integração com Calendly
Lead com score 90+ → mensagem automática com link Calendly pessoal do Marcos/Ítalo. Conversion direto pra reunião.

### 24. Co-gestão com clientes existentes
Cliente da Solvefy CPaaS (ex: assessoria de cobrança grande) usa o scraper para prospectar SEUS próprios clientes finais.

Valor adicional: **lock-in** + cross-sell da plataforma EDS.

---

## 🎁 Ideias bônus

### 25. "Lead da semana" automático
Toda segunda 8h, Gemini analisa os leads top 5 da semana e gera relatório de 1 página por lead:
- Por que esse lead é interessante
- Quais sinais ativos foram detectados
- Próxima ação recomendada
- Frase de abordagem refinada

Sai automaticamente para o WhatsApp do time.

### 26. Detector de timing
Gemini monitora notícias sobre cada lead (Google Alerts via API):
- Lançamento de produto novo → janela de prospecção quente
- Demissão de CTO → janela de oportunidade
- Funding round → orçamento liberado

Alerta dispara push notification para o SDR.

### 27. Concurrent processing
Hoje o pipeline é serial. Com `asyncio` + `aiohttp`, podemos processar 50 empresas em paralelo, reduzindo tempo de run em 10x.

### 28. Versão mobile da extensão
PWA para iOS/Android permite time capturar leads em eventos físicos (palestras, conferências) tirando foto de crachá → OCR → enrich → score.

---

## 📊 Priorização sugerida

| Item | Esforço | Impacto | Prioridade |
|---|---|---|---|
| #5 Integração Intercom | Médio | Alto | **P0** |
| #6 Monitor regulatório | Baixo | Alto | **P0** |
| #9 Outbound multicanal | Alto | Muito alto | **P1** |
| #14 Reuso para KR3 | Baixo | Alto | **P1** |
| #7 Re-scoring periódico | Baixo | Médio | **P2** |
| #11 Análise competitiva | Médio | Médio | **P2** |
| #13 SQLite DB | Médio | Médio | **P2** |
| #10 Sales co-pilot | Alto | Alto | **P2** |
| #17 Modelo treinado | Muito alto | Médio | **P3** |
| #18 Produto comercial | Muito alto | Muito alto | **P3** |

---

## 🤝 Como propor novas funcionalidades

Quem quiser sugerir nova feature:
1. Cria nota em `docs/proposals/<feature>.md`
2. Apresenta na weekly de Growth
3. Se aprovado, vira tarefa no `Tarefas.md`
4. Implementação segue padrão arquitetural existente
