# 📚 Documentação — Solve Scraper

Bem-vindo. Esta pasta contém toda a documentação do **Solve Scraper**, o motor de prospecção B2B da Solvefy.

---

## 🗺️ Onde começar

| Se você é... | Comece por |
|---|---|
| **Marcos (Head)** | [`APRESENTACAO.md`](./APRESENTACAO.md) — visão de produto e ROI |
| **Ítalo / Diretoria** | [`APRESENTACAO.md`](./APRESENTACAO.md) — benefícios e custo |
| **Mateus / Isadora (operação)** | [`COMO_USAR.md`](./COMO_USAR.md) — manual prático |
| **Quem vai instalar** | [`INSTALACAO.md`](./INSTALACAO.md) — passo a passo |
| **Devs futuros** | [`ARQUITETURA.md`](./ARQUITETURA.md) — design técnico |
| **Quem pensa estratégia** | [`POSSIBILIDADES.md`](./POSSIBILIDADES.md) — roadmap |

---

## 📄 Documentos disponíveis

### [`APRESENTACAO.md`](./APRESENTACAO.md)
Apresentação do produto: o que resolve, benefícios, ROI, visão estratégica.
**Leitura: 5 min**

### [`INSTALACAO.md`](./INSTALACAO.md)
Guia de instalação do zero. Setup do scraper Python + extensão Chrome + variáveis.
**Leitura: 10 min** · **Execução: 15 min**

### [`COMO_USAR.md`](./COMO_USAR.md)
Manual operacional para o time. Casos de uso, workflows, comandos, interpretação do CSV.
**Leitura: 10 min**

### [`ARQUITETURA.md`](./ARQUITETURA.md)
Design técnico do sistema. Diagramas, decisões, fluxo de dados, custo de execução.
**Leitura: 15 min**

### [`POSSIBILIDADES.md`](./POSSIBILIDADES.md)
Roadmap de evolução. 28 casos de uso adicionais e expansões propostas.
**Leitura: 20 min**

---

## 🚀 Quickstart absoluto

```bash
cd "/Users/marcoscarvalho/Library/CloudStorage/Dropbox/_solvefy/solve scraper - linked in"
make setup
# edite .env com GEMINI_API_KEY
make run-betting   # primeira coleta
```

CSV pronto em `data/output/`.

---

## 💡 Para o time

Este projeto é **propriedade do time de Growth da Solvefy** e foi desenhado para ser:
- **Mantido pelo Mateus** (técnico) com suporte da **Isadora Mello** (analytics + tracking)
- **Operado pelo time inteiro** via extensão Chrome
- **Direcionado pelo Marcos** (estratégia de ICP, fontes, scoring)

Mudanças significativas devem passar por discussão semanal.

---

## 🔗 Links rápidos

- Repositório: pasta local (não commitado em remote ainda)
- Time: [[01-Time]] no vault
- KR2 vinculado: [[04-Roadmap/KR2-CPaaS-Junho]]
- Tarefas operacionais: [[05-Tarefas/Tarefas]]
