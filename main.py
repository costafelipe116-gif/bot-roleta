import os
import time
import requests

# Token do Telegram configurado no Railway
TOKEN_TELEGRAM = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

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
    # Usando uma API pública de futebol gratuita (Football-Data) sem necessidade de chave secreta
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
    print("🔄 Varrendo partidas ao vivo (Modo Gratuito)...")
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
            
            # Identificando a competição
            competicao = jogo["competition"]["name"]

            # Disparando alerta genérico de jogo ao vivo encontrado no radar
            alerta = (
                f"🚨 *OPORTUNIDADE AO VIVO* 🚨\n\n"
                f"🏆 Competição: {competicao}\n"
                f"⚽ {casa} {gols_casa} x {gols_fora} {fora}\n"
                f"📊 Partida em andamento sob monitoramento\n"
                f"🎯 Alvo: Ficar atento para entrada (Odd 1.50 - 1.70)"
            )
            enviar_telegram(alerta)
            
            # Pausa curta para não estourar o limite de requisições gratuitas
            time.sleep(2)
            
        except Exception as e:
            print(f"Erro ao processar jogo: {e}")

if __name__ == "__main__":
    print("🤖 Robô de Futebol Gratuito Iniciado 24/7!")
    while True:
        monitorar()
        time.sleep(120) # Varredura a cada 2 minutos
