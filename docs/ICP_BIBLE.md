# ICP & Bible Book — Solvefy CPaaS

> **Fonte:** Bible Book Solvefy CPaaS v2.1 (Product Owner: Deivid Höhn, atualizado 26/05/2026) + Planilha ICP_Solvefy_CPaaS.xlsx
> **Esse documento é a fonte de verdade para o scraper, scoring e outbound do KR2.**

---

## 1. O que vendemos

**Solvefy CPaaS** = infraestrutura de comunicação omnichannel.
Roda **SMS · WhatsApp · RCS · Voz · E-mail** atrás de **uma única API**, com dashboard unificado, billing centralizado e suporte humano em PT-BR.

### Frase-síntese (ICP)
> "Eu ajudo empresas brasileiras de 10 a 1.000 funcionários a unificarem comunicação multicanal (SMS, WhatsApp, RCS, Voz, E-mail) em uma única API, com fatura em BRL e suporte humano em PT-BR."

---

## 2. ICP — Perfil de Cliente Ideal

| Atributo | Definição |
|---|---|
| **Segmento** | Empresas brasileiras, 10–1.000 funcionários, em **e-commerce · fintechs · gaming · varejo · saúde · educação · SaaS B2B · serviços** |
| **Dor crítica** | Opera 2+ canais com vendors fragmentados (Twilio, Zenvia, Infobip, API pirata de WhatsApp). Insatisfação concreta com custo, complexidade, cambial ou risco de banimento |
| **Budget** | R$ 1.000 a R$ 15.000/mês em comunicação multicanal |
| **Ciclo de compra** | 2–4 semanas (PME) · 4–8 semanas (mid-market via API) · até 12 semanas (enterprise) |
| **Decisor (trio)** | Marketing inicia · Tech Lead valida · Ops/Finanças aprova |

### Sinais positivos (high fit)
- Já usa SMS, WhatsApp ou e-mail manualmente
- Possui ao menos 1 dev dedicado com acesso a integrações
- Quer reduzir número de fornecedores de comunicação
- Operação ativa em 2+ canais hoje
- Histórico de banimento por API pirata do WhatsApp
- Investe em automação: RD Station, HubSpot, ERPs verticais
- Setor financeiro veta ferramentas em USD
- Produz campanhas com cadência semanal/mensal
- Já operou com vendor global (Twilio, Infobip) e sentiu o atrito

### Sinais negativos (low fit, descartar)
- Menos de 10 funcionários
- Usa apenas 1 canal sem intenção de expandir
- Sem equipe técnica mínima
- Foco exclusivo em atendimento/helpdesk (não em disparo)
- Startup em fase de exploração sem produto validado

---

## 3. Personas (trio de decisão)

### Persona 1 — Ana · Head of Marketing / Growth
- **Idade:** 28–38 · 3–7 anos de experiência
- **Cargo:** Head of Marketing, Growth Manager, Coordenadora de Marketing Digital
- **Persegue:** aumentar conversão, automatizar disparo, mostrar ROI claro, parar de depender de TI
- **Dói:** campanhas espalhadas, sem visão unificada, 8–15h/sem em planilha, dev é gargalo
- **Frase típica:** *"Eu quero rodar WhatsApp, SMS e E-mail do mesmo lugar e olhar um único dashboard pra saber o que funcionou."*

### Persona 2 — Lucas · Tech Lead / CTO
- **Idade:** 30–42
- **Cargo:** Tech Lead, CTO, Head de Engenharia, Arquiteto de Soluções
- **Persegue:** diminuir dívida técnica, garantir SLA, simplificar stack, parar de virar gargalo
- **Dói:** 3-4 integrações com vendors, cada canal novo = 2 semanas, webhook quebra em silêncio, suporte responde em inglês
- **Frase típica:** *"Me dá uma REST bem documentada, webhook que não falha e suporte técnico que entende a stack."*

### Persona 3 — Patrícia · Líder de Ops / CFO
- **Idade:** 35–55
- **Cargo:** Head/Diretora Ops, CFO, Controller, COO
- **Persegue:** previsibilidade orçamentária, redução de fornecedores, zerar exposição cambial
- **Dói:** custo volátil em USD, reconciliação manual, impossibilidade de forecast 12 meses
- **Frase típica:** *"Não aprovo mais nada cobrado em dólar com pricing imprevisível. Quero fatura única em real."*

