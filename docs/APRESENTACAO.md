# Solve Scraper — Apresentação do Produto

> Motor de prospecção B2B com IA, construído internamente para o time de Growth da Solvefy.

---

## 🎯 O problema que resolve

A Solvefy precisa entregar **250 leads qualificados em 5 semanas** para o KR2 (CPaaS), em 4 verticais simultâneas. As soluções de mercado custam caro e não conhecem o contexto da Solvefy:

| Solução de mercado | Custo mensal | Problemas |
|---|---|---|
| Apollo Pro | R$ 400 | Lista genérica, sem contexto Brasil |
| Phantombuster | R$ 350 | Configuração trabalhosa, risco LinkedIn |
| Clay | R$ 750 | Caro, curva de aprendizado |
| ZoomInfo / Lusha | R$ 2.000+ | Sem cobertura BR de qualidade |
| Apollo + SDR freela | R$ 10.000+/mês | Caro e lento |

**Resultado típico:** time gasta semanas em ferramentas, paga assinaturas mensais, ainda assim recebe leads frios e desqualificados.

---

## 💡 A solução

Um **scraper próprio orquestrado por Gemini** que:
1. **Coleta** das fontes oficiais brasileiras (SPA/MF, Bacen, oHub, ABStartups)
2. **Classifica** vertical e segmento via IA
3. **Enriquece** com CNPJ, decisores, e-mail
4. **Pontua** cada lead com critério ICP da Solvefy
5. **Personaliza** uma frase de abordagem única por empresa
6. **Exporta** CSV pronto pra Apollo/Smartlead/Heyreach

E uma **extensão Chrome** para captura visual no LinkedIn Sales Navigator.

---

## 🏆 Benefícios

### 1. Economia direta
| Item | Solução de mercado | Solve Scraper |
|---|---|---|
| Custo inicial | R$ 10.000+ (setup + SDR) | **R$ 150** (Gemini API) |
| Custo mensal | R$ 1.500–10.000 | **R$ 0–250** (Hunter opcional) |
| **Economia/ano** | — | **R$ 18.000–120.000** |

### 2. Contexto brasileiro nativo
Sabe extrair de fontes brasileiras:
- Lista oficial das 188 bets do SPA/MF
- Lista das 174 IPs do Bacen
- 200+ empresas de cobrança do oHub
- 1.430 SaaS B2B mapeados pela ABStartups
- BrasilAPI para enrichment com CNPJ

### 3. Qualidade superior via IA
- Cada lead vem com **score ICP de 0–100**
- Cada lead vem com **frase personalizada** pronta para outbound
- Cada lead vem com **classificação automática** de segmento

### 4. Sem dependência de fornecedor
- Roda local (Mac/Linux)
- Sem assinaturas obrigatórias
- Sem limite de execuções
- Sem risco de mudança de pricing

### 5. Integra com o resto da operação
- Saída direta para CSV padrão Apollo
- API REST para integrar com Intercom / HubSpot
- Extensão Chrome para captura visual
- Logs auditáveis para LGPD

---

## 🚀 Como funciona (em 3 passos)

### Passo 1 — Coleta automática
```bash
make run-betting
```
O scraper acessa SPA/MF, baixa a página, salva o HTML.

### Passo 2 — Enriquecimento com IA
- Gemini lê o HTML → extrai 188 empresas estruturadas
- Para cada empresa: classifica vertical, busca CNPJ, infere decisor, pontua score
- Para cada lead com score > 50: gera frase personalizada de abordagem

### Passo 3 — Saída pronta pra usar
```
data/output/leads_betting_2026-05-28_1430.csv
```

CSV com 18 colunas, pronto para:
- Importar no Apollo
- Importar no Smartlead (cold e-mail)
- Importar no Heyreach (LinkedIn)
- Subir em planilha pro time

---

## 🌟 Possibilidades de uso

### Hoje (MVP)
- Geração de listas qualificadas das 4 verticais do KR2
- Captura semi-manual no LinkedIn via extensão
- Score automático e frase personalizada

### Próximas 2 semanas
- Integração direta com Intercom (lead vira contato automaticamente)
- Alertas no Slack quando lead com score > 80 entrar
- Re-scoring periódico de leads antigos
- Dashboard simples de leads por vertical

### Próximos 3 meses
- **Monitor de mudanças regulatórias:** detecta nova bet autorizada / nova IP Bacen → notifica time
- **Outbound multicanal:** gera 3 mensagens diferentes (SMS, e-mail, LinkedIn) por lead
- **Integração com EDS:** dispara SMS pela própria plataforma Solvefy a leads opt-in
- **Sales co-pilot:** Gemini responde mensagens de leads em tempo real, com tom da Solvefy
- **Análise competitiva:** monitora quais clientes estão consumindo de Twilio/Zenvia/Pontaltech

### Visão de longo prazo
- **Plataforma SaaS interna** que o time de Growth opera 100% via extensão Chrome
- **Marketplace de listas** entre verticais da Solvefy (Cobrança usa lista de IPs como prospect)
- **Reuso para KR3 (Ads/agências)** sem reescrever — só trocar a fonte
- **Treinamento de modelo próprio** fine-tunado nos cases reais de fechamento

---

## 📊 Métricas-chave esperadas

| Métrica | Meta no KR2 |
|---|---|
| Volume total processado | 2.000+ empresas |
| Leads com score ≥ 70 | 500+ |
| Custo por lead qualificado | < R$ 1 (vs. R$ 160 do plano paid) |
| Tempo do time economizado | 88h/semana |
| Setup inicial | 1 dia |

---

## 💎 Diferencial estratégico

A Solvefy não vai depender de **nenhuma ferramenta externa** para fazer prospecção em escala. O sistema:
- Custa o que custa um café por mês
- Cresce junto com a empresa
- É 100% adaptável ao contexto Solvefy
- Pode virar produto comercializável no futuro (cross-sell para clientes CPaaS)

**Visão:** todo time de Growth tem motor próprio de prospecção. Isso é o nosso.
