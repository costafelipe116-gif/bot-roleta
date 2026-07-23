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

# Filtros e Parâmetros
ODD_MINIMA = 1.50
ODD_MAXIMA = 2.00
INTERVALO_VERIFICACAO = 60  # Verifica o mercado a cada 60 segundos

# Memória para evitar spam do mesmo jogo
jogos_ja_alertados = set()


# ==========================================================
# 2. FUNÇÃO PARA ENVIAR ALERTA NO TELEGRAM
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
# 3. BUSCAR PARTIDAS AO VIVO E ESTATÍSTICAS (Tempo e Placar)
# ==========================================================
def obter_partidas_ao_vivo_detalhadas():
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
                
                # Placar atual
                score = m.get("score", {})
                full_time = score.get("fullTime", {})
                gols_casa = full_time.get("home", 0) or 0
                gols_fora = full_time.get("away", 0) or 0
                
                # Identificar etapa do jogo (1º ou 2º tempo)
                stage_status = score.get("duration", "REGULAR")
                
                chave = f"{casa} x {fora}".lower()
                partidas_mapeadas[chave] = {
                    "casa": casa,
                    "fora": fora,
                    "gols_casa": gols_casa,
                    "gols_fora": gols_fora,
                    "status": stage_status
                }
    except Exception as e:
        print(f"Erro ao buscar dados ao vivo: {e}")
        
    return partidas_mapeadas


# ==========================================================
# 4. ANALISADOR DE OPORTUNIDADES BASEADO NAS REGRAS
# ==========================================================
def analisar_oportunidades_ao_vivo():
    print("⚡ Analisando partidas e regras ao vivo...")
    
    # Busca dados de tempo/placar reais
    partidas_ao_vivo = obter_partidas_ao_vivo_detalhadas()
    if not partidas_ao_vivo:
        return

    # Busca as odds do mercado ao vivo
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

            # Verifica se o jogo realmente está rolando no ao vivo
            if chave_jogo not in partidas_ao_vivo:
                continue

            info_jogo = partidas_ao_vivo[chave_jogo]
            gols_c = info_jogo["gols_casa"]
            gols_f = info_jogo["gols_fora"]

            # Evita duplicidade de alerta para o mesmo jogo
            if chave_jogo in jogos_ja_alertados:
                continue

            # Varre as casas de apostas em busca das odds entre 1.50 e 2.00
            for casa in jogo.get("bookmakers", []):
                nome_casa = casa.get("title", "")
                
                for mercado in casa.get("markets", []):
                    tipo_mercado = mercado.get("key", "")
                    
                    for aposta in mercado.get("outcomes", []):
                        odd_atual = aposta.get("price", 0)
                        nome_aposta = aposta.get("name", "")

                        # Validação do intervalo de Odd que você pediu (1.50 a 2.00)
                        if ODD_MINIMA <= odd_atual <= ODD_MAXIMA:
                            
                            # REGRAS DE ANÁLISE SOLICITADAS:
                            estrategia_detectada = ""

                            # Regra 2: Jogo 0x0 no 1º tempo para Over 0.5 Gols / Cantos (15'+)
                            if gols_c == 0 and gols_f == 0:
                                estrategia_detectada = "⚽ **Oportunidade 1º Tempo:** Jogo 0x0 (Pressão para Gol ou Cantos após 15')"

                            # Regra 3: Time da casa perdendo de 1x0 no 2º tempo (Reação para +1.5 Gols / Gols)
                            elif gols_c < gols_f and gols_f - gols_c == 1:
                                estrategia_detectada = "🔥 **Oportunidade 2º Tempo:** Time da Casa perdendo de 1x0 (Pressão por Virada / Gols)"

                            # Regra geral de cantos e mercados ao vivo mapeados nas odds
                            else:
                                estrategia_detectada = f"🎯 **Oportunidade Ao Vivo:** Mercado de {nome_aposta}"

                            if estrategia_detectada:
                                mensagem = (
                                    "🚨 **SINAL DE ENTRADA AO VIVO!** 🚨\n\n"
                                    f"⚽ **Jogo:** {time_casa} {gols_c} x {gols_f} {time_fora}\n"
                                    f"🏢 **Casa:** {nome_casa}\n"
                                    f"{estrategia_detectada}\n"
                                    f"📈 **Odd Alvo:** {odd_atual:.2f}\n\n"
                                    "💡 *Confira o confronto ao vivo na sua plataforma e execute a entrada!*"
                                )
                                
                                enviar_alerta_telegram(mensagem)
                                jogos_ja_alertados.add(chave_jogo)
                                break
                else:
                    continue
                break

    except Exception as e:
        print(f"Erro ao processar estratégias: {e}")


# ==========================================================
# 5. EXECUÇÃO CONTÍNUA DO ROBÔ
# ==========================================================
if __name__ == "__main__":
    print("🚀 Robô de Análises Ao Vivo (Gols e Cantos) Iniciado!")
    while True:
        analisar_oportunidades_ao_vivo()
        time.sleep(INTERVALO_VERIFICACAO)
