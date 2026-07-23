import os
import time
import requests

# Credenciais do Telegram e Football API
TOKEN_TELEGRAM = os.getenv("TELEGRAM_TOKEN") or os.getenv("TOKEN_TELEGRAM")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")

# Guarda alertas já enviados para não repeti-los (evita spam)
alertas_enviados = set()

def enviar_telegram(mensagem):
    if not TOKEN_TELEGRAM or not CHAT_ID:
        print("⚠️ Credenciais do Telegram não configuradas nas Variables.")
        return
    url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print("✅ Alerta enviado para o Telegram!")
    except Exception as e:
        print(f"❌ Erro ao enviar para o Telegram: {e}")

def buscar_jogos_ao_vivo():
    url = "https://api.football-data.org/v4/matches?status=LIVE"
    headers = {}
    if FOOTBALL_API_KEY:
        headers["X-Auth-Token"] = FOOTBALL_API_KEY
        
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            dados = response.json()
            return dados.get("matches", [])
        else:
            print(f"⚠️ Erro na API de Futebol: Status {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Erro de conexão com a API de futebol: {e}")
        return []

def monitorar():
    print("🔄 Varrendo partidas ao vivo...")
    partidas = buscar_jogos_ao_vivo()
    print(f"📊 Partidas ao vivo encontradas: {len(partidas)}")
    
    for jogo in partidas:
        try:
            jogo_id = jogo.get("id")
            status_jogo = jogo.get("status", "")
            
            if status_jogo != "LIVE":
                continue
                
            casa = jogo["homeTeam"]["name"]
            fora = jogo["awayTeam"]["name"]
            
            # Placar atual
            score = jogo.get("score", {}).get("fullTime", {})
            gols_casa = score.get("home") if score.get("home") is not None else 0
            gols_fora = score.get("away") if score.get("away") is not None else 0
            gols_total = gols_casa + gols_fora
            
            competicao = jogo.get("competition", {}).get("name", "Desconhecida")
            
            # Minuto do jogo (se a API não fornecer o minuto exato, pula a verificação de minuto)
            minuto = jogo.get("minute")
            if minuto is None:
                continue

            # 1. Alerta de Escanteios no 1º Tempo (13' a 18')
            chave_escanteios = f"{jogo_id}_escanteios_1ht"
            if 13 <= minuto <= 18 and chave_escanteios not in alertas_enviados:
                alerta = (
                    f"🚨 *OPORTUNIDADE - ESCANTEIOS 1HT* 🚨\n\n"
                    f"🏆 Competição: {competicao}\n"
                    f"⚽ {casa} {gols_casa} x {gols_fora} {fora}\n"
                    f"⏱️ Minuto: {minuto}' (1º Tempo)\n"
                    f"🎯 Alvo: Mais de 3.5 Cantos (1HT)\n"
                    f"📊 Odds Estimadas: 1.50 - 2.00"
                )
                enviar_telegram(alerta)
                alertas_enviados.add(chave_escanteios)

            # 2. Alerta de Gols no 1º Tempo (25' a 40' sem gols)
            chave_gols = f"{jogo_id}_gols_1ht"
            if 25 <= minuto <= 40 and gols_total == 0 and chave_gols not in alertas_enviados:
                alerta = (
                    f"⚡ *OPORTUNIDADE DE GOL (1º TEMPO)* ⚡\n\n"
                    f"🏆 Competição: {competicao}\n"
                    f"⚽ {casa} {gols_casa} x {gols_fora} {fora}\n"
                    f"⏱️ Minuto: {minuto}'\n"
                    f"🎯 Alvo: Mais de 0.5 Gols (1HT)\n"
                    f"📊 Odds Estimadas: 1.50 - 2.00"
                )
                enviar_telegram(alerta)
                alertas_enviados.add(chave_gols)
            
            time.sleep(1)
            
        except Exception as e:
            print(f"⚠️ Erro ao processar o jogo {jogo.get('id')}: {e}")

if __name__ == "__main__":
    print("🤖 Robô de Futebol Iniciado com Sucesso!")
    enviar_telegram("🤖 *Robô de Futebol Online!* Monitorando partidas ao vivo 24/7.")
    while True:
        monitorar()
        time.sleep(120)  # Varredura a cada 2 minutos
