"""
Agente: regulatory-monitor
Busca notícias regulatórias via Google News e gera um .md por notícia.
"""

import os
import re
import json
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from dateutil import parser as date_parser
from dotenv import load_dotenv
import anthropic
from urllib.parse import quote

load_dotenv()

JANELA_HORAS = 24  # só considera notícias publicadas nas últimas N horas


def dentro_da_janela(data_str: str, horas: int = JANELA_HORAS) -> bool:
    """Retorna True se a notícia foi publicada dentro da janela de recência.
    Se a data não vier preenchida ou não for parseável, deixa passar (não exclui às cegas)."""
    if not data_str:
        return True
    try:
        data_pub = date_parser.parse(data_str)
        if data_pub.tzinfo is None:
            data_pub = data_pub.replace(tzinfo=timezone.utc)
        agora = datetime.now(timezone.utc)
        delta_horas = (agora - data_pub).total_seconds() / 3600
        return delta_horas <= horas
    except Exception:
        return True


FONTES_OFICIAIS = [
    {
        "nome": "ANTT",
        "rss": "https://www.gov.br/antt/pt-br/@@atom.xml",
    },
    {
        "nome": "Senatran",
        "rss": "https://www.gov.br/senatran/pt-br/@@atom.xml",
    },
    {
        "nome": "Ministério dos Transportes",
        "rss": "https://www.gov.br/transportes/pt-br/@@atom.xml",
    },
    {
        "nome": "CONTRAN",
        "rss": "https://www.gov.br/senatran/pt-br/assuntos/contran/@@atom.xml",
    },
    {
        "nome": "GOV.BR Trânsito e Transporte",
        "rss": "https://www.gov.br/pt-br/noticias/transito-e-transportes/@@atom.xml",
    },
]

def buscar_feed_oficial(fonte: dict) -> list:
    """Lê feed Atom/RSS diretamente do site oficial."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(fonte["rss"], headers=headers, timeout=12)
        response.raise_for_status()

        # Suporte a Atom e RSS
        root = ET.fromstring(response.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        items = []

        # Tenta Atom
        entries = root.findall("atom:entry", ns)
        if entries:
            for entry in entries[:15]:
                title = entry.find("atom:title", ns)
                link_el = entry.find("atom:link", ns)
                updated = entry.find("atom:updated", ns)
                link = link_el.get("href", "") if link_el is not None else ""
                items.append({
                    "titulo": title.text if title is not None else "",
                    "link": link,
                    "data": updated.text if updated is not None else "",
                    "fonte": fonte["nome"],
                })
        else:
            # Tenta RSS
            for item in root.findall(".//item")[:15]:
                title = item.find("title")
                link = item.find("link")
                pub_date = item.find("pubDate")
                items.append({
                    "titulo": title.text if title is not None else "",
                    "link": link.text if link is not None else "",
                    "data": pub_date.text if pub_date is not None else "",
                    "fonte": fonte["nome"],
                })

        print(f"   {fonte['nome']}: {len(items)} itens encontrados")
        return items

    except Exception as e:
        print(f"   Erro ao buscar {fonte['nome']}: {e}")
        return []


def enriquecer_noticia(noticia: dict) -> dict:
    """Resolve URL real, extrai imagem OG e o texto completo do artigo (insumo pro resumo fiel)."""
    url = noticia.get("link", "")
    noticia["texto_completo"] = None
    if not url:
        return noticia
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"},
                                allow_redirects=True, timeout=10)
        response.raise_for_status()
        noticia["link"] = response.url

        # Se o link não saiu de news.google.com, é a página wrapper do Google
        # (redirect via JS que o requests não segue) — não é o artigo real.
        # Nesse caso não extraímos nem imagem nem texto, pra não publicar
        # o ícone genérico do Google ou um texto que não é da matéria.
        link_resolveu = "news.google.com" not in response.url

        if link_resolveu:
            soup = BeautifulSoup(response.text, "html.parser")

            og = soup.find("meta", property="og:image")
            if og and og.get("content"):
                noticia["imageUrl"] = og["content"]

            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "iframe", "noscript"]):
                tag.decompose()
            container = soup.find("article") or soup
            paragrafos = [p.get_text(" ", strip=True) for p in container.find_all("p")]
            texto = "\n".join(p for p in paragrafos if len(p) > 40).strip()
            if len(texto) >= 300:
                noticia["texto_completo"] = texto[:8000]
    except Exception:
        pass
    return noticia


def sintetizar_com_claude(noticias: list) -> list:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    texto_noticias = ""
    for i, n in enumerate(noticias):
        texto_noticias += f"\n[{i}] TITULO: {n['titulo']}\n    FONTE: {n['fonte']}\n    DATA: {n['data']}\n    LINK: {n['link']}\n"

    prompt = f"""Voce e um analista especializado em regulacao de transporte e frotas no Brasil.

Abaixo estao titulos de noticias sobre regulacao, legislacao e normas do setor de transporte.

