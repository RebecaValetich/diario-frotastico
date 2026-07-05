"""
Agente: market-radar
Monitora mercado de frotas via Google News + blogs de concorrentes.
Gera 1 .md por notícia com hashtags para concorrentes.
"""

import os
import re
import json
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
import anthropic
from urllib.parse import quote, urljoin

load_dotenv()

TERMOS_MERCADO = [
    "gestão de frotas Brasil",
    "telemetria veicular",
    "rastreamento veicular startup",
    "indicação de condutor frota",
    "combustível caminhão preço",
    "fleet management technology",
    "mobilidade logística Brasil",
    "transporte carga tecnologia",
]

CONCORRENTES = [
    {"nome": "Cobli", "hashtag": "#Cobli", "blog": "https://cobli.co/blog", "news_termo": "Cobli frota"},
    {"nome": "Infleet", "hashtag": "#Infleet", "blog": "https://infleet.com.br/blog", "news_termo": "Infleet telemetria"},
    {"nome": "Brobot", "hashtag": "#Brobot", "blog": "https://www.brobot.com.br/blog", "news_termo": "Brobot frotas"},
    {"nome": "Geotab", "hashtag": "#Geotab", "blog": "https://www.geotab.com/blog/", "news_termo": "Geotab fleet"},
    {"nome": "Samsara", "hashtag": "#Samsara", "blog": "https://www.samsara.com/blog", "news_termo": "Samsara fleet management"},
    {"nome": "Fleet Complete", "hashtag": "#FleetComplete", "blog": "https://www.fleetcomplete.com/blog/", "news_termo": "Fleet Complete launch"},
]

# Veículos de imprensa especializados em transporte/logística/frotas
FONTES_MERCADO_GERAL = [
    {"nome": "Transporte Moderno", "rss": "https://transportemoderno.com.br/feed/"},
    {"nome": "Mundo Logística", "rss": "https://mundologistica.com.br/feed/"},
    {"nome": "Diário do Transporte", "rss": "https://diariodotransporte.com.br/feed/"},
]

def buscar_google_news(termo: str, max_items: int = 3) -> list:
    try:
        url = f"https://news.google.com/rss/search?q={quote(termo)}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        items = []
        for item in root.findall('.//item')[:max_items]:
            title = item.find('title')
            link = item.find('link')
            pub_date = item.find('pubDate')
            source = item.find('source')
            items.append({
                "titulo": title.text if title is not None else "",
                "link": link.text if link is not None else "",
                "data": pub_date.text if pub_date is not None else "",
                "fonte": source.text if source is not None else "Google News",
                "concorrente": None,
            })
        return items
    except Exception as e:
        print(f"   Erro ao buscar '{termo}': {e}")
        return []


