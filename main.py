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

INTERVALO = 60  # Varredura a cada 60 segundos
ARQUIVO_HISTORICO = "historico.json"
CACHE_MINUTOS = 3600  # Memória anti-spam de 1 hora

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ==========================================================
# CACHE ANTI-SPAM
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
# HISTÓRICO EM JSON
# ==========================================================

def carregar_historico():
    if not Path(ARQUIVO_HISTORICO).exists():
        return []
    try:
        with open(ARQUIVO_HISTORICO, "r", encoding="utf8") as f:
            return json.load(f)
    except:
        return []

def salvar_historico(dados):
    try:
        with open(ARQUIVO_HISTORICO, "w", encoding="utf8") as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
    except Exception as erro:
        logging.error(f"Erro ao salvar histórico: {erro}")

def registrar_sinal(casa, fora, estrategia, minuto, placar):
    historico = carregar_historico()
    historico.append({
        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "casa": casa,
        "fora": fora,
        "estrategia": estrategia,
        "minuto": minuto,
        "placar": placar
    })
    salvar_historico(historico)

# ==========================================================
# ENVIAR MENSAGEM NO TELEGRAM
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
            logging.info("✅ Alerta enviado ao Telegram!")
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
            logging.error(f"⚠️ Erro API Football Data ({resposta.status_code}): {resposta.text}")
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
        logging.error(f"❌ Erro de conexão: {erro}")
        return []

# ==========================================================
# ANALISAR ESTRATÉGIAS REAIS
# ==========================================================

def analisar_jogos():
    jogos = buscar_jogos()

    if not jogos:
        logging.info("📊 Nenhum jogo ao vivo nas ligas monitoradas no momento.")
        return

    logging.info(f"🔎 {len(jogos)} jogo(s) ao vivo sendo analisado(s)...")

    for jogo in jogos:
        try:
            fixture_id = jogo["id"]
            casa = jogo["casa"]
            fora = jogo["fora"]
            minuto = jogo["minuto"]
            gols_casa = jogo["gols_casa"]
            gols_fora = jogo["gols_fora"]
            liga = jogo["liga"]

            estrategia = None

            # 🎯 1. Pressão Over 0.5 HT (0x0 entre 25' e 40' min)
            if 25 <= minuto <= 40 and gols_casa == 0 and gols_fora == 0:
                estrategia = "⚽ Over 0.5 HT (Gol no 1º Tempo)"

            # 🎯 2. Reação / Virada no 2º Tempo (Casa perdendo por 1 gol após os 50' min)
            elif minuto >= 50 and (gols_fora - gols_casa == 1):
                estrategia = "🔥 Pressão Mandante (Buscando Empate/Virada)"

            # 🎯 3. Gol no Final / Over Limite (Jogo empatado ou 1 gol de dif. após 80' min)
            elif minuto >= 80 and abs(gols_casa - gols_fora) <= 1:
                estrategia = "🚩 Pressão Final (Over Limite / Cantos Finais)"

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
            registrar_sinal(casa, fora, estrategia, minuto, f"{gols_casa}x{gols_fora}")

        except Exception as erro:
            logging.error(f"❌ Erro ao processar partida {jogo.get('casa')}: {erro}")

# ==========================================================
# LOOP PRINCIPAL
# ==========================================================

if __name__ == "__main__":
    logging.info("🤖 Robô de Sinal Iniciado!")
    enviar_telegram("🤖 *Robô Atualizado e Online!* Monitorando partidas ao vivo com estratégias de placar e tempo.")

    while True:
        try:
            limpar_cache()
            analisar_jogos()
        except Exception as erro:
            logging.error(f"❌ Erro no loop: {erro}")
        
        time.sleep(INTERVALO)
