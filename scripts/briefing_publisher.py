"""
Agente: briefing-publisher
Consolida os outputs dos agentes e publica o briefing diário final.
"""

import os
from datetime import datetime
from dotenv import load_dotenv
import anthropic

load_dotenv()


def ler_tmp(prefixo: str, hoje: str) -> str:
    """Lê o arquivo temporário de um agente."""
    pasta = os.path.join(os.path.dirname(__file__), "..", "site", "frontend", "src", "content", "blog", "tmp")
    caminho = os.path.join(pasta, f"{prefixo}-{hoje}.md")

    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            return f.read()
    return f"## {prefixo}\nSem dados disponíveis hoje."


def gerar_destaque_com_claude(conteudo_completo: str) -> str:
    """Pede ao Claude para escolher o destaque do dia."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    prompt = f"""Você é um analista sênior de produto especializado em gestão de frotas.

Abaixo está o briefing de mercado de hoje. Sua tarefa é escrever o "Destaque do dia": 
- 1 parágrafo curto (3-4 frases)
- O item mais relevante e impactante do dia
- Por que especificamente importa para uma empresa de gestão de frotas no Brasil

Se não houver nenhum item relevante, escreva: "Nenhum destaque relevante hoje."

--- BRIEFING ---
{conteudo_completo}
"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text


def salvar_briefing_final(conteudo: str, hoje: str):
    """Salva o briefing final em site/posts/."""
    pasta = os.path.join(os.path.dirname(__file__), "..", "site", "frontend", "src", "content", "blog")
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, f"{hoje}.md")

    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo)

    print(f"✅ Briefing final salvo em: {caminho}")
    return caminho


def limpar_tmp(hoje: str):
    """Remove os arquivos temporários após publicar."""
    pasta = os.path.join(os.path.dirname(__file__), "..", "site", "frontend", "src", "content", "blog", "tmp")
    for prefixo in ["regulatory", "market", "vc"]:
        caminho = os.path.join(pasta, f"{prefixo}-{hoje}.md")
        if os.path.exists(caminho):
            os.remove(caminho)
            print(f"   🗑️  Removido: {prefixo}-{hoje}.md")


def main():
    print("📰 briefing-publisher iniciado...")
    hoje = datetime.now().strftime("%Y-%m-%d")
    hoje_formatado = datetime.now().strftime("%d/%m/%Y")

    # 1. Lê os outputs dos agentes
    print("   Lendo outputs dos agentes...")
    regulatorio = ler_tmp("regulatory", hoje)
    mercado = ler_tmp("market", hoje)
    vc = "## 📊 Startups / VC\n\n_Em breve — agente em desenvolvimento._"

    # 2. Monta o conteúdo completo
    conteudo_completo = f"{regulatorio}\n\n{mercado}"

    # 3. Gera o destaque do dia
    print("   Gerando destaque do dia...")
    destaque = gerar_destaque_com_claude(conteudo_completo)

    # 4. Monta o briefing final com frontmatter para o Astro
    data_iso = datetime.now().strftime("%Y-%m-%dT07:00:00Z")
    briefing_final = f"""---
title: "Briefing de Mercado — {hoje_formatado}"
description: "Inteligência de mercado diária: frotas, mobilidade e regulação"
pubDate: "{data_iso}"
---

{regulatorio}

---

{mercado}

---

{vc}

---

## 💡 Destaque do dia

{destaque}
"""

    # 5. Salva o briefing final
    salvar_briefing_final(briefing_final, hoje)

    # 6. Limpa os arquivos temporários
    print("   Limpando arquivos temporários...")
    limpar_tmp(hoje)

    print("\n✅ Briefing publicado com sucesso!")
    print(f"   Arquivo: site/posts/{hoje}.md")


if __name__ == "__main__":
    main()
