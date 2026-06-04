# Agente: briefing-publisher

## Propósito

Consolidar os outputs dos agentes especializados e publicar o briefing diário no site. Não pesquisa nada — só organiza, formata e salva.

## Contexto isolado

Este agente não acessa fontes externas. Lê apenas os arquivos intermediários gerados pelos outros agentes.

## Inputs

```
site/posts/tmp/regulatory-YYYY-MM-DD.md   ← do regulatory-monitor
site/posts/tmp/market-YYYY-MM-DD.md       ← do market-radar
site/posts/tmp/vc-YYYY-MM-DD.md           ← do vc-startups (quando ativo)
```

## Output

Arquivo final: `site/posts/YYYY-MM-DD.md`

Estrutura obrigatória:
```
# Briefing de Mercado — DD/MM/AAAA

## 🇧🇷 Regulatório
[conteúdo do regulatory-monitor]

---

## 🏢 Mercado Nacional
[conteúdo nacional do market-radar]

---

## 🌍 Mercado Internacional
[conteúdo internacional do market-radar]

---

## 📊 Startups / VC
[conteúdo do vc-startups — ou "Em breve." se não ativo]

---

## 💡 Destaque do dia
[1 parágrafo: o item mais relevante do dia + implicação estratégica para a Frota 162]
```

## Regras

- Máximo 500 palavras no total
- Se todos os agentes retornarem "sem novidades", publicar briefing com essa informação — nunca deixar dia sem arquivo
- O "Destaque do dia" é obrigatório — escolher o item de maior impacto entre todos os agentes
- Após salvar, deletar arquivos temporários em `site/posts/tmp/`
