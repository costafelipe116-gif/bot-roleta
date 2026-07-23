import os
import time
import requests

# Variáveis de ambiente configuradas no Railway
TOKEN_TELEGRAM = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")

def enviar_telegram(mensagem):
    if not TOKEN_TELEGRAM or not CHAT_ID:
        print("Credenciais do Telegram não configuradas.")
        return
    url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Erro ao enviar para o Telegram: {e}")

def buscar_jogos_ao_vivo():
    url = "https://v3.football.api-sports.io/fixtures"
    querystring = {"live": "all"}
    headers = {
        "x-rapidapi-key": API_FOOTBALL_KEY,
        "x-rapidapi-host": "v3.football.api-sports.io"
    }
    try:
        response = requests.get(url, headers=headers, params=querystring)
        dados = response.json()
        return dados.get("response", [])
    except Exception as e:
        print(f"Erro na API de futebol: {e}")
        return []

def monitorar():
    print("🔄 Varrendo partidas ao vivo...")
    partidas = buscar_jogos_ao_vivo()
    
    for jogo in partidas:
        minuto = jogo["fixture"]["status"]["elapsed"]
        casa = jogo["teams"]["home"]["name"]
        fora = jogo["teams"]["away"]["name"]
        gols = (jogo["goals"]["home"] or 0) + (jogo["goals"]["away"] or 0)
        
        # Puxando estatísticas dinâmicas da partida ao vivo
        cantos = 0
        pressao = 0
        for stat in jogo.get("statistics", []):
            for s in stat.get("statistics", []):
                if s["type"] == "Corner Kicks":
                    cantos += int(s["value"] or 0)
                elif s["type"] in ["Dangerous Attacks", "Total Shots"]:
                    pressao += int(s["value"] or 0)

        # Gatilho 1: 1º Tempo (Até 15') - Foco em Gols/Cantos (Odd 1.50 - 1.70)
        if minuto <= 15 and gols == 0:
            if pressao >= 6 and cantos >= 2:
                alerta = (
                    f"🚨 *OPORTUNIDADE HT (1º TEMPO)* 🚨\n\n"
                    f"⚽ {casa} vs {fora}\n"
                    f"⏱️ Minuto: {minuto}'\n"
                    f"🚩 Cantos: {cantos} | Pressão: Forte\n"
                    f"🎯 Alvo: Over 0.5 HT / Cantos (Odd 1.50 - 1.70)"
                )
                enviar_telegram(alerta)

        # Gatilho 2: 2º Tempo (Até 60') - Foco em Gols/Cantos (Odd 1.50 - 1.70)
        elif 45 <= minuto <= 60:
            if pressao >= 10:
                alerta = (
                    f"🚨 *OPORTUNIDADE 2º TEMPO (Até 60')* 🚨\n\n"
                    f"⚽ {casa} vs {fora}\n"
                    f"⏱️ Minuto: {minuto}'\n"
                    f"📊 Ritmo intenso no pós-intervalo\n"
                    f"🎯 Alvo: Over 0.5 / 1.5 Gols ou Cantos (Odd 1.50 - 1.70)"
                )
                enviar_telegram(alerta)

if __name__ == "__main__":
    print("🤖 Robô de Análise Ao Vivo Iniciado 24/7!")
    while True:
        monitorar()
        time.sleep(60) # Pausa de 60 segundos entre cada varredura
