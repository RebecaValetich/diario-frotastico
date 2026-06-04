"""
Agente: market-radar
Monitora concorrentes nacionais e internacionais de gestão de frotas.
"""

import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
import anthropic

load_dotenv()

FONTES_NACIONAL = [
    {"nome": "Brobot", "url": "https://www.brobot.com.br/blog"},
    {"nome": "Cobli", "url": "https://cobli.co/blog"},
    {"nome": "Infleet", "url": "https://infleet.com.br/blog"},
]

FONTES_INTERNACIONAL = [
    {"nome": "Geotab", "url": "https://www.geotab.com/blog/"},
    {"nome": "Samsara", "url": "https://www.samsara.com/blog"},
    {"nome": "Transport Topics", "url": "https://www.ttnews.com/latest"},
    {"nome": "Logistics Management", "url": "https://www.logisticsmgmt.com/topic/news"},
    {"nome": "Fleet Complete", "url": "https://www.fleetcomplete.com/blog/"},
]

def buscar_conteudo(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        texto = soup.get_text(separator="\n", strip=True)
        return texto[:3000]
    except Exception as e:
        return f"Erro ao acessar {url}: {e}"

def sintetizar_com_claude(conteudos_nacional: list, conteudos_internacional: list) -> str:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    texto_nacional = ""
    for item in conteudos_nacional:
        texto_nacional += f"\n\n---\nFonte: {item['nome']} ({item['url']})\n{item['conteudo']}"

    texto_internacional = ""
    for item in conteudos_internacional:
        texto_internacional += f"\n\n---\nFonte: {item['nome']} ({item['url']})\n{item['conteudo']}"

    prompt = f"""Você é um analista de mercado especializado em gestão de frotas e mobilidade.

Hoje é {datetime.now().strftime('%d/%m/%Y')}. Abaixo está conteúdo coletado de concorrentes e players do setor.

Sua tarefa:
1. Identificar apenas novidades reais: lançamentos de produto, novas parcerias, movimentos estratégicos, inovações tecnológicas
2. Ignorar conteúdo de marketing genérico, cases antigos ou opinião sem fato novo
3. Para cada item relevante: 2-3 frases explicando o que aconteceu + por que importa para o setor de frotas
4. Se não houver nada relevante em uma seção, escrever "Sem novidades relevantes nas últimas 48h."

Formato de saída (markdown):
## 🏢 Mercado Nacional

### [Título curto]
[2-3 frases: o que aconteceu + por que importa para frotas]
Fonte: [Nome] | [URL]

## 🌍 Mercado Internacional

### [Título curto]
[2-3 frases: o que aconteceu + por que importa para frotas]
Fonte: [Nome] | [URL]

Máximo 3 itens por seção. Seja direto e objetivo.

--- FONTES NACIONAIS ---
{texto_nacional}

--- FONTES INTERNACIONAIS ---
{texto_internacional}
"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

def salvar_output(conteudo: str):
    hoje = datetime.now().strftime("%Y-%m-%d")
    hoje_formatado = datetime.now().strftime("%d/%m/%Y")
    data_iso = datetime.now().strftime("%Y-%m-%dT07:00:00Z")
    pasta = os.path.join(os.path.dirname(__file__), "..", "site", "frontend", "src", "content", "mercado")
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, f"{hoje}.md")

    post_completo = f"""---
title: "Mercado — {hoje_formatado}"
description: "Movimentos de concorrentes nacionais e internacionais em gestão de frotas"
pubDate: "{data_iso}"
---

{conteudo}
"""

    with open(caminho, "w", encoding="utf-8") as f:
        f.write(post_completo)

    print(f"✅ Salvo em: {caminho}")
    return caminho

def main():
    print("🔍 market-radar iniciado...")

    conteudos_nacional = []
    for fonte in FONTES_NACIONAL:
        print(f"   Acessando {fonte['nome']}...")
        conteudo = buscar_conteudo(fonte["url"])
        conteudos_nacional.append({**fonte, "conteudo": conteudo})

    conteudos_internacional = []
    for fonte in FONTES_INTERNACIONAL:
        print(f"   Acessando {fonte['nome']}...")
        conteudo = buscar_conteudo(fonte["url"])
        conteudos_internacional.append({**fonte, "conteudo": conteudo})

    print("   Sintetizando com Claude...")
    briefing = sintetizar_com_claude(conteudos_nacional, conteudos_internacional)
    salvar_output(briefing)
    print("\n📋 Resultado:")
    print(briefing)

if __name__ == "__main__":
    main()
