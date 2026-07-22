import os
from playwright.sync_api import sync_playwright
import telebot

# Pega o token do bot direto das variáveis de ambiente do Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

def rodar_automacao():
    with sync_playwright() as p:
        # headless=True é obrigatório no Railway pois o servidor não tem tela
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        url_roleta = "https://skylinewgrows.evo-games.com/frontend/evo/r2/#category=all_games&game=roulette&table_id=7x0b1tgh7agmf6hv&lobby_launch_id=2471e41bc5c049ba9c6b4344776e7e98"
        
        print(f"Acessando a roleta: {url_roleta}")
        page.goto(url_roleta)
        
        # Aguarda alguns segundos para garantir que a página carregou
        page.wait_for_timeout(10000)
        
        print("Página da roleta aberta com sucesso na nuvem!")
        browser.close()

@bot.message_handler(commands=['start', 'help'])
def enviar_boas_vindas(message):
    bot.reply_to(message, "Opa! Bot rodando perfeitamente e conectado ao Railway.")

@bot.message_handler(commands=['rodar'])
def trigger_bot(message):
    bot.reply_to(message, "Iniciando a automação e abrindo a roleta...")
    try:
        rodar_automacao()
        bot.reply_to(message, "Automação finalizada com sucesso! Roleta acessada.")
    except Exception as e:
        bot.reply_to(message, f"Erro ao executar: {e}")

if __name__ == "__main__":
    print("Bot iniciado...")
    bot.infinity_polling()
