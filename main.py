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
INTERVALO_VERIFICACAO = 60  # Checa a cada 60 segundos

# Memória para evitar mandar o mesmo jogo repetido
jogos_ja_alertados = set()


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
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Erro ao enviar no Telegram: {e}")


# ==========================================================
# 3. BUSCAR JOGOS AO VIVO (Football-Data.org)
# ==========================================================
def obter_times_ao_vivo():
    url = "https://api.football-data.org/v4/matches"
    headers = {"X-Auth-Token": FOOTBALL_DATA_KEY}
    params = {"status": "IN_PLAY"}
    
    times_ao_vivo = set()
    try:
        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200:
            partidas = res.json().get("matches", [])
            for p in partidas:
                casa = p.get("homeTeam", {}).get("name", "").lower()
                fora = p.get("awayTeam", {}).get("name", "").lower()
                if casa: times_ao_vivo.add(casa)
                if fora: times_ao_vivo.add(fora)
    except Exception as e:
        print(f"Erro ao consultar Football-Data: {e}")
    
    return times_ao_vivo


# ==========================================================
# 4. ANALISAR OPORTUNIDADES SEM SPAM
# ==========================================================
def analisar_oportunidades():
    print("⚡ Varrendo mercado em busca de oportunidades ao vivo...")
    
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
            return

        jogos_odds = resposta_odds.json()
        times_ao_vivo = obter_times_ao_vivo()

        for jogo in jogos_odds:
            if "soccer" not in jogo.get("sport_key", ""):
                continue

            time_casa = jogo.get("home_team", "")
            time_fora = jogo.get("away_team", "")
            
            # Valrida se o jogo está rolando de fato (opcional, caso queira filtrar estrito)
            # Se quiser garantir que só pega jogo ao vivo da lista, descomente a linha abaixo:
            # if times_ao_vivo and not (time_casa.lower() in times_ao_vivo or time_fora.lower() in times_ao_vivo): continue

            id_jogo = jogo.get("id")

            # Se esse jogo já mandou sinal nesta execução, pula para o próximo para não lotar de spam
            if id_jogo in jogos_ja_alertados:
                continue

            # Varre as casas procurando a primeira odd válida no intervalo de 1.50 a 2.00
            encontrou_oportunidade = False
            mercado_encontrado = ""
            odd_encontrada = 0.0
            casa_nome = ""

            for casa in jogo.get("bookmakers", []):
                if encontrou_oportunidade: 
                    break
                casa_nome = casa.get("title", "")
                
                for mercado in casa.get("markets", []):
                    if encontrou_oportunidade: 
                        break
                    tipo_mercado = mercado.get("key", "")
                    
                    for aposta in mercado.get("outcomes", []):
                        odd_atual = aposta.get("price", 0)

                        if ODD_MINIMA <= odd_atual <= ODD_MAXIMA:
                            mercado_encontrado = aposta.get("name")
                            odd_encontrada = odd_atual
                            encontrou_oportunidade = True
                            break

            # Se achou uma boa oportunidade, dispara apenas UM alerta por jogo
            if encontrou_oportunidade:
                mensagem = (
                    "🚨 **OPORTUNIDADE AO VIVO DETECTADA!** 🚨\n\n"
                    f"⚽ **Jogo:** {time_casa} x {time_fora}\n"
                    f"🏢 **Casa:** {casa_nome}\n"
                    f"🎯 **Entrada:** {mercado_encontrado}\n"
                    f"📈 **Odd:** {odd_encontrada:.2f}\n\n"
                    "💡 *Abra sua casa de apostas e verifique o momento da partida!*"
                )
                enviar_alerta_telegram(mensagem)
                jogos_ja_alertados.add(id_jogo)  # Bloqueia esse jogo para não repetir

    except Exception as e:
        print(f"Erro na análise: {e}")


# ==========================================================
# 5. EXECUÇÃO CONTINUA
# ==========================================================
if __name__ == "__main__":
    print("🚀 Bot Otimizado Iniciado!")
    while True:
        analisar_oportunidades()
        time.sleep(INTERVALO_VERIFICACAO)