---

## 4. Dores reais (de quem opera multicanal hoje)

| Dor | Tipo |
|---|---|
| Gerenciar 4+ vendors com faturas, SLAs e consoles separados | Fragmentação |
| Cada canal novo consome 40–80h de dev (R$ 10–20k) | Custo técnico |
| 8–15h/semana conciliando faturas e renovando templates | Custo operacional |
| Sem visão unificada de entrega, leitura, conversão | Dados fragmentados |
| Custo real em USD 40–70% acima do anunciado (IOF + câmbio) | Exposição cambial |
| Risco de banimento por API não-oficial do WhatsApp | Risco jurídico |
| Suporte global responde em inglês, no fuso errado | Suporte distante |
| Webhook quebra em silêncio — campanha não foi entregue | Instabilidade técnica |
| 3 tickets em 3 vendors para 1 envio que travou | Responsabilidade difusa |
| ROI por jornada vira planilha que ninguém atualiza | Falta de ROI |
| Dados de clientes espalhados — LGPD em risco | Compliance LGPD |
| Impossibilidade de escalar RCS sem refatorar | Escalabilidade |
| CFO veta ferramentas em USD | Bloqueio orçamentário |

---

## 5. Desejos (o que o cliente sonha)

| Desejo | Tipo |
|---|---|
| Dashboard único com entrega, leitura, conversão em tempo real | Visibilidade |
| Rodar campanha multicanal (WhatsApp + SMS + E-mail) do mesmo lugar | Autonomia operacional |
| Integração em 1 dia útil, não projeto de 2 semanas | Agilidade técnica |
| API REST bem documentada com sandbox imediato | Agilidade técnica |
| Forecast de 12 meses em BRL sem surpresas | Previsibilidade financeira |
| Fatura única em real, custo previsível mês a mês | Previsibilidade financeira |
| Compliance LGPD centralizado em um único fornecedor | Segurança jurídica |
| SLA único quando algo trava | Confiabilidade |
| Suporte humano em PT-BR incluso no plano | Atendimento local |
| Escalar RCS e Voz sem refatorar integração | Escalabilidade |
| Operar WhatsApp via Meta oficial sem risco de banimento | Segurança |
| Fallback RCS → SMS automático sem codificar | Resiliência |

---

## 6. Diferenciais competitivos (use no outbound)

1. **5 canais reais em 1 API** — SMS, WhatsApp (Meta oficial), RCS, Voz, E-mail. Não "1 canal com 4 anexos"
2. **Fallback RCS → SMS nativo** — único no Brasil. Middleware reenvia automaticamente
3. **Pricing em BRL, contrato em português** — sem IOF, sem variação cambial. Forecast de 12 meses viável
4. **Brasil-first com arquitetura global** — schema multi-moeda/idioma/região desde o dia 1
5. **Suporte humano em PT-BR** — incluso em todos os planos, com SLA explícito
6. **Onboarding em 1 dia útil** — primeira mensagem em 24h
7. **Integração oficial em todos os canais** — zero risco de banimento WhatsApp, zero exposição jurídica
8. **LGPD-first** — arquitetura, não checklist

---

## 7. Concorrência (com gap específico)

| Concorrente | Força | Fraqueza | Nossa vantagem |
|---|---|---|---|
| **Twilio** | Líder global, SDKs, comunidade dev | Preço USD, suporte EN, contratação complexa, onboarding longo | Onboarding em horas, BRL, suporte PT-BR, contrato BR, sem IOF |
| **Infobip** | 700+ conexões com operadoras, rica em RCS/WhatsApp | Preço alto, foco enterprise, localização rasa | Simplicidade, ticket de PME, painel para mid-market BR |
| **Sinch** | Escala global, parcerias com operadoras | Sem presença real BR, suporte EN, preço USD | Localização total, ticket PME, atendimento dedicado |
| **Zenvia** | Marca conhecida BR, base instalada | Saindo do CPaaS para virar SaaS, perdeu 18% clientes em 1 ano, prejuízo R$ 154mi em 2024 | Estabilidade estratégica — nosso negócio É CPaaS |
| **Take Blip** | Forte em WhatsApp BSP | Concentração em WhatsApp, raso em SMS/Voz/RCS/E-mail, ticket alto | Multicanal real e equilibrado, pricing PME |
| **Middleware caseiro** | Controle, customização | R$ 10-20k por integração nova, 8-15h/sem manutenção, sem SLA | Pronto, mantido, SLA único, custo previsível |

