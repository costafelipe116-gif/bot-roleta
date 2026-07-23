import os
import time
import requests

# ==========================================================
# 1. SUAS CONFIGURAÇÕES E CHAVES OFICIAIS (PREENCHIDAS)
# ==========================================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8675857127:AAFvZAqEJhu5UJPY6v8t7Y3GTQJTxgI788g")
CHAT_ID = os.getenv("CHAT_ID", "5912926190")
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "d27dcfd9551863e11be6453b75d9b6f1")

# Filtros do Bot
ODD_MINIMA = 1.50
ODD_MAXIMA = 2.00
INTERVALO_VERIFICACAO = 40  # Verifica novos jogos a cada 40 segundos

# Guardar alertas enviados para evitar spam de mensagens repetidas
jogos_alertados = set()


# ==========================================================
# 2. FUNÇÃO PARA DISPARAR ALERTA NO TELEGRAM
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
        print(f"❌ Erro de conexão ao enviar no Telegram: {e}")


# ==========================================================
# 3. ANALISADOR DE OPORTUNIDADES AO VIVO
# ==========================================================
def analisar_jogos_ao_vivo():
    print("⚡ Buscando oportunidades AO VIVO no mercado de futebol...")
    
    url = "https://api.the-odds-api.com/v4/sports/upcoming/odds/"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu,us",
        "markets": "h2h,totals",
        "oddsFormat": "decimal"
    }

    try:
        resposta = requests.get(url, params=params)
        
        if resposta.status_code != 200:
            print(f"⚠️ Erro na API de Odds ({resposta.status_code}): {resposta.text}")
            return

        jogos = resposta.json()

        for jogo in jogos:
            sport_key = jogo.get("sport_key", "")
            if "soccer" not in sport_key:
                continue

            id_jogo = jogo.get("id")
            time_casa = jogo.get("home_team", "Time Casa")
            time_fora = jogo.get("away_team", "Time Fora")
            bookmakers = jogo.get("bookmakers", [])

            for casa in bookmakers:
                nome_casa = casa.get("title", "Casa de Apostas")
                
                for mercado in casa.get("markets", []):
                    tipo_mercado = mercado.get("key", "")
                    
                    for aposta in mercado.get("outcomes", []):
                        nome_opcao = aposta.get("name")
                        odd_atual = aposta.get("price", 0)

                        # FILTRO DE ODD AO VIVO (Entre 1.50 e 2.00)
                        if ODD_MINIMA <= odd_atual <= ODD_MAXIMA:
                            id_alerta = f"{id_jogo}_{tipo_mercado}_{nome_opcao}_{odd_atual}"

                            if id_alerta not in jogos_alertados:
                                mensagem = (
                                    "🚨 **OPORTUNIDADE AO VIVO DETECTADA!** 🚨\n\n"
                                    f"⚽ **Jogo:** {time_casa} x {time_fora}\n"
                                    f"🏢 **Casa:** {nome_casa}\n"
                                    f"🎯 **Mercado/Entrada:** {nome_opcao}\n"
                                    f"📈 **Odd Atual:** {odd_atual:.2f}\n\n"
                                    "💡 *Confira o momento do jogo na sua casa de apostas e realize a entrada!*"
                                )
                                
                                enviar_alerta_telegram(mensagem)
                                jogos_alertados.add(id_alerta)

    except Exception as e:
        print(f"❌ Erro ao analisar jogos ao vivo: {e}")


# ==========================================================
# 4. EXECUÇÃO CONTINUA
# ==========================================================
if __name__ == "__main__":
    print("🚀 Bot de Sinais AO VIVO Iniciado!")
    
    while True:
        analisar_jogos_ao_vivo()
        time.sleep(INTERVALO_VERIFICACAO)