def buscar_feed_mercado(fonte: dict) -> list:
    """Lê RSS diretamente de veículo especializado em transporte/frotas."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(fonte["rss"], headers=headers, timeout=12)
        response.raise_for_status()
        # Remove BOM e caracteres inválidos que quebram o XML
        conteudo = response.content.lstrip(b'\xef\xbb\xbf').lstrip(b'\xff\xfe').lstrip(b'\xfe\xff')
        root = ET.fromstring(conteudo)
        items = []
        for item in root.findall(".//item")[:10]:
            title = item.find("title")
            link = item.find("link")
            pub_date = item.find("pubDate")
            items.append({
                "titulo": title.text if title is not None else "",
                "link": link.text if link is not None else "",
                "data": pub_date.text if pub_date is not None else "",
                "fonte": fonte["nome"],
                "concorrente": None,
                "hashtag": None,
                "origem": "brasil",
            })
        print(f"   {fonte['nome']}: {len(items)} itens encontrados")
        return items
    except ET.ParseError:
        # Fallback: scraping direto da página de notícias
        print(f"   {fonte['nome']}: RSS inválido, tentando scraping...")
        return buscar_scraping(fonte)
    except Exception as e:
        print(f"   Erro ao buscar {fonte['nome']}: {e}")
        return []


def buscar_scraping(fonte: dict) -> list:
    """Scraping direto da página de notícias quando RSS falha."""
    try:
        url_noticias = fonte["rss"].replace("/feed/", "/noticias")
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url_noticias, headers=headers, timeout=12)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        items = []
        for tag in soup.find_all("h3")[:15]:
            a = tag.find("a")
            if not a:
                continue
            titulo = a.get_text(strip=True)
            link = a.get("href", "")
            if link and not link.startswith("http"):
                from urllib.parse import urljoin
                link = urljoin(url_noticias, link)
            if titulo and link:
                items.append({
                    "titulo": titulo,
                    "link": link,
                    "data": "",
                    "fonte": fonte["nome"],
                    "concorrente": None,
                    "hashtag": None,
                    "origem": "brasil",
                })
        print(f"   {fonte['nome']} (scraping): {len(items)} itens encontrados")
        return items
    except Exception as e:
        print(f"   Erro scraping {fonte['nome']}: {e}")
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


def buscar_blog(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)[:2000]
    except Exception as e:
        return f"Erro: {e}"


def buscar_blog_concorrente(concorrente: dict) -> list:
    """Busca posts direto no blog do concorrente — RSS se existir, senão scraping da listagem.
    Complementa (não substitui) a busca via Google News pelo mesmo concorrente."""
    blog_url = concorrente["blog"]
    headers = {"User-Agent": "Mozilla/5.0"}

    candidatos_rss = [
        blog_url.rstrip('/') + '/feed/',
        blog_url.rstrip('/') + '/rss/',
        blog_url.rstrip('/') + '/rss.xml',
    ]
    for rss_url in candidatos_rss:
        try:
            response = requests.get(rss_url, headers=headers, timeout=10)
            response.raise_for_status()
            conteudo = response.content.lstrip(b'\xef\xbb\xbf').lstrip(b'\xff\xfe').lstrip(b'\xfe\xff')
            root = ET.fromstring(conteudo)
            items = []
            for item in root.findall(".//item")[:10]:
                title = item.find("title")
                link = item.find("link")
                pub_date = item.find("pubDate")
                items.append({
                    "titulo": title.text if title is not None else "",
                    "link": link.text if link is not None else "",
                    "data": pub_date.text if pub_date is not None else "",
                    "fonte": concorrente["nome"],
                    "concorrente": concorrente["nome"],
                    "hashtag": concorrente["hashtag"],
                })
            if items:
                print(f"   {concorrente['nome']}: {len(items)} itens via RSS direto do blog")
                return items
        except Exception:
            continue

    # Fallback: scraping direto da página do blog (sem RSS disponível)
    try:
        response = requests.get(blog_url, headers=headers, timeout=12)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        items = []
        for tag in soup.find_all(["h2", "h3"])[:15]:
            a = tag.find("a")
            if not a:
                continue
            titulo = a.get_text(strip=True)
            link = a.get("href", "")
            if link and not link.startswith("http"):
                link = urljoin(blog_url, link)
            if titulo and link:
                items.append({
                    "titulo": titulo,
                    "link": link,
                    "data": "",
                    "fonte": concorrente["nome"],
                    "concorrente": concorrente["nome"],
                    "hashtag": concorrente["hashtag"],
                })
        print(f"   {concorrente['nome']} (scraping blog): {len(items)} itens encontrados")
        return items
    except Exception as e:
        print(f"   Erro ao buscar blog de {concorrente['nome']}: {e}")
        return []


def sintetizar_com_claude(noticias_mercado: list, noticias_concorrentes: list) -> list:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    texto_mercado = ""
    for i, n in enumerate(noticias_mercado):
        texto_mercado += f"\n[M{i}] TÍTULO: {n['titulo']}\n     FONTE: {n['fonte']}\n     DATA: {n['data']}\n     LINK: {n['link']}\n"

    texto_concorrentes = ""
    for n in noticias_concorrentes:
        texto_concorrentes += f"\n[C] CONCORRENTE: {n['concorrente']}\n    TÍTULO: {n['titulo']}\n    FONTE: {n['fonte']}\n    DATA: {n['data']}\n    LINK: {n['link']}\n"

    prompt = f"""Você é um analista de mercado especializado em gestão de frotas.