---

## 8. Aplicação por vertical do KR2

Mantemos as 4 verticais priorizadas pelo Ítalo (todas dentro do ICP do Bible). Por baixo, são "recortes" do segmento:

| KR2 Vertical | Mapeamento no ICP do Bible | Volume típico | Dor crítica |
|---|---|---|---|
| **Betting** | Gaming (subset: bets reguladas SPA/MF) | Massivo — milhões SMS/mês em pico | OTP latência, banimento WhatsApp não-oficial, taxa de entrega em final de campeonato |
| **Pagamentos (IPs Bacen)** | Fintechs | Alto + crítico — SLA enterprise | Compliance Bacen/LGPD, OTP transacional, alerta anti-fraude |
| **Cobrança** | Serviços + SaaS B2B (recuperação de crédito) | Massivo — milhões SMS/mês | Régua multicanal, taxa de resposta, custo por contato |
| **SaaS B2B / B2B2C** | SaaS B2B (notificações para usuário final) | Alto — centenas de milhares/mês | API multi-tenant, custo escalável, expansão LATAM |

---

## 9. Mensagens centrais por vertical (use no scoring + outbound)

### Betting
> "5 canais oficiais em 1 API. WhatsApp via Meta, RCS direto operadora, fallback automático SMS. Fatura BRL, suporte humano em PT-BR. Aguenta pico de jogo, zero risco de banimento."

### Pagamentos (IPs Bacen)
> "OTP transacional e alertas anti-fraude com SLA único. LGPD centralizada, compliance Bacen, fatura BRL e contrato em PT. APIs robustas para integração em 1 dia útil."

### Cobrança
> "Régua de cobrança em SMS + WhatsApp + Voz pelo mesmo endpoint. 98% entrega no SMS, fatura única em BRL, dashboard com entrega/leitura/conversão em tempo real."

### SaaS B2B
> "API CPaaS multi-tenant para embutir SMS/WhatsApp/RCS/Voz/E-mail no seu produto sem virar telecom. Pricing BRL com forecast 12 meses, fallback RCS→SMS nativo, suporte humano PT-BR."

---

## 10. "Desculpinhas" comuns (objeções a preparar)

- "Já temos uma solução que funciona mais ou menos, não vale a pena mudar agora."
- "A integração vai demorar e meu dev está ocupado com outras prioridades."
- "É mais um custo fixo — precisamos validar o ROI antes de contratar."
- "Nosso CFO bloqueou novas ferramentas SaaS até o fechamento do trimestre."
- "Já ouvimos plataformas que prometem tudo e entregam pouco."
- "A API não-oficial que usamos hoje está funcionando, vamos deixar assim."
- "Não temos um dev disponível para fazer a integração agora."

---

## 11. Mercado (números públicos)

- **TAM Global CPaaS:** USD 21,27 bi em 2026 → USD 41,05 bi em 2031 (CAGR 14,05%, Mordor)
- **TAM Brasil:** USD 1,12 bi em 2025, CAGR 23,4% até 2030 (Global Growth Insights)
- **CAGR LATAM 2025-2031:** 30,9% (maior do mundo, Cognitive Market Research)
- **SAM Solvefy (PMEs mid-market BR):** R$ 800 mi – R$ 1,8 bi/ano
- **SOM Ano 1:** R$ 7,2 mi (50 empresas ativas com 2+ canais)
- **WhatsApp BR:** 169 mi usuários · 96% das empresas usam como canal principal
- **RCS:** +371% em 2024 · iOS habilitado em 2025-2026 (Vivo, TIM, Claro) · ~185 mi dispositivos

---

## 12. Por que agora? (timing)

