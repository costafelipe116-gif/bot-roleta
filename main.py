import os
import subprocess
from playwright.sync_api import sync_playwright
import telebot

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

def garantir_navegador():
    # Instala o navegador do Playwright caso ele ainda não exista no ambiente
    print("Verificando/instalando o navegador do Playwright...")
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        print(f"Erro ao instalar navegador: {e}")

def rodar_automacao():
    garantir_navegador()
    
    with sync_playwright() as p:
        # Usa o lançamento padrão do Playwright (ele gerencia o binário baixado sozinho)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        url_roleta = "https://skylinewgrows.evo-games.com/frontend/evo/r2/#category=all_games&game=roulette&table_id=7x0b1tgh7agmf6hv&lobby_launch_id=2471e41bc5c049ba9c6b4344776e7e98"
        
        print(f"Acessando a roleta: {url_roleta}")
        page.goto(url_roleta)
        page.wait_for_timeout(10000)
        
        print("Página da roleta aberta com sucesso!")
        browser.close()

@bot.message_handler(commands=['start', 'help'])
def enviar_boas_vindas(message):
    bot.reply_to(message, "Opa! Bot rodando perfeitamente no Railway 🚀")

@bot.message_handler(commands=['rodar'])
def trigger_bot(message):
    bot.reply_to(message, "Iniciando automação e preparando o navegador...")
    try:
        rodar_automacao()
        bot.reply_to(message, "Automação finalizada com sucesso! Roleta acessada.")
    except Exception as e:
        bot.reply_to(message, f"Erro ao executar: {e}")

if __name__ == "__main__":
    print("Bot iniciado...")
    bot.infinity_polling()