Selecione APENAS noticias em que o SUJEITO DA ACAO e um orgao publico oficial: ANTT, CONTRAN, Senatran, DENATRAN, Ministerio dos Transportes, Governo Federal, Diario Oficial, Detran estadual ou orgao equivalente.

REJEITAR obrigatoriamente:
- Analises, opinioes ou reportagens de veiculos privados (Diario do Transporte, Logweb, etc.) que comentam sobre o setor sem anunciar ato oficial
- Noticias de empresas privadas, sindicatos ou associacoes (mesmo que relacionadas a transporte)
- Conteudo de mercado, tecnologia ou competidores

ACEITAR apenas:
- Resolucoes, portarias, instrucoes normativas publicadas por orgaos oficiais
- Alteracoes em CNH, multas, tabelas de frete definidas por orgao regulador
- Decisoes administrativas com impacto direto na operacao de frotas

Regras adicionais:
- Maximo 8 noticias
- Eliminar duplicatas

Nesta etapa voce so SELECIONA e CLASSIFICA — nao escreva resumo. O resumo e gerado depois, com base no texto completo do ato oficial, pra nunca inventar informacao a partir so do titulo.

IMPORTANTE: no campo "titulo", substitua qualquer aspas dupla interna por aspas simples.

Retorne APENAS o JSON abaixo, sem nenhum texto antes ou depois:
[
  {{
    "titulo": "titulo original",
    "fonte": "nome da fonte",
    "link": "url",
    "data": "data original",
    "tags": ["tag1", "tag2"]
  }}
]

Para o campo "tags": atribua 1 a 3 tags que descrevam o tipo de ato e o tema.
Use termos como: Resolução, Portaria, CNH, Multas, Free Flow, CIOT, Retrofit,
Pedágio, Rastreamento, Peso, Dimensões, Habilitação, Fiscalização, Frete.

NOTICIAS:
{texto_noticias}"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )

    texto = message.content[0].text.strip()
    texto = re.sub(r'```json\s*', '', texto)
    texto = re.sub(r'```\s*', '', texto)
    texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', texto)
    try:
        inicio = texto.find('[')
        fim = texto.rfind(']') + 1
        if inicio >= 0 and fim > inicio:
            return json.loads(texto[inicio:fim])
        return []
    except Exception as e:
        print(f"   Erro ao parsear JSON: {e}")
        print(f"   Resposta (primeiros 500 chars): {texto[:500]}")
        return []


FALLBACK_BODY = (
    "**Esta notícia deve ser acessada diretamente no site de origem.** "
    "Não foi possível carregar o conteúdo completo automaticamente para gerar um resumo fiel — "
    "use o link da fonte abaixo para ler o ato oficial na íntegra."
)
FALLBACK_DESCRICAO = "Conteúdo completo disponível apenas na fonte original."


def gerar_resumos_fieis(noticias: list) -> list:
    """Gera o resumo de cada noticia com base SOMENTE no texto extraido da pagina.
    Nunca infere a partir do titulo. Se nao ha texto extraido, ou o Claude sinaliza
    que o texto e insuficiente, marca scraping_falhou=True e o item cai no fallback."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    com_texto = [(i, n) for i, n in enumerate(noticias) if n.get("texto_completo")]

    for n in noticias:
        n["scraping_falhou"] = True

    if not com_texto:
        return noticias

    bloco = ""
    for i, n in com_texto:
        bloco += f"\n=== NOTICIA {i} ===\nTITULO: {n['titulo']}\nTEXTO EXTRAIDO DA PAGINA:\n{n['texto_completo']}\n"

    prompt = f"""Voce vai escrever resumos de atos oficiais sobre regulacao de transporte e frotas no Brasil.

REGRAS ESTRITAS — siga a risca:
- Baseie-se EXCLUSIVAMENTE no texto extraido fornecido abaixo de cada noticia.
- NUNCA invente, infira, complete ou use conhecimento previo sobre o assunto alem do que esta escrito no texto.
- Escreva o resumo mais completo e informativo possivel dentro do que o texto realmente contem: numeros, datas, artigos, valores, prazos, mudancas especificas.
- Nao repita a manchete sem agregar informacao do corpo do texto.
- Se o texto extraido for insuficiente, cortado, for pagina de erro/paywall/cookie banner, ou nao tiver informacao real sobre o ato, responda para aquele indice apenas: "INSUFICIENTE".

Retorne APENAS um JSON valido, sem texto antes ou depois:
[
  {{"indice": 0, "resumo": "resumo fiel de 8-12 frases, ou 'INSUFICIENTE'"}}
]

{bloco}
"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=6000,
        messages=[{"role": "user", "content": prompt}]
    )

    texto = message.content[0].text.strip()
    texto = re.sub(r'```json\s*', '', texto)
    texto = re.sub(r'```\s*', '', texto)
    texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', texto)

    resultados = {}
    try:
        inicio = texto.find('[')
        fim = texto.rfind(']') + 1
        if inicio >= 0 and fim > inicio:
            for item in json.loads(texto[inicio:fim]):
                resultados[item.get("indice")] = item.get("resumo", "")
    except Exception as e:
        print(f"   Erro ao parsear resumos: {e}")

    for i, n in enumerate(noticias):
        resumo = resultados.get(i, "")
        if n.get("texto_completo") and resumo and resumo.strip().upper() != "INSUFICIENTE":
            n["resumo"] = resumo
            n["scraping_falhou"] = False

    return noticias