- **RCS bateu maturidade** — TIM e Vivo com E2E no iOS 26.5 (mai/2026). Claro Q2/2026. 185 mi dispositivos.
- **WhatsApp virou dependência** — 169 mi usuários, 96% das empresas. Meta cobra por conversação desde jul/2025.
- **Consolidação abre janela** — Zenvia avalia sair do CPaaS para virar SaaS pure-play.
- **IA generativa virou tablestakes** — 63% das marcas pilotam bots conversacionais.
- **LGPD virou critério de eliminação** — empresas preferem 1 vendor com compliance centralizado a gerenciar LGPD em 4 fornecedores.

---

## 13. O que NÃO somos (out of scope)

- Não somos CRM nem gestão de pipeline comercial
- Não somos helpdesk/ticketing (mas oferecemos webhook que viabiliza)
- Não somos plataforma isolada de e-mail marketing (e-mail é canal dentro do hub)
- Não fornecemos infraestrutura de telecom própria (somos camada sobre brokers oficiais)
- Não competimos com Solvefy Marketing — somos infraestrutura

---

## 14. Stack técnico do produto (info para Tech Leads)

- **Backend:** NestJS 10 + TypeScript 5.2 (Node 18+), Clean Architecture/DDD, OpenAPI/Swagger
- **Frontend:** Next.js 14 + React 18 + TypeScript, shadcn/ui + Tailwind, ApexCharts
- **Mensageria:** BullMQ 5 + Redis, retry exponencial + DLQ
- **Cloud:** Azure AKS (Kubernetes)
- **DBs:** PostgreSQL (transacional, multi-tenancy por tenant_id) + MongoDB (logs/telemetria) + Redis
- **Observability:** OpenTelemetry + SigNoz + Sentry, 6 checkpoints na pipeline RCS
- **Integrações:** Meta Cloud API (Embedded Signup), Twilio (SMS internacional + Voz), operadoras BR (Vivo, TIM, Claro, Oi), Google RBM, SendGrid/Amazon SES

---

## 15. Unit economics (referência)

| Métrica | Valor |
|---|---|
| CAC meta | R$ 2.000 |
| ARPU meta | R$ 2.000 (MRR) |
| LTV | R$ 66.667 (churn 3%) → R$ 100k (churn 2% meta) |
| LTV:CAC | 33:1 atual → 50:1 meta |
| Payback | 1 mês |
| NRR | ≥ 110% |

---

## 16. Como o scraper deve aplicar isso

1. **Filtragem inicial:** empresa precisa estar no segmento amplo (e-commerce, fintech, gaming, varejo, saúde, educação, SaaS B2B, serviços) com 10–1.000 funcionários
2. **Scoring:** aplicar peso pelos sinais positivos/negativos da seção 2
3. **Decisor a buscar:** trio Marketing → Tech Lead → Ops/Finanças (priorizar conforme persona dominante da empresa)
4. **Gatilho personalizado:** usar mensagem central da vertical (seção 9) + dor específica detectada
5. **Mensagens de outbound:** falar a língua da persona — para Tech Lead, foco em REST/webhook/SLA; para Marketing, foco em dashboard único/ROI; para Ops, foco em fatura BRL/forecast

---

## 17. North Star Metric do produto

> Número de empresas ativas que enviaram a 1ª campanha em 2 ou mais canais simultâneos em ≤ 7 dias pós-integração.

Implícito no scraper: **leads qualificados são empresas que conseguiriam virar ativas em 7 dias** — ou seja, têm dev disponível + budget já alocado + dor concreta + insatisfação com vendor atual.

---

## 18. Onde está cada coisa no projeto

| Bible Section | Aplicado em |
|---|---|
| ICP (seção 2) | `config.yaml` → `verticais.<x>.icp` |
| Personas | `src/claude_agent/scorer.py` (decisores) + `outbound/orchestrator.py` (tom da msg) |
| Mensagens centrais | `config.yaml` → `verticais.<x>.mensagem_central` |
| Diferenciais | `src/claude_agent/personalize.py` (SYSTEM_PERSONALIZER) |
| Concorrentes | Referência interna para tratamento de objeção |
| Sinais positivos/negativos | `src/claude_agent/scorer.py` (critérios de fit) |
| Out of scope | `src/claude_agent/classifier.py` (não classificar como CPaaS prospect) |
