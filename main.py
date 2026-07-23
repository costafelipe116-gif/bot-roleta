import time
import requests

# ==========================================================
# 1. SUAS CONFIGURAÇÕES
# ==========================================================
TELEGRAM_TOKEN = "SEU_TELEGRAM_TOKEN_AQUI"
CHAT_ID = "SEU_CHAT_ID_AQUI"
ODDS_API_KEY = "d27dcfd9551863e11be6453b75d9b6f1"

# Filtros do bot
ODD_MINIMA = 1.50
ODD_MAXIMA = 2.00
INTERVALO_VERIFICACAO = 60  # Tempo em segundos entre cada checagem

# Guardar os alertas já enviados para não repeti-los (evita spam)
jogos_alertados = set()


# ==========================================================
# 2. FUNÇÃO QUE ENVIA A MENSAGEM PARA O TELEGRAM
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
            print("✅ Alerta enviado com sucesso no Telegram!")
        else:
            print(f"❌ Erro ao enviar no Telegram: {resposta.text}")
    except Exception as e:
        print(f"❌ Falha de conexão ao enviar mensagem: {e}")


# ==========================================================
# 3. FUNÇÃO QUE BUSCA OS JOGOS E FILTRA AS ODDS
# ==========================================================
def verificar_jogos_e_odds():
    print("🔍 Analisando odds no mercado de futebol...")
    
    url = "https://api.the-odds-api.com/v4/sports/upcoming/odds/"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu,us",         # Regiões das casas de apostas
        "markets": "h2h,totals",    # Mercados: Vencedor e Gols
        "oddsFormat": "decimal"
    }

    try:
        resposta = requests.get(url, params=params)
        
        if resposta.status_code != 200:
            print(f"⚠️ Erro na API de Odds (Código {resposta.status_code}): {resposta.text}")
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
                    for aposta in mercado.get("outcomes", []):
                        nome_opcao = aposta.get("name")
                        odd_atual = aposta.get("price", 0)

                        # FILTRO: Verifica se a Odd está no intervalo (1.50 a 2.00)
                        if ODD_MINIMA <= odd_atual <= ODD_MAXIMA:
                            id_alerta = f"{id_jogo}_{nome_opcao}_{odd_atual}"

                            if id_alerta not in jogos_alertados:
                                mensagem = (
                                    "🚨 **ALERTA DE ENTRADA DETECTADO!** 🚨\n\n"
                                    f"⚽ **Jogo:** {time_casa} x {time_fora}\n"
                                    f"🏢 **Casa:** {nome_casa}\n"
                                    f"🎯 **Mercado/Opção:** {nome_opcao}\n"
                                    f"📈 **Odd Atual:** {odd_atual:.2f}\n\n"
                                    "💡 *Acesse a casa de apostas para realizar sua entrada!*"
                                )
                                
                                enviar_alerta_telegram(mensagem)
                                jogos_alertados.add(id_alerta)

    except Exception as e:
        print(f"❌ Erro no processamento dos dados: {e}")


# ==========================================================
# 4. EXECUÇÃO CONTÍNUA DO BOT
# ==========================================================
if __name__ == "__main__":
    print("🚀 Bot de Sinais iniciado com sucesso!")
    
    while True:
        verificar_jogos_e_odds()
        time.sleep(INTERVALO_VERIFICACAO)
