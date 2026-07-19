# Como construí o Diário Frotástico

> Relato técnico do processo de construção — da ideia ao deploy em produção.

---

## 1. Design

Comecei pensando em como eu queria *visualizar* a informação — não um dashboard, um site de notícia mesmo, com hierarquia editorial (destaque, seções, "lido agora").

Tentei fazer na mão: ficou ruim. Tentei templates prontos: ficou genérico, sem cara de produto interno. O que funcionou foi pegar uma referência real (print da nova tela da unificação) e usar como base visual no Claude — a partir dali cheguei no layout atual: tema claro, tipografia de jornal, seções por editoria.

## 2. Escopo — as frentes de informação

Defini 4 frentes que fazem sentido pra decisão de produto na Frota 162:

- **Mercado** — concorrentes diretos e tendências de tecnologia em frotas/telemetria
- **Órgãos públicos** — mudanças regulatórias que afetam operação (ANTT, Senatran, CONTRAN)
- **Startups / VC** — captações e novos entrantes no ecossistema (ainda não ativo)
- *(Mercado e Concorrentes acabaram unificados num agente só, porque as fontes se sobrepõem)*

Pra cada frente, mapeei fontes reais: blogs de concorrentes (Cobli, Infleet, Brobot, Geotab, Samsara, Fleet Complete), veículos especializados (Transporte Moderno, Mundo Logística, Diário do Transporte), feeds oficiais de governo (ANTT, Senatran, Ministério dos Transportes, CONTRAN), e busca aberta no Google News pra cobrir o que não tem fonte fixa.

## 3. Agentes

Cada frente virou um script Python independente, com contexto isolado (um agente não sabe nada do domínio do outro):

- `market_radar.py` — mercado + concorrentes
- `regulatory_monitor.py` — órgãos públicos
- `vc-startups` — esqueleto criado, não implementado ainda

Cada agente segue o mesmo padrão: busca candidatos nas fontes → Claude seleciona os relevantes e classifica (tags, origem, hashtag de concorrente) → busca o texto completo do artigo selecionado → Claude escreve um resumo fiel a esse texto (nunca ao título sozinho) → salva como página própria no site (Astro content collections), com fonte e link sempre visíveis.

## 4. Automação diária (cron)

Configurei um workflow do GitHub Actions que roda todo dia às 7h BRT: dispara os dois agentes, comita as notícias novas direto no repositório, builda o site (Astro, gerador estático) e publica no GitHub Pages — tudo num job só, pra evitar uma limitação do GitHub onde um commit automático não dispara um segundo workflow. Também roda sob demanda (disparo manual) e em qualquer push — mas nesse último caso pula a etapa de rodar os agentes, pra nunca gastar chamada de API à toa num commit qualquer.

## 5. Blindagem de qualidade do conteúdo

Depois do primeiro run, apareceram problemas reais que precisaram de correção:

**Resumo não podia vir do título sozinho.** Na primeira versão, o Claude escrevia o resumo só com base em título/fonte/data — risco real de invenção. Corrigi adicionando uma etapa de scraping do texto completo do artigo, e uma regra explícita: o resumo (8–12 frases) só pode usar informação que está literalmente no texto extraído, nunca inferir ou completar com conhecimento prévio. Quando o scraping falha, o site não inventa nada — mostra uma mensagem clara de "acesse na fonte original".

**Links do Google News eram um problema disfarçado.** O Google News entrega uma URL de redirecionamento (via JavaScript), não o link real do artigo. Isso fazia o sistema salvar o ícone genérico do Google como se fosse a imagem da notícia. Corrigi detectando quando o link não resolve pro site real e, nesse caso, simplesmente não salvando imagem nem tentando extrair texto — em vez de publicar algo errado.

**Duplicação de conteúdo entre dias.** Como a busca no Google News recicla notícias antigas (uma matéria de semanas atrás pode ser reindexada como "nova"), o mesmo fato aparecia de novo, com data de hoje. Resolvido em duas camadas: um filtro de recência (descarta qualquer candidato com mais de 24h antes mesmo de chegar no Claude) e, para atos regulatórios especificamente, uma checagem de data explícita no próprio título do ato (ex: "Portaria nº X de 2018") — porque a data de indexação do feed não é confiável, mas a data do ato em si está sempre no nome dele.

**Ajustes de front-end**: removi caixas de "imagem indisponível" (quando não há imagem real, o espaço simplesmente não existe, em vez de mostrar um placeholder), e corrigi duplicação visual do resumo (aparecia duas vezes na mesma página de artigo).

## 6. Decisão de deploy e infraestrutura

Comparei GitHub Pages + Actions contra Netlify/Vercel. Critério decisivo: o pipeline precisa rodar Python, gerar conteúdo e commitar de volta no mesmo lugar onde o deploy acontece — GitHub Actions faz isso nativamente e de graça; Netlify/Vercel exigiriam plano pago pro cron nativo, e ainda assim precisariam de uma integração cruzada pra commitar de volta no GitHub.

Também decidi conscientemente **não** usar o domínio pessoal raiz (`rebecavaletich.github.io`) pra esse projeto — criei um repositório com nome da empresa (`diario-frotastico`), deixando o slot pessoal livre pra outros projetos futuros. Isso trouxe um custo técnico real: GitHub Pages de projeto publica num subcaminho, então precisei configurar `base` no Astro e reescrever ~20 links absolutos hardcoded no código pra não quebrar a navegação.

## 7. Estado atual

- No ar em **rebecavaletich.github.io/diario-frotastico**, público, sem login.
- Atualiza sozinho todo dia, sem intervenção manual.
- Conteúdo é append-only — nada é apagado automaticamente, fica acumulando com a data original.
- Custo estimado de API (Claude Haiku 4.5): na faixa de poucos centavos de dólar por dia.
- Pendências conhecidas: agente de Startups/VC ainda não implementado; paginação ainda não existe nas páginas de listagem (hoje mostra tudo numa lista só — funciona bem com o volume atual, vira problema em alguns meses de acúmulo); upgrade do Astro (6→7) registrado como débito técnico, não urgente.