Hoje é {datetime.now().strftime('%d/%m/%Y')}.

Abaixo estão notícias de mercado e de concorrentes. Selecione as mais relevantes e retorne um JSON.

Critérios:
- Lançamentos de produto, captações, parcerias, inovações em frotas/telemetria/logística
- Máximo 8 notícias no total
- Eliminar duplicatas
- Para notícias de concorrentes: incluir o campo "hashtag" com o nome da empresa

Nesta etapa você só SELECIONA e CLASSIFICA — não escreva resumo. O resumo é gerado depois, com base no texto completo do artigo, pra nunca inventar informação a partir só do título.

IMPORTANTE: no campo "titulo", substitua qualquer aspas dupla interna por aspas simples.

Retorne APENAS um JSON válido, sem texto antes ou depois:
[
  {{
    "titulo": "título original",
    "fonte": "nome da fonte",
    "link": "url",
    "data": "data original",
    "hashtag": "#NomeConcorrente ou null se não for de concorrente",
    "origem": "brasil ou internacional",
    "tags": ["tag1", "tag2"]
  }}
]

Para o campo "tags": atribua 1 a 3 tags temáticas que descrevam o assunto da notícia.
Use termos específicos e reconhecíveis do setor, como:
Telemetria, Rastreamento, Combustível, Eletrificação, IA, Roteirização, CIOT, Retrofit,
Captação, Fusão, Parceria, Concorrência, Logística, Segurança, Regulação, Motorista, EV.

--- NOTÍCIAS DE MERCADO ---
{texto_mercado}

--- NOTÍCIAS DE CONCORRENTES ---
{texto_concorrentes}
"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )

    texto = message.content[0].text.strip()
    texto = re.sub(r'```json\s*', '', texto)
    texto = re.sub(r'```\s*', '', texto)
    # Remove caracteres de controle que quebram o JSON
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
    "use o link da fonte abaixo para ler a matéria na íntegra."
)
FALLBACK_DESCRICAO = "Conteúdo completo disponível apenas na fonte original."


def gerar_resumos_fieis(noticias: list) -> list:
    """Gera o resumo de cada notícia com base SOMENTE no texto extraído da página.
    Nunca infere a partir do título. Se não há texto extraído, ou o Claude sinaliza
    que o texto é insuficiente, marca scraping_falhou=True e o item cai no fallback."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    com_texto = [(i, n) for i, n in enumerate(noticias) if n.get("texto_completo")]

    for n in noticias:
        n["scraping_falhou"] = True

    if not com_texto:
        return noticias

    bloco = ""
    for i, n in com_texto:
        bloco += f"\n=== NOTÍCIA {i} ===\nTÍTULO: {n['titulo']}\nTEXTO EXTRAÍDO DA PÁGINA:\n{n['texto_completo']}\n"

    prompt = f"""Você vai escrever resumos de notícias sobre gestão de frotas, mobilidade e logística.

REGRAS ESTRITAS — siga à risca:
- Baseie-se EXCLUSIVAMENTE no texto extraído fornecido abaixo de cada notícia.
- NUNCA invente, infira, complete ou use conhecimento prévio sobre o assunto além do que está escrito no texto.
- Escreva o resumo mais completo e informativo possível dentro do que o texto realmente contém: números, datas, nomes, decisões, valores, mudanças específicas.
- Não repita a manchete sem agregar informação do corpo do texto.
- Se o texto extraído for insuficiente, cortado, for página de erro/paywall/cookie banner, ou não tiver informação real sobre a notícia, responda para aquele índice apenas: "INSUFICIENTE".