def salvar_noticias(noticias: list):
    hoje = datetime.now().strftime("%Y-%m-%d")
    pasta = os.path.join(os.path.dirname(__file__), "..", "site", "frontend", "src", "content", "orgaos-publicos")
    os.makedirs(pasta, exist_ok=True)

    salvos = 0
    for i, noticia in enumerate(noticias):
        slug = f"{hoje}-{i+1:02d}"
        caminho = os.path.join(pasta, f"{slug}.md")

        titulo = noticia.get('titulo', '').replace('"', "'")
        fonte = noticia.get('fonte', '').replace('"', "'")

        scraping_falhou = noticia.get('scraping_falhou', True)
        corpo = FALLBACK_BODY if scraping_falhou else noticia.get('resumo', '')
        descricao = FALLBACK_DESCRICAO if scraping_falhou else noticia.get('resumo', '').replace('"', "'")[:160]

        image_url = noticia.get('imageUrl', '')
        tags = noticia.get('tags', [])
        tags_yaml = '\n'.join([f'  - "{t}"' for t in tags]) if tags else ''
        tags_field = f'tags:\n{tags_yaml}' if tags_yaml else 'tags: []'
        conteudo = f"""---
title: "{titulo}"
description: "{descricao.replace('"', "'")}"
pubDate: "{datetime.now().strftime('%Y-%m-%dT07:00:00Z')}"
fonte: "{fonte}"
linkOriginal: "{noticia.get('link', '')}"
dataOriginal: "{noticia.get('data', '')}"
imageUrl: "{image_url}"
{tags_field}
---

{corpo}

**Fonte:** [{noticia.get('fonte', '')}]({noticia.get('link', '')})
"""
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(conteudo)
        salvos += 1

    print(f"✅ {salvos} noticias salvas em orgaos-publicos/")
    return salvos


TERMOS_FALLBACK = [
    "site:gov.br ANTT resolução portaria 2026",
    "site:gov.br CONTRAN resolução 2026",
    "site:gov.br Senatran instrução normativa 2026",
    "site:gov.br transportes portaria 2026",
    "ANTT resolução portaria junho 2026",
    "CONTRAN resolução junho 2026",
]

def main():
    print("🔍 regulatory-monitor iniciado...")

    todas = []
    for fonte in FONTES_OFICIAIS:
        print(f"   Buscando: {fonte['nome']}...")
        noticias = buscar_feed_oficial(fonte)
        todas.extend(noticias)

    print(f"   {len(todas)} itens dos feeds. Complementando com Google News...")
    for termo in TERMOS_FALLBACK:
            print(f"   Buscando: '{termo}'...")
            url = f"https://news.google.com/rss/search?q={quote(termo)}&hl=pt-BR&gl=BR&ceid=BR:pt-419&tbs=qdr:m"
            headers = {"User-Agent": "Mozilla/5.0"}
            try:
                response = requests.get(url, headers=headers, timeout=10)
                root = ET.fromstring(response.content)
                for item in root.findall('.//item')[:5]:
                    title = item.find('title')
                    link = item.find('link')
                    pub_date = item.find('pubDate')
                    source = item.find('source')
                    todas.append({
                        "titulo": title.text if title is not None else "",
                        "link": link.text if link is not None else "",
                        "data": pub_date.text if pub_date is not None else "",
                        "fonte": source.text if source is not None else "GOV.BR",
                    })
            except Exception as e:
                print(f"   Erro: {e}")

    print(f"   {len(todas)} itens coletados no total (feeds + Google News).")

    print(f"   Filtrando por recência (últimas {JANELA_HORAS}h)...")
    antes = len(todas)
    todas = [n for n in todas if dentro_da_janela(n.get('data', ''))]
    print(f"   {antes - len(todas)} descartados por serem antigos.")

    print("   Filtrando e sintetizando com Claude...")

    noticias_filtradas = sintetizar_com_claude(todas)
    print(f"   {len(noticias_filtradas)} noticias relevantes selecionadas.")

    if noticias_filtradas:
        print("   Resolvendo URLs, buscando imagens e extraindo texto completo...")
        noticias_filtradas = [enriquecer_noticia(n) for n in noticias_filtradas]
        print("   Gerando resumos fieis ao texto extraido...")
        noticias_filtradas = gerar_resumos_fieis(noticias_filtradas)
        salvar_noticias(noticias_filtradas)
        for n in noticias_filtradas:
            aviso = " [scraping falhou -> fallback]" if n.get('scraping_falhou') else ""
            print(f"\n   - {n['titulo']}{aviso}")
    else:
        print("   Sem novidades regulatorias relevantes hoje.")


if __name__ == "__main__":
    main()
