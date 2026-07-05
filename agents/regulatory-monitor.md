# Agente: regulatory-monitor

## Propósito

Monitorar órgãos públicos brasileiros em busca de mudanças regulatórias, novas normas e atualizações de APIs que impactam operações de gestão de frotas.

## Contexto isolado

Este agente não sabe nada sobre concorrentes ou startups. Foca exclusivamente em: regulação, legislação e APIs governamentais.

## Fontes

Definidas em `context/sources.md` → seção `regulatory-monitor`.

- Serpro
- Senatran
- Governo Federal (Portal de Legislação e Notícias)

## Output

Arquivo intermediário: `site/posts/tmp/regulatory-YYYY-MM-DD.md`

Estrutura:
```
## 🇧🇷 Regulatório

### [Título do item]
[8–12 frases, fiel ao texto extraído da página de origem — nunca inferido ou inventado a partir do título]
Fonte: [Nome] | [link]
```

Máximo: 3 itens por dia. Se não houver novidade relevante, emitir:
```
## 🇧🇷 Regulatório
Sem novidades regulatórias relevantes nas últimas 48h.
```

## Regra de fidelidade do resumo

O resumo é gerado a partir do texto completo extraído da página de origem — nunca a partir só do título. Se o scraping falhar (paywall, JS-rendering, texto insuficiente), o item não recebe resumo inventado: o corpo publicado indica que a notícia deve ser lida na fonte original, com o link de referência.

## Critério de relevância

Incluir quando:
- Nova norma ou resolução publicada pelo Senatran
- Atualização de API ou base de dados do Serpro
- Mudança tributária ou legislativa com impacto em frotas/transporte

Descartar:
- Notícias sem efeito prático imediato
- Conteúdo institucional sem novidade
