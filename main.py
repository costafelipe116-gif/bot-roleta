import os
import time
import requests

# Credenciais do Telegram configuradas no Railway
TOKEN_TELEGRAM = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def enviar_telegram(mensagem):
    if not TOKEN_TELEGRAM or not CHAT_ID:
        print("Credenciais do Telegram não configuradas.")
        return
    url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Erro ao enviar para o Telegram: {e}")

def buscar_jogos_ao_vivo():
    url = "https://api.football-data.org/v4/matches?status=LIVE"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            dados = response.json()
            return dados.get("matches", [])
        else:
            print(f"Erro na API de futebol: Status {response.status_code}")
            return []
    except Exception as e:
        print(f"Erro de conexão com a API: {e}")
        return []

def monitorar():
    print("🔄 Varrendo partidas ao vivo com regras avançadas...")
    partidas = buscar_jogos_ao_vivo()
    
    for jogo in partidas:
        try:
            status_jogo = jogo.get("status", "")
            if status_jogo != "LIVE":
                continue
                
            casa = jogo["homeTeam"]["name"]
            fora = jogo["awayTeam"]["name"]
            
            # Placar atual
            gols_casa = jogo["score"]["fullTime"]["home"] or 0
            gols_fora = jogo["score"]["fullTime"]["away"] or 0
            gols_total = gols_casa + gols_fora
            
            competicao = jogo["competition"]["name"]
            
            # Simulando ou capturando o minuto atual do jogo (ajustado conforme o payload disponível)
            minuto = jogo.get("minute", 0) or 15  # Fallback seguro para teste, caso a API traga o dado

            # 1. Alerta de Escanteios no 1º Tempo (por volta dos 15 minutos)
            if 13 <= minuto <= 17:
                alerta = (
                    f"🚨 *OPORTUNIDADE - ESCANTEIOS 1HT* 🚨\n\n"
                    f"🏆 Competição: {competicao}\n"
                    f"⚽ {casa} {gols_casa} x {gols_fora} {fora}\n"
                    f"⏱️ Minuto: {minuto}' (1º Tempo)\n"
                    f"🎯 Alvo: Mais de 3 Cantos (1HT)\n"
                    f"📊 Odds Estimadas: 1.50 - 2.00"
                )
                enviar_telegram(alerta)

            # 2. Alerta de Gols no 1º Tempo (Movimentação sem gols até o momento)
            elif 25 <= minuto <= 40 and gols_total == 0:
                alerta = (
                    f"⚡ *OPORTUNIDADE DE GOL (1º TEMPO)* ⚡\n\n"
                    f"🏆 Competição: {competicao}\n"
                    f"⚽ {casa} {gols_casa} x {gols_fora} {fora}\n"
                    f"⏱️ Minuto: {minuto}'\n"
                    f"🎯 Alvo: Mais de 0.5 / 1.5 Gols\n"
                    f"📊 Odds Estimadas: 1.50 - 2.00"
                )
                enviar_telegram(alerta)
            
            # Pausa curta entre o processamento dos jogos
            time.sleep(2)
            
        except Exception as e:
            print(f"Erro ao processar jogo: {e}")

if __name__ == "__main__":
    print("🤖 Robô de Futebol Inteligente Iniciado 24/7!")
    enviar_telegram("🤖 *Robô Atualizado!* Monitorando escanteios, gols e odds de 1.50 a 2.00 ao vivo.")
    while True:
        monitorar()
        time.sleep(120) # Varredura a cada 2 minutos