Retorne APENAS um JSON válido, sem texto antes ou depois:
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
    pasta = os.path.join(os.path.dirname(__file__), "..", "site", "frontend", "src", "content", "mercado")
    os.makedirs(pasta, exist_ok=True)

    salvos = 0
    for i, noticia in enumerate(noticias):
        slug = f"{hoje}-{i+1:02d}"
        caminho = os.path.join(pasta, f"{slug}.md")

        hashtag = noticia.get('hashtag') or ''
        hashtag_field = f'hashtag: "{hashtag}"' if hashtag else 'hashtag: ""'

        image_url = noticia.get('imageUrl', '')
        tags = noticia.get('tags', [])
        tags_yaml = '\n'.join([f'  - "{t}"' for t in tags]) if tags else ''
        tags_field = f'tags:\n{tags_yaml}' if tags_yaml else 'tags: []'

        scraping_falhou = noticia.get('scraping_falhou', True)
        corpo = FALLBACK_BODY if scraping_falhou else noticia.get('resumo', '')
        descricao = FALLBACK_DESCRICAO if scraping_falhou else noticia.get('resumo', '').replace('"', "'")[:160]

        conteudo = f"""---
title: "{noticia.get('titulo', '').replace('"', "'")}"
description: "{descricao.replace('"', "'")}"
pubDate: "{datetime.now().strftime('%Y-%m-%dT07:00:00Z')}"
fonte: "{noticia.get('fonte', '').replace('"', "'")}"
linkOriginal: "{noticia.get('link', '')}"
dataOriginal: "{noticia.get('data', '')}"
origem: "{noticia.get('origem', 'brasil')}"
imageUrl: "{image_url}"
{hashtag_field}
{tags_field}
---

{corpo}

{f'**{hashtag}**' if hashtag else ''}

**Fonte:** [{noticia.get('fonte', '')}]({noticia.get('link', '')})
"""
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(conteudo)
        salvos += 1

    print(f"✅ {salvos} notícias salvas em mercado/")
    return salvos


def main():
    print("🔍 market-radar iniciado...")

    # 1. Notícias gerais de mercado (Google News)
    noticias_mercado = []
    for termo in TERMOS_MERCADO:
        print(f"   Buscando mercado: '{termo}'...")
        noticias_mercado.extend(buscar_google_news(termo, max_items=5))

    # 2. Veículos especializados em transporte/frotas (RSS direto)
    print("   Buscando fontes especializadas...")
    for fonte in FONTES_MERCADO_GERAL:
        noticias_mercado.extend(buscar_feed_mercado(fonte))

    # 3. Notícias e blogs de concorrentes (Google News + blog direto de cada um)
    noticias_concorrentes = []
    for c in CONCORRENTES:
        print(f"   Buscando concorrente (Google News): {c['nome']}...")
        news = buscar_google_news(c['news_termo'], max_items=4)
        for n in news:
            n['concorrente'] = c['nome']
            n['hashtag'] = c['hashtag']
        noticias_concorrentes.extend(news)

        print(f"   Buscando concorrente (blog direto): {c['nome']}...")
        noticias_concorrentes.extend(buscar_blog_concorrente(c))

    print(f"   {len(noticias_mercado)} notícias de mercado, {len(noticias_concorrentes)} de concorrentes.")
    print("   Filtrando e sintetizando com Claude...")

    noticias_filtradas = sintetizar_com_claude(noticias_mercado, noticias_concorrentes)
    print(f"   {len(noticias_filtradas)} notícias relevantes selecionadas.")

    if noticias_filtradas:
        print("   Resolvendo URLs, buscando imagens e extraindo texto completo...")
        noticias_filtradas = [enriquecer_noticia(n) for n in noticias_filtradas]
        print("   Gerando resumos fiéis ao texto extraído...")
        noticias_filtradas = gerar_resumos_fieis(noticias_filtradas)
        salvar_noticias(noticias_filtradas)
        for n in noticias_filtradas:
            hashtag = f" {n.get('hashtag', '')}" if n.get('hashtag') else ""
            aviso = " [scraping falhou → fallback]" if n.get('scraping_falhou') else ""
            print(f"\n   • {n['titulo']}{hashtag}{aviso}")
    else:
        print("   Sem novidades relevantes hoje.")


if __name__ == "__main__":
    main()
