import io
import logging
import os
import re

from PIL import Image
from google import genai
from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

NUCLEO_14 = [31,9,22,18,29,14,20,1,33,16,24]
NUCLEO_25 = [17,34,25,2,21]
NUCLEO_11 = [23,30,11,36,13]

def obter_gemini_client():
    key = os.getenv("GEMINI_API_KEY","").strip()
    if not key:
        return None
    return genai.Client(api_key=key)

def analisar_matematica_roleta(numeros):
    if not numeros:
        return "Nenhum número encontrado."
    return f"Foram encontrados {len(numeros)} números:\n{numeros}"

async def processar_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Foto recebida")

    status = await update.message.reply_text("🔍 Lendo histórico...")

    try:
        client = obter_gemini_client()
        if client is None:
            await status.edit_text("❌ GEMINI_API_KEY não configurada.")
            return

        photo = await update.message.photo[-1].get_file()
        data = await photo.download_as_bytearray()
        image = Image.open(io.BytesIO(data))

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                image,
                "Liste apenas os números da roleta na ordem em que aparecem."
            ]
        )

        text = getattr(response, "text", "") or ""
        nums = [int(x) for x in re.findall(r"\b([0-9]|[12][0-9]|3[0-6])\b", text)]

        await status.delete()
        await update.message.reply_text(
            analisar_matematica_roleta(nums),
            parse_mode="Markdown"
        )

    except Exception:
        logging.exception("Erro ao processar imagem")
        try:
            await status.delete()
        except Exception:
            pass
        await update.message.reply_text("⚠️ Ocorreu um erro ao processar a imagem.")

def main():
    token = os.getenv("TELEGRAM_TOKEN","").strip()

    if not token:
        raise RuntimeError("TELEGRAM_TOKEN não configurado.")

    app = Application.builder().token(token).build()

    app.add_handler(
        MessageHandler(filters.PHOTO, processar_foto)
    )

    logging.info("Bot iniciado.")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()
