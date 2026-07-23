import os
import time
import requests

# ==========================================================
# 1. SUAS CONFIGURAÇÕES E CHAVES OFICIAIS
# ==========================================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8675857127:AAFvZAqEJhu5UJPY6v8t7Y3GTQJTxgI788g")
CHAT_ID = os.getenv("CHAT_ID", "5912926190")
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "d27dcfd9551863e11be6453b75d9b6f1")
FOOTBALL_DATA_KEY = os.getenv("FOOTBALL_DATA_KEY", "db1b4be93bda49ab9f05fa9e20b994c1")

# Filtros do Bot
ODD_MINIMA = 1.50
ODD_MAXIMA = 2.00
INTERVALO_VERIFICACAO = 40  # Checa a cada 40 segundos

# Guardar alertas enviados para evitar spam de mensagens repetidas
jogos_alertados = set()


# ==========================================================
# 2. ENVIAR ALERTA NO TELEGRAM
# ==========================================================
def enviar_alerta_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": mensagem,
        "parse_mode": "Markdown"
    }
    try:
        resposta = requests.post(url, json=payload)
        if resposta.status_code == 200:
            print("✅ Alerta ao vivo enviado com sucesso no Telegram!")
        else:
            print(f"❌ Erro no Telegram ({resposta.status_code}): {resposta.text}")
    except Exception as e:
        print(f"❌ Erro ao enviar no Telegram: {e}")


# ==========================================================
# 3. BUSCAR PLACARES E JOGOS AO VIVO (Football-Data.org)
# ==========================================================
def obter_jogos_ao_vivo_stats():
    url = "https://api.football-data.org/v4/matches"
    headers = {"X-Auth-Token": FOOTBALL_DATA_KEY}
    params = {"status": "IN_PLAY"}
    
    try:
        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200:
            return res.json().get("matches", [])
    except Exception as e:
        print(f"⚠️ Erro ao consultar Football-Data: {e}")
    return []


# ==========================================================
# 4. ANALISAR OPORTUNIDADES AO VIVO + ODDS
# ==========================================================
def analisar_oportunidades():
    print("⚡ Analisando jogos AO VIVO e buscando oportunidades...")
    
    # 1. Busca odds ao vivo
    url_odds = "https://api.the-odds-api.com/v4/sports/upcoming/odds/"
    params_odds = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu,us",
        "markets": "h2h,totals",
        "oddsFormat": "decimal"
    }

    try:
        resposta_odds = requests.get(url_odds, params=params_odds)
        if resposta_odds.status_code != 200:
            print(f"⚠️ Erro na Odds API ({resposta_odds.status_code}): {resposta_odds.text}")
            return

        jogos_odds = resposta_odds.json()
        jogos_stats = obter_jogos_ao_vivo_stats()

        for jogo in jogos_odds:
            sport_key = jogo.get("sport_key", "")
            if "soccer" not in sport_key:
                continue

            id_jogo = jogo.get("id")
            time_casa = jogo.get("home_team", "Time Casa")
            time_fora = jogo.get("away_team", "Time Fora")

            # Varre as odds das casas de apostas
            for casa in jogo.get("bookmakers", []):
                nome_casa = casa.get("title", "Casa de Apostas")
                
                for mercado in casa.get("markets", []):
                    tipo_mercado = mercado.get("key", "")
                    
                    for aposta in mercado.get("outcomes", []):
                        nome_opcao = aposta.get("name")
                        odd_atual = aposta.get("price", 0)

                        # FILTRO DE ODD ENTRE 1.50 E 2.00
                        if ODD_MINIMA <= odd_atual <= ODD_MAXIMA:
                            id_alerta = f"{id_jogo}_{tipo_mercado}_{nome_opcao}_{odd_atual}"

                            if id_alerta not in jogos_alertados:
                                mensagem = (
                                    "🚨 **OPORTUNIDADE AO VIVO DETECTADA!** 🚨\n\n"
                                    f"⚽ **Jogo:** {time_casa} x {time_fora}\n"
                                    f"🏢 **Casa:** {nome_casa}\n"
                                    f"🎯 **Entrada/Mercado:** {nome_opcao}\n"
                                    f"📈 **Odd Atual:** {odd_atual:.2f}\n\n"
                                    "💡 *Verifique o momento do jogo na sua casa de apostas e faça sua entrada!*"
                                )
                                
                                enviar_alerta_telegram(mensagem)
                                jogos_alertados.add(id_alerta)

    except Exception as e:
        print(f"❌ Erro no processamento: {e}")


# ==========================================================
# 5. EXECUÇÃO CONTINUA DO BOT
# ==========================================================
if __name__ == "__main__":
    print("🚀 Bot de Sinais AO VIVO com 2 APIs Iniciado!")
    
    while True:
        analisar_oportunidades()
        time.sleep(INTERVALO_VERIFICACAO)
