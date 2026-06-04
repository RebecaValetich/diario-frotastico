# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

A market intelligence agent that runs daily, collects news about **fleet management**, **mobility**, and **startups/VC** (Brazil-focused and global), synthesizes it using an LLM, and publishes a daily briefing to a static website.

## Intended Architecture

### Pipeline (runs daily via cron/GitHub Actions)
1. **Fetch** — collect articles from RSS feeds, news APIs, and web scraping
2. **Filter & deduplicate** — drop noise, surface relevant stories per topic cluster
3. **Synthesize** — call Claude API to produce a structured briefing (headlines, summaries, signal/noise annotation)
4. **Publish** — render briefing as a static HTML page and deploy (e.g., GitHub Pages, Netlify)

### Key topic clusters
- Fleet management & telematics (Brazil and global)
- Mobility (EVs, ride-hailing, logistics, MaaS)
- Startups & VC activity in Brazil

### Expected tech stack (to be finalized)
- **Agent**: Python, using the Anthropic SDK (`anthropic`) with prompt caching for repeated context
- **Scheduling**: GitHub Actions (`schedule: cron`) or a lightweight cron runner
- **Static site**: Hugo, Jekyll, or plain HTML templated with Jinja2
- **Sources**: RSS feeds, Google News RSS, NewsAPI, or direct scraping

## Development Conventions (once established)

_Fill in as the project takes shape:_

- How to run the pipeline locally: `TBD`
- How to run tests: `TBD`
- How to build/preview the static site: `TBD`
- Required environment variables: `TBD` (e.g., `ANTHROPIC_API_KEY`, `NEWS_API_KEY`)

## Notes

- Briefings are append-only — never modify or delete past published pages
- The synthesis step should use Claude with prompt caching; the system prompt (topic definitions, formatting instructions) is stable across runs and should be cached
- Prefer RSS/free sources over paid APIs where coverage is adequate
