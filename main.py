import os
import telebot
from playwright.sync_api import sync_playwright

# Pega o token do bot direto das variáveis de ambiente do Railway
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

def rodar_automacao():
    with sync_playwright() as p:
        # O argumento headless=True é obrigatório para rodar em servidores em nuvem sem interface gráfica
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Coloque aqui o link ou a lógica da sua automação com o Playwright
        # Exemplo: page.goto("https://seu-site-de-roleta.com")
        
        print("Automação rodando com sucesso!")
        browser.close()

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Opa! Bot rodando perfeitamente no Railway 🚀")

@bot.message_handler(commands=['rodar'])
def trigger_bot(message):
    bot.reply_to(message, "Iniciando a automação...")
    try:
        rodar_automacao()
        bot.reply_to(message, "Automação finalizada com sucesso!")
    except Exception as e:
        bot.reply_to(message, f"Erro ao executar: {e}")

if __name__ == "__main__":
    print("Bot iniciado...")
    bot.infinity_polling()
