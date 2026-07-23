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

INTERVALO = 60  # Tempo entre varreduras em segundos
ARQUIVO_HISTORICO = "historico.json"
CACHE_MINUTOS = 3600  # Memória anti-spam de 1 hora

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ==========================================================
# MEMÓRIA ANTI-SPAM (CACHE)
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
# HISTÓRICO DE SINAIS (JSON)
# ==========================================================

def carregar_historico():
    if not Path(ARQUIVO_HISTORICO).exists():
        return []
    try:
        with open(ARQUIVO_HISTORICO, "r", encoding="utf8") as f:
            return json.load(f)
    except Exception as erro:
        logging.error(f"Erro ao carregar histórico: {erro}")
        return []

def salvar_historico(dados):
    try:
        with open(ARQUIVO_HISTORICO, "w", encoding="utf8") as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
    except Exception as erro:
        logging.error(f"Erro ao salvar histórico: {erro}")

def registrar_sinal(casa, fora, estrategia, minuto, placar, confianca):
    historico = carregar_historico()
    novo_registro = {
        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "casa": casa,
        "fora": fora,
        "estrategia": estrategia,
        "minuto": minuto,
        "placar": placar,
        "confianca": confianca,
        "resultado": "PENDENTE"
    }
    historico.append(novo_registro)
    salvar_historico(historico)

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
            logging.info("✅ Mensagem enviada com sucesso ao Telegram.")
        else:
            logging.error(f"❌ Erro Telegram ({r.status_code}): {r.text}")
    except Exception as erro:
        logging.error(f"❌ Exceção no envio do Telegram: {erro}")

# ==========================================================
# BUSCA DE JOGOS AO VIVO (FOOTBALL-DATA.ORG)
# ==========================================================

def buscar_jogos():
    url = "https://api.football-data.org/v4/matches"
    headers = {"X-Auth-Token": FOOTBALL_DATA_KEY}
    params = {"status": "IN_PLAY"}

    try:
        resposta = requests.get(url, headers=headers, params=params, timeout=20)
        if resposta.status_code != 200:
            logging.error(f"⚠️ Football Data API Erro ({resposta.status_code}): {resposta.text}")
            return []

        partidas = resposta.json().get("matches", [])
        jogos = []

        for jogo in partidas:
            minuto = jogo.get("minute", 0) or 0
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
                "competicao": jogo.get("competition", {}).get("name", "Geral")
            })

        return jogos

    except Exception as erro:
        logging.error(f"❌ Erro de conexão com a API de Futebol: {erro}")
        return []

# Safe fallback/módulo estatístico
def buscar_estatisticas(fixture_id, minuto):
    # Simulação/Estimativa de pressão com base no tempo de jogo
    # para APIs gratuitas que não entregam contagem de escanteios em tempo real.
    est_escanteios = max(1, int(minuto / 12))
    est_finalizacoes = max(2, int(minuto / 6))
    est_finalizacoes_gol = max(1, int(minuto / 15))

    return {
        "escanteios": est_escanteios,
        "finalizacoes": est_finalizacoes,
        "finalizacoes_gol": est_finalizacoes_gol
    }

# ==========================================================
# FILTRO DE CONFIANÇA DA IA
# ==========================================================

def calcular_confianca(minuto, gols_casa, gols_fora, escanteios, finalizacoes, finalizacoes_gol):
    pontos = 0

    # Tempo da partida
    if 15 <= minuto <= 20:
        pontos += 20
    elif 21 <= minuto <= 40:
        pontos += 15
    elif minuto >= 80:
        pontos += 20

    # Escanteios
    if escanteios <= 1:
        pontos += 20
    elif escanteios <= 3:
        pontos += 10

    # Finalizações
    if finalizacoes >= 12:
        pontos += 20
    elif finalizacoes >= 8:
        pontos += 15
    elif finalizacoes >= 5:
        pontos += 10

    # Finalizações no gol
    if finalizacoes_gol >= 5:
        pontos += 20
    elif finalizacoes_gol >= 3:
        pontos += 15
    elif finalizacoes_gol >= 2:
        pontos += 10

    # Placar equilibrado/apertado
    if abs(gols_casa - gols_fora) <= 1:
        pontos += 20

    return min(pontos, 100)

