import os
import time
import json
import logging
import requests
from pathlib import Path
from datetime import datetime

# ==========================================================
# CONFIGURAÇÕES E CREDENCIAIS
# ==========================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8675857127:AAFvZAqEJhu5UJPY6v8t7Y3GTQJTxgI788g")
CHAT_ID = os.getenv("CHAT_ID", "5912926190")

FOOTBALL_DATA_KEY = os.getenv("FOOTBALL_DATA_KEY") or os.getenv("FOOTBALL_API_KEY", "db1b4be93bda49ab9f05fa9e20b994c1")

INTERVALO = 60  # Varredura a cada 1 minuto
ARQUIVO_HISTORICO = "historico.json"
CACHE_MINUTOS = 3600  # Memória anti-spam de 1 hora por jogo

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ==========================================================
# MEMÓRIA ANTI-SPAM
# ==========================================================

alertas = {}

def alerta_enviado(chave):
    agora = time.time()
    if chave in alertas:
        if agora - alertas[chave] < CACHE_MINUTOS:
            return True
    alertas[chave] = agora
    return False

def limpar_cache():
    agora = time.time()
    remover = [chave for chave, instante in alertas.items() if agora - instante > CACHE_MINUTOS]
    for chave in remover:
        del alertas[chave]

# ==========================================================
# DISPARO PARA O TELEGRAM
# ==========================================================

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
            logging.info("✅ Sinal enviado para o Telegram!")
        else:
            logging.error(f"❌ Erro Telegram ({r.status_code}): {r.text}")
    except Exception as erro:
        logging.error(f"❌ Exceção Telegram: {erro}")

# ==========================================================
# BUSCAR JOGOS AO VIVO
# ==========================================================

def buscar_jogos():
    url = "https://api.football-data.org/v4/matches"
    headers = {"X-Auth-Token": FOOTBALL_DATA_KEY}
    params = {"status": "IN_PLAY"}

    try:
        resposta = requests.get(url, headers=headers, params=params, timeout=20)
        if resposta.status_code != 200:
            logging.error(f"⚠️ API Error ({resposta.status_code}): {resposta.text}")
            return []

        partidas = resposta.json().get("matches", [])
        jogos = []

        for jogo in partidas:
            minuto = jogo.get("minute") or 0
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
        logging.error(f"❌ Erro na busca de partidas: {erro}")
        return []

# ==========================================================
# ANÁLISE DE ESTRATÉGIA ÚNICA (0x0 NO 2º TEMPO)
# ==========================================================

def analisar_jogos():
    jogos = buscar_jogos()

    if not jogos:
        logging.info("📊 Varrendo partidas ao vivo... (Nenhum jogo no momento)")
        return

    logging.info(f"🔎 Analisando {len(jogos)} jogo(s) ao vivo...")

    for jogo in jogos:
        try:
            fixture_id = jogo["id"]
            casa = jogo["casa"]
            fora = jogo["fora"]
            minuto = jogo["minuto"]
            gols_casa = jogo["gols_casa"]
            gols_fora = jogo["gols_fora"]
            liga = jogo["liga"]

            # 🎯 REGRA ÚNICA: 2º Tempo (entre 50' e 75' min) e Placar 0 x 0
            if 50 <= minuto <= 75 and gols_casa == 0 and gols_fora == 0:
                
                chave = f"{fixture_id}-over05-2ht"

                if alerta_enviado(chave):
                    continue

                mensagem = f"""🔥 *SINAL DETECTADO: OVER 0.5 GOLS*

🏆 *{casa} x {fora}*
🏆 *Liga:* {liga}
⏱️ *Minuto:* {minuto}' do 2º Tempo
⚽ *Placar Atual:* 0 x 0

📈 *Entrada Recomendada:* Over 0.5 Gols (Gol no jogo)
💰 *Odd Estimada:* ~1.50 a 1.70

💡 *O jogo está no 2º tempo com placar zerado. Excelente momento para buscar 1 gol!*"""

                enviar_telegram(mensagem)
                logging.info(f"🚀 Alerta enviado: {casa} x {fora} [{minuto}']")

        except Exception as erro:
            logging.error(f"❌ Erro ao analisar partida {jogo.get('casa')}: {erro}")

# ==========================================================
# LOOP PRINCIPAL
# ==========================================================

if __name__ == "__main__":
    logging.info("🤖 Bot de Sinal Over 0.5 2HT Iniciado!")
    enviar_telegram("🤖 *Bot Atualizado!* Focado exclusivamente em jogos 0x0 no 2º Tempo (Odd 1.50+).")

    while True:
        try:
            limpar_cache()
            analisar_jogos()
        except Exception as erro:
            logging.error(f"❌ Erro no loop: {erro}")
        
        time.sleep(INTERVALO)
