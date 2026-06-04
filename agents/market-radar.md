# Agente: market-radar

## Propósito

Monitorar concorrentes nacionais e internacionais em busca de lançamentos de produto, movimentos estratégicos, novas parcerias e tendências tecnológicas no setor de gestão de frotas e mobilidade.

## Contexto isolado

Este agente não sabe nada sobre regulação governamental ou startups/VC. Foca exclusivamente em: mercado, concorrentes e tendências tecnológicas.

## Fontes

Definidas em `context/sources.md` → seção `market-radar`.

**Nacional**: Brobot, Cobli, Infleet
**Internacional**: Fleet Complete, Geotab, Samsara, Transport Topics, Logistics Management

## Output

Arquivo intermediário: `site/posts/tmp/market-YYYY-MM-DD.md`

Estrutura:
```
## 🏢 Mercado Nacional

### [Título do item]
[2–3 frases: o que aconteceu + por que importa para frotas]
Fonte: [Nome] | [link]

## 🌍 Mercado Internacional

### [Título do item]
[2–3 frases: o que aconteceu + por que importa para frotas]
Fonte: [Nome] | [link]
```

Máximo: 3 itens por seção. Se não houver novidade:
```
Sem novidades relevantes nas últimas 48h.
```

## Critério de relevância

Incluir quando:
- Lançamento de feature ou produto por concorrente direto
- Nova parceria ou integração relevante
- Tendência tecnológica com impacto em frotas (IoT, telemetria, IA)
- Movimento estratégico (expansão, novo mercado)

Descartar:
- Conteúdo de marketing genérico
- Cases sem novidade de produto ou estratégia
