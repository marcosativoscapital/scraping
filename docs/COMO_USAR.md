# Como usar — Solve Scraper

Manual operacional para o time de Growth.

---

## 🎯 Casos de uso

| Cenário | Comando / Ação |
|---|---|
| Quero coletar todas as bets autorizadas | `make run-betting` |
| Quero coletar todas as IPs Bacen | `make run-pagamentos` |
| Quero coletar empresas de cobrança | `make run-cobranca` |
| Quero coletar SaaS B2B | `make run-saas` |
| Quero coletar tudo de uma vez | `make run` |
| Quero capturar leads do LinkedIn | Extensão Chrome |
| Quero CSV pronto para Apollo | `python -m src.main --output apollo` |
| Quero CSV padrão + Apollo | `python -m src.main --output both` |

---

## 🚀 Modo 1 — Terminal (CLI)

### Coleta básica
```bash
python -m src.main --vertical betting --limit 50
```

### Coleta completa com enrichment de e-mail
```bash
python -m src.main --vertical all --enrich-email
```

### Saída específica para Apollo
```bash
python -m src.main --vertical pagamentos --output apollo
```

### Argumentos disponíveis
| Argumento | Valores | Default |
|---|---|---|
| `--vertical` | `betting`, `pagamentos`, `cobranca`, `saas_b2b`, `all` | `all` |
| `--limit` | int | sem limite |
| `--enrich-email` | flag | `False` |
| `--output` | `csv`, `apollo`, `both` | `csv` |
| `--output-dir` | path | `data/output` |
| `--log-level` | `DEBUG`, `INFO`, `WARNING` | `INFO` |

---

## 🌐 Modo 2 — Extensão Chrome

### 2.1 Subir servidor
```bash
make server
```
Mantém esse terminal aberto.

### 2.2 Coletar via extensão
1. Clique no ícone da extensão
2. Aba **Dashboard**
3. Escolha vertical + limit + enrich-email
4. Clique em **▶ Disparar**
5. Acompanhe o job na lista

### 2.3 Capturar leads do LinkedIn
1. Navegue até uma busca no LinkedIn Sales Navigator
   - Ex: `https://www.linkedin.com/sales/search/people?keywords=CTO%20fintech`
2. Espere a página carregar
3. Clique no ícone da extensão → aba **LinkedIn**
4. Clique em **📥 Capturar página atual**
5. Os leads aparecem no preview e o CSV é gerado em `data/output/`

**Dica:** capture várias páginas (1 a 10) para volume maior. A cada captura, 25 leads (1 página do Sales Nav) são processados.

---

## 📋 Como interpretar o CSV

### Score ICP — significado

| Score | Recomendação | Ação |
|---|---|---|
| 80–100 | `ativar_outbound` | Levar pro SDR imediatamente |
| 60–79 | `ativar_outbound` | Outbound padrão, prioridade normal |
| 40–59 | `nutrir` | Nurture sequence (sem outbound direto) |
| 0–39 | `descartar` | Não trabalhar |

### Gatilho personalizado

Já vem pronto, mas vale revisar antes de enviar. Editar sempre que:
- A frase parece genérica demais
- Há gancho mais recente que o sistema não capturou
- A linguagem ficou robótica

### Colunas importantes

- **vertical:** filtro principal
- **score_icp:** ordenação
- **gatilho_personalizado:** primeira frase do outbound
- **decisor_nome / decisor_linkedin:** alvo do outbound
- **email_provavel + email_validado:** se `True`, manda direto
- **observacoes:** info adicional do Gemini

---

## 🔄 Workflows típicos

### Workflow 1 — Lista fresca semanal
**Toda segunda-feira:**
```bash
make run             # coleta tudo
```
Resultado: 4 CSVs (um por vertical) + 1 consolidado.
Mateus filtra score ≥ 70 e sobe no Smartlead.

### Workflow 2 — Captura LinkedIn dirigida
Quando você ou Isadora estão prospectando manualmente no Sales Nav:
1. Faz a busca
2. Captura página
3. Vai pra próxima
4. Repete

Ao final, todos os leads viraram CSV automaticamente.

### Workflow 3 — Operação Indicação
Para usar a base Brasilfone:
```bash
# Importe a base no CSV manualmente
# Use o scorer e personalize para cada contato
python -m src.api.server &
# Use a API REST diretamente para processar leads existentes
```

### Workflow 4 — Monitor de novas bets
```bash
# Roda toda manhã
make run-betting
# Diff com lista anterior identifica nova bet autorizada
```
Automatização via cron:
```cron
0 9 * * 1-5 cd /caminho/projeto && make run-betting
```

---

## ⚙️ Configuração avançada

### Editar ICPs / scoring
Edite `config.yaml`:
- Mude pesos do scoring
- Adicione novos decisores-alvo por vertical
- Ajuste mensagem central

### Adicionar nova fonte / vertical
1. Crie `src/scrapers/<nova_fonte>.py` herdando de `BaseScraper`
2. Adicione no `SCRAPERS` em `src/pipeline.py`
3. Adicione a vertical em `config.yaml`

### Trocar modelo Gemini
No `.env`:
```env
GEMINI_MODEL=gemini-2.5-flash  # ou gemini-2.5-pro
```

---

## 🔐 Segurança e LGPD

- **Não commitar `.env`** (já está no `.gitignore`)
- Todos os dados coletados são de **fontes públicas**
- Para uso comercial dos leads: oferecer opt-out claro nos primeiros contatos
- Logs auditáveis em `data/raw/` (preservar 90 dias)

---

## 📞 Suporte interno

- Dúvidas operacionais: time de Growth
- Dúvidas técnicas: pessoa que estiver mantendo o código (Mateus / Isadora Mello)
- Bugs: abrir issue no repo
- Mudanças de seletor LinkedIn: editar `chrome-extension/content.js`
