import os
import telebot

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start', 'help'])
def enviar_boas_vindas(message):
    bot.reply_to(message, "Opa! Robô de análise por print ativado 🚀\n\nMande o print do histórico da roleta para receber a análise.")

# Handler para receber fotos/prints enviados por você
@bot.message_handler(content_types=['photo'])
def analisar_print(message):
    bot.reply_to(message, "Recebi o seu print! Analisando o histórico da mesa...")
    
    try:
        # Aqui entra a lógica da sua estratégia (análise dos números que vierem no print)
        # Exemplo simulado de resposta de sinal:
        # "Análise concluída! Tendência forte para Vermelho / Coluna 2."
        
        resposta_analise = "📊 **Análise Concluída:**\n\n- Padrão identificado nas últimas rodadas.\n- Sugestão: Ficar de olho na entrada de dezenas ou cores conforme o seu método."
        
        bot.reply_to(message, resposta_analise, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"Erro ao processar a imagem: {e}")

if __name__ == "__main__":
    print("Bot de análise iniciado e aguardando prints...")
    bot.infinity_polling()
