# Pendências Técnicas

> Débitos técnicos identificados, não urgentes. Revisar periodicamente.

---

## 2026-07-04 — Upgrade Astro 6 → 7

**Contexto**: `npm audit` no `site/frontend` acusa 2 vulnerabilidades (1 alta, 1 baixa):

- **Astro (alta)**: XSS via atributos não escapados em spread props ([GHSA-jrpj-wcv7-9fh9](https://github.com/advisories/GHSA-jrpj-wcv7-9fh9)) e SSRF via header Host em prerendered error page ([GHSA-2pvr-wf23-7pc7](https://github.com/advisories/GHSA-2pvr-wf23-7pc7)).
- **esbuild (baixa)**: leitura arbitrária de arquivo no dev server em Windows ([GHSA-g7r4-m6w7-qqqr](https://github.com/advisories/GHSA-g7r4-m6w7-qqqr)).

**Por que não é urgente**:
- Site roda `output` estático, sem adapter — o vetor de SSRF (server/SSR) não se aplica.
- Conteúdo vem só dos scripts Python internos, não há input de usuário via spread props.
- Vulnerabilidade do esbuild é dev-only e específica de Windows; ambiente de dev é Mac.

**Por que não corrigir agora**: `npm audit fix` sozinho não resolve — as CVEs cobrem toda a linha 6.x. O fix real exige major bump pra Astro 7.0.6, que pode quebrar content collections/integrações (mdx, sitemap) e precisa de teste dedicado.

**Próximo passo**: agendar upgrade pro Astro 7 como tarefa isolada, com teste de build completo antes de merge. Não misturar com outras correções.

**Status**: aberto.
