import os
import time
import requests

# ==========================================================
# 1. CONFIGURAÇÕES E CHAVES
# ==========================================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8675857127:AAFvZAqEJhu5UJPY6v8t7Y3GTQJTxgI788g")
CHAT_ID = os.getenv("CHAT_ID", "5912926190")
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "d27dcfd9551863e11be6453b75d9b6f1")
FOOTBALL_DATA_KEY = os.getenv("FOOTBALL_DATA_KEY", "db1b4be93bda49ab9f05fa9e20b994c1")

# Parâmetros de Filtro
ODD_MINIMA = 1.50
ODD_MAXIMA = 2.00
INTERVALO_VERIFICACAO = 60  # Roda a verificação a cada 60 segundos

# Memória anti-spam (evita repetir alertas do mesmo jogo)
jogos_ja_alertados = set()


# ==========================================================
# 2. FUNÇÃO DE ENVIO PARA O TELEGRAM
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
# 3. BUSCAR PARTIDAS AO VIVO (COM MINUTO E PLACAR)
# ==========================================================
def obter_partidas_ao_vivo():
    url = "https://api.football-data.org/v4/matches"
    headers = {"X-Auth-Token": FOOTBALL_DATA_KEY}
    params = {"status": "IN_PLAY"}
    
    partidas_mapeadas = {}
    try:
        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200:
            matches = res.json().get("matches", [])
            for m in matches:
                casa = m.get("homeTeam", {}).get("name", "")
                fora = m.get("awayTeam", {}).get("name", "")
                
                score = m.get("score", {})
                full_time = score.get("fullTime", {})
                gols_casa = full_time.get("home", 0) or 0
                gols_fora = full_time.get("away", 0) or 0
                
                # Captura o minuto atual do jogo fornecido pela API
                minuto_atual = m.get("minute", 0) or 0
                
                chave = f"{casa} x {fora}".lower()
                partidas_mapeadas[chave] = {
                    "casa": casa,
                    "fora": fora,
                    "gols_casa": gols_casa,
                    "gols_fora": gols_fora,
                    "minuto": minuto_atual
                }
    except Exception as e:
        print(f"Erro ao buscar partidas ao vivo: {e}")
        
    return partidas_mapeadas


# ==========================================================
# 4. MOTOR DE ANÁLISE DAS 4 ESTRATÉGIAS AO VIVO
# ==========================================================
def analisar_estrategias_ao vivo():
    print("⚡ Varrendo mercado e partidas ao vivo...")
    
    partidas_ao_vivo = obter_partidas_ao_vivo()
    if not partidas_ao_vivo:
        return

    url_odds = "https://api.the-odds-api.com/v4/sports/upcoming/odds/"
    params_odds = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu,us",
        "markets": "h2h,totals",
        "oddsFormat": "decimal"
    }

    try:
        resposta = requests.get(url_odds, params=params_odds)
        if resposta.status_code != 200:
            return

        jogos = resposta.json()

        for jogo in jogos:
            if "soccer" not in jogo.get("sport_key", ""):
                continue

            time_casa = jogo.get("home_team", "")
            time_fora = jogo.get("away_team", "")
            chave_jogo = f"{time_casa} x {time_fora}".lower()

            # Garante estritamente que o jogo está rolando no ao vivo
            if chave_jogo not in partidas_ao_vivo:
                continue

            info = partidas_ao_vivo[chave_jogo]
            gols_c = info["gols_casa"]
            gols_f = info["gols_fora"]
            minuto = info["minuto"]

            # Evita duplicidade de alerta para a mesma partida
            if chave_jogo in jogos_ja_alertados:
                continue

            # Varre as odds das casas de apostas
            for casa in jogo.get("bookmakers", []):
                nome_casa = casa.get("title", "")
                
                for mercado in casa.get("markets", []):
                    for aposta in mercado.get("outcomes", []):
                        odd_atual = aposta.get("price", 0)
                        nome_aposta = aposta.get("name", "")

                        # Valida o filtro de Odds (1.50 a 2.00)
                        if ODD_MINIMA <= odd_atual <= ODD_MAXIMA:
                            
                            estrategia_detectada = ""

                            # --- ESTRATÉGIA 1: Cantos no 1º Tempo (A partir dos 15 minutos) ---
                            if 15 <= minuto <= 22 and gols_c == 0 and gols_f == 0:
                                estrategia_detectada = f"📐 **Estratégia Cantos 1º Tempo:** Jogo com {minuto}' e 0x0 (Pressão por Escanteios)"

                            # --- ESTRATÉGIA 2: Gol no 1º Tempo / Over 0.5 HT (A partir dos 15 minutos, 0x0) ---
                            elif minuto >= 15 and gols_c == 0 and gols_f == 0 and ("over" in nome_aposta.lower() or "0.5" in nome_aposta):
                                estrategia_detectada = f"⚽ **Estratégia Over 0.5 HT:** Jogo 0x0 aos {minuto}' (Pressão para Gol no 1º Tempo)"

                            # --- ESTRATÉGIA 3: Time da Casa Perdendo de 1x0 no 2º Tempo (Reação / Mais de 1.5 Gols) ---
                            elif minuto >= 46 and gols_c == 0 and gols_f == 1:
                                estrategia_detectada = f"🔥 **Estratégia Reação 2º Tempo:** Time da Casa perdendo de 1x0 aos {minuto}' (Pressão por Empate/Virada)"

                            # --- ESTRATÉGIA 4: Cantos Limite / Final de Jogo (A partir dos 80 minutos) ---
                            elif minuto >= 80:
                                estrategia_detectada = f"🚨 **Estratégia Cantos Limite:** Reta final de jogo aos {minuto}' (Pressão Total p/ Escanteios)"

                            # Se alguma das regras foi acionada, dispara o alerta
                            if estrategia_detectada:
                                mensagem = (
                                    "🎯 **OPORTUNIDADE AO VIVO DETECTADA!** 🎯\n\n"
                                    f"⚽ **Confronto:** {time_casa} **{gols_c} x {gols_f}** {time_fora}\n"
                                    f"⏱️ **Minuto:** {minuto}'\n"
                                    f"🏢 **Casa:** {nome_casa}\n"
                                    f"{estrategia_detectada}\n"
                                    f"📈 **Odd Alvo:** {odd_atual:.2f} ({nome_aposta})\n\n"
                                    "💡 *Abra sua plataforma e analise a entrada em tempo real!*"
                                )
                                
                                enviar_alerta_telegram(mensagem)
                                jogos_ja_alertados.add(chave_jogo)
                                break
                else:
                    continue
                break

    except Exception as e:
        print(f"Erro ao processar o motor de estratégias: {e}")


# ==========================================================
# 5. LOOP DE EXECUÇÃO CONTÍNUA
# ==========================================================
if __name__ == "__main__":
    print("🚀 Robô de Análises Ao Vivo com Regras Específicas Iniciado!")
    while True:
        analisar_estrategias_ao vivo()
        time.sleep(INTERVALO_VERIFICACAO)