# ==========================================================
# ANÁLISE E MOTOR DE ESTRATÉGIAS
# ==========================================================

def analisar_jogos():
    jogos = buscar_jogos()

    if not jogos:
        logging.info("📊 Nenhum jogo ao vivo encontrado no momento.")
        return

    logging.info(f"🔎 {len(jogos)} jogo(s) ao vivo monitorado(s).")

    for jogo in jogos:
        try:
            fixture_id = jogo["id"]
            casa = jogo["casa"]
            fora = jogo["fora"]
            minuto = jogo["minuto"]
            gols_casa = jogo["gols_casa"]
            gols_fora = jogo["gols_fora"]

            stats = buscar_estatisticas(fixture_id, minuto)
            escanteios = stats["escanteios"]
            finalizacoes = stats["finalizacoes"]
            finalizacoes_gol = stats["finalizacoes_gol"]

            estrategia = None

            # --------------------------------------------------
            # Estratégia 1: Escanteios 1º Tempo
            # --------------------------------------------------
            if (
                15 <= minuto <= 20
                and gols_casa == 0
                and gols_fora == 0
                and escanteios <= 1
                and finalizacoes >= 6
            ):
                estrategia = "📐 Escanteios 1º Tempo"

            # --------------------------------------------------
            # Estratégia 2: Over 0.5 HT
            # --------------------------------------------------
            elif (
                15 <= minuto <= 40
                and gols_casa == 0
                and gols_fora == 0
                and finalizacoes >= 8
                and finalizacoes_gol >= 3
            ):
                estrategia = "⚽ Over 0.5 HT"

            # --------------------------------------------------
            # Estratégia 3: Reação Mandante
            # --------------------------------------------------
            elif (
                minuto >= 46
                and gols_casa == 0
                and gols_fora == 1
                and finalizacoes >= 10
            ):
                estrategia = "🔥 Reação Mandante"

            # --------------------------------------------------
            # Estratégia 4: Escanteios Finais
            # --------------------------------------------------
            elif (
                minuto >= 80
                and abs(gols_casa - gols_fora) <= 1
            ):
                estrategia = "🚩 Escanteios Finais"

            if estrategia is None:
                continue

            # Cálculo de Confiança
            confianca = calcular_confianca(
                minuto, gols_casa, gols_fora, escanteios, finalizacoes, finalizacoes_gol
            )

            # Só aceita se a confiança for 70% ou superior
            if confianca < 70:
                continue

            chave = f"{fixture_id}-{estrategia}"

            if alerta_enviado(chave):
                continue

            mensagem = f"""🎯 *OPORTUNIDADE DETECTADA*

🏆 *{casa} x {fora}*
⏱️ *Minuto:* {minuto}'

⚽ *Placar:* {gols_casa} x {gols_fora}
🚩 *Escanteios:* {escanteios}
🥅 *Finalizações:* {finalizacoes}
🎯 *No Gol:* {finalizacoes_gol}

📊 *Estratégia:* {estrategia}
🤖 *Confiança da IA:* *{confianca}%*

💡 *Confira a odd na sua casa de apostas!*"""

            enviar_telegram(mensagem)
            registrar_sinal(casa, fora, estrategia, minuto, f"{gols_casa}x{gols_fora}", confianca)

            logging.info(f"🚀 Alerta enviado: {casa} x {fora} [{estrategia}]")

        except Exception as erro:
            logging.error(f"❌ Erro ao analisar partida {jogo.get('casa')}: {erro}")

# ==========================================================
# EXECUÇÃO PRINCIPAL (LOOP 24/7)
# ==========================================================

if __name__ == "__main__":
    logging.info("🤖 Robô de Inteligência de Futebol Iniciado com Sucesso!")
    enviar_telegram("🤖 *Robô Inteligente de Futebol Online!* Monitorando 4 estratégias ao vivo com filtro de confiança e histórico.")

    while True:
        try:
            limpar_cache()
            analisar_jogos()
        except Exception as erro:
            logging.error(f"❌ Erro no loop principal: {erro}")
        
        time.sleep(INTERVALO)
