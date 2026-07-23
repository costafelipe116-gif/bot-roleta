import os
import time
import json
import logging
import requests
from pathlib import Path
from datetime import datetime

# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8675857127:AAFvZAqEJhu5UJPY6v8t7Y3GTQJTxgI788g")
CHAT_ID = os.getenv("CHAT_ID", "5912926190")
FOOTBALL_DATA_KEY = os.getenv("FOOTBALL_DATA_KEY") or os.getenv("FOOTBALL_API_KEY", "db1b4be93bda49ab9f05fa9e20b994c1")

INTERVALO = 60
ARQUIVO_HISTORICO = "historico.json"
CACHE_MINUTOS = 3600

# 🔴 COLOQUE True PARA TESTAR O TELEGRAM AGORA (Mesmo sem jogos ao vivo)
# 🟢 COLOQUE False QUANDO QUISER DEIXAR RODANDO OFICIALMENTE
MODO_TESTE = True 

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

alertas = {}

def alerta_enviado(chave):
    agora = time.time()
    if chave in alertas:
        if agora - alertas[chave] < CACHE_MINUTOS:
            return True
    alertas[chave] = agora
    return False

def enviar_telegram(texto):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": texto,
        "parse_mode": "Markdown"
    }
    try:
        r = requests.post(url, json=payload, timeout=20)
        if r.status_code == 200:
            logging.info("✅ Mensagem enviada com sucesso ao Telegram!")
        else:
            logging.error(f"❌ Erro Telegram ({r.status_code}): {r.text}")
    except Exception as erro:
        logging.error(f"❌ Exceção Telegram: {erro}")

def buscar_jogos():
    url = "https://api.football-data.org/v4/matches"
    headers = {"X-Auth-Token": FOOTBALL_DATA_KEY}
    
    # Se MODO_TESTE for True, busca jogos agendados ou finalizados para testar
    params = {"status": "SCHEDULED,FINISHED"} if MODO_TESTE else {"status": "IN_PLAY"}

    try:
        resposta = requests.get(url, headers=headers, params=params, timeout=20)
        
        if resposta.status_code == 403:
            logging.error("❌ Erro 403: Chave da API inválida ou sem acesso a esta liga.")
            return []
        elif resposta.status_code != 200:
            logging.error(f"⚠️ Erro API ({resposta.status_code}): {resposta.text}")
            return []

        partidas = resposta.json().get("matches", [])
        jogos = []

        for jogo in partidas[:5]:  # Pega os primeiros 5 jogos para teste
            minuto = jogo.get("minute") or 30  # Simula 30 min se for teste
            casa = jogo.get("homeTeam", {}).get("name", "Casa")
            fora = jogo.get("awayTeam", {}).get("name", "Fora")
            
            score = jogo.get("score", {}).get("fullTime", {})
            gols_casa = score.get("home") if score.get("home") is not None else 0
            gols_fora = score.get("away") if score.get("away") is not None else 0

            jogos.append({
                "id": jogo.get("id"),
                "casa": casa,
                "fora": fora,
                "minuto": minuto,
                "gols_casa": gols_casa,
                "gols_fora": gols_fora,
                "liga": jogo.get("competition", {}).get("name", "Liga")
            })

        return jogos

    except Exception as erro:
        logging.error(f"❌ Erro de conexão com a API: {erro}")
        return []

def analisar_jogos():
    jogos = buscar_jogos()

    if not jogos:
        logging.info("📊 Nenhum jogo ao vivo nas 12 ligas grátis no momento.")
        return

    logging.info(f"🔎 {len(jogos)} jogo(s) encontrado(s) para análise.")

    for jogo in jogos:
        try:
            fixture_id = jogo["id"]
            casa = jogo["casa"]
            fora = jogo["fora"]
            minuto = jogo["minuto"]
            gols_casa = jogo["gols_casa"]
            gols_fora = jogo["gols_fora"]
            liga = jogo["liga"]

            # Em MODO_TESTE dispara um alerta genérico de teste
            if MODO_TESTE:
                estrategia = "🧪 MODO DE TESTE (Verificação de Bot)"
            else:
                estrategia = None
                if 25 <= minuto <= 40 and gols_casa == 0 and gols_fora == 0:
                    estrategia = "⚽ Over 0.5 HT (Gol no 1º Tempo)"
                elif minuto >= 50 and (gols_fora - gols_casa == 1):
                    estrategia = "🔥 Pressão Mandante (Buscando Empate)"
                elif minuto >= 80 and abs(gols_casa - gols_fora) <= 1:
                    estrategia = "🚩 Pressão Final (Over Limite)"

            if estrategia is None:
                continue

            chave = f"{fixture_id}-{estrategia}"

            if alerta_enviado(chave):
                continue

            mensagem = f"""🎯 *OPORTUNIDADE DETECTADA*

🏆 *{casa} x {fora}*
🏆 *Liga:* {liga}
⏱️ *Minuto:* {minuto}'
⚽ *Placar:* {gols_casa} x {gols_fora}

📊 *Estratégia:* {estrategia}

💡 *Confira a cotação na sua casa de apostas!*"""

            enviar_telegram(mensagem)

        except Exception as erro:
            logging.error(f"❌ Erro ao analisar jogo: {erro}")

if __name__ == "__main__":
    logging.info("🤖 Robô de Sinal Iniciado!")
    enviar_telegram("🤖 *Robô Atualizado!* Monitorando com logs detalhados.")

    while True:
        try:
            analisar_jogos()
        except Exception as erro:
            logging.error(f"❌ Erro no loop: {erro}")
        
        time.sleep(INTERVALO)
