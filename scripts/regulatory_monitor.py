"""
Agente: regulatory-monitor
Monitora órgãos públicos brasileiros e gera briefing regulatório diário.
"""

import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
import anthropic

load_dotenv()

FONTES = [
    {"nome": "Serpro", "url": "https://www.serpro.gov.br/menu/noticias"},
    {"nome": "Senatran / Denatran", "url": "https://www.gov.br/transportes/pt-br/assuntos/noticias"},
    {"nome": "Governo Federal", "url": "https://www.gov.br/pt-br/noticias"},
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

def sintetizar_com_claude(conteudos: list) -> str:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    texto_fontes = ""
    for item in conteudos:
        texto_fontes += f"\n\n---\nFonte: {item['nome']} ({item['url']})\n{item['conteudo']}"

    prompt = f"""Você é um analista de mercado especializado em gestão de frotas e mobilidade no Brasil.

Abaixo está o conteúdo coletado de órgãos públicos brasileiros hoje ({datetime.now().strftime('%d/%m/%Y')}).

Sua tarefa:
1. Identificar apenas as novidades regulatórias relevantes para o setor de gestão de frotas, transporte e mobilidade
2. Ignorar conteúdo genérico, institucional ou sem novidade prática
3. Para cada item relevante, escrever 2-3 frases: o que mudou + por que importa para frotas
4. Se não houver nada relevante, dizer claramente "Sem novidades regulatórias relevantes nas últimas 48h."

Formato de saída (markdown):
## 🇧🇷 Regulatório

### [Título curto]
[2-3 frases explicando o que aconteceu e por que importa para frotas]
Fonte: [Nome da fonte] | [URL]

Máximo 3 itens. Seja objetivo e direto.

--- CONTEÚDO COLETADO ---
{texto_fontes}
"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

def salvar_output(conteudo: str):
    hoje = datetime.now().strftime("%Y-%m-%d")
    hoje_formatado = datetime.now().strftime("%d/%m/%Y")
    data_iso = datetime.now().strftime("%Y-%m-%dT07:00:00Z")
    pasta = os.path.join(os.path.dirname(__file__), "..", "site", "frontend", "src", "content", "orgaos-publicos")
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, f"{hoje}.md")

    post_completo = f"""---
title: "Órgãos Públicos — {hoje_formatado}"
description: "Atualizações regulatórias de Serpro, Senatran e Governo Federal"
pubDate: "{data_iso}"
---

{conteudo}
"""

    with open(caminho, "w", encoding="utf-8") as f:
        f.write(post_completo)

    print(f"✅ Salvo em: {caminho}")
    return caminho

def main():
    print("🔍 regulatory-monitor iniciado...")
    conteudos = []
    for fonte in FONTES:
        print(f"   Acessando {fonte['nome']}...")
        conteudo = buscar_conteudo(fonte["url"])
        conteudos.append({"nome": fonte["nome"], "url": fonte["url"], "conteudo": conteudo})

    print("   Sintetizando com Claude...")
    briefing = sintetizar_com_claude(conteudos)
    salvar_output(briefing)
    print("\n📋 Resultado:")
    print(briefing)

if __name__ == "__main__":
    main()
