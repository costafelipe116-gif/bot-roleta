import os
import logging
import asyncio
import re
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from google import genai
from PIL import Image
import io

# Configuração de Logs
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

def obter_gemini_client():
    raw_key = os.getenv("GEMINI_API_KEY", "")
    if not raw_key:
        return None
    # Remove automaticamente qualquer caractere invisível/Unicode copiado pelo celular (no início/fim)
    clean_key = re.sub(r'[^\x00-\x7F]+', '', raw_key).strip()
    try:
        return genai.Client(api_key=clean_key)
    except Exception as e:
        logging.error(f"Erro ao inicializar Gemini Client: {e}")
        return None

# Mapeamento de Núcleos KP
NUCLEO_14 = [31, 9, 22, 18, 29, 14, 20, 1, 33, 16, 24]
NUCLEO_25 = [17, 34, 25, 2, 21]
NUCLEO_11 = [23, 30, 11, 36, 13]

# Mapeamento do Racetrack (Lado Direito vs. Lado Esquerdo)
LADO_DIREITO = [23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35]
LADO_ESQUERDO = [8, 30, 11, 36, 13, 27, 6, 34, 17, 25, 2, 21, 4, 19, 15, 32]

def analisar_matematica_roleta(numeros):
    total = len(numeros)
    if total == 0:
        return "⚠️ Nenhum número válido foi encontrado na imagem. Tente enviar um print mais aproximado do histórico da mesa."

    # 1. Mapeamento Racetrack
    qtd_direito = sum(1 for n in numeros if n in LADO_DIREITO)
    qtd_esquerdo = sum(1 for n in numeros if n in LADO_ESQUERDO)
    pct_direito = round((qtd_direito / total) * 100) if total else 0
    pct_esquerdo = round((qtd_esquerdo / total) * 100) if total else 0

    # 2. Raio-X KP
    qtd_kp14 = sum(1 for n in numeros if n in NUCLEO_14)
    qtd_kp25 = sum(1 for n in numeros if n in NUCLEO_25)
    qtd_kp11 = sum(1 for n in numeros if n in NUCLEO_11)

    pct_kp14 = round((qtd_kp14 / total) * 100) if total else 0
    pct_kp25 = round((qtd_kp25 / total) * 100) if total else 0
    pct_kp11 = round((qtd_kp11 / total) * 100) if total else 0

    kp_dict = {"Núcleo 14 (+5 vizinhos)": pct_kp14, "Núcleo 25 (+2 vizinhos)": pct_kp25, "Núcleo 11 (+2 vizinhos)": pct_kp11}
    nucleo_dominante = max(kp_dict, key=kp_dict.get)

    # 3. Famílias de Cavalos (Terminais)
    cav_258 = sum(1 for n in numeros if str(n)[-1] in ['2', '5', '8'])
    cav_147 = sum(1 for n in numeros if str(n)[-1] in ['1', '4', '7'])
    cav_0369 = sum(1 for n in numeros if str(n)[-1] in ['0', '3', '6', '9'])

    pct_258 = round((cav_258 / total) * 100) if total else 0
    pct_147 = round((cav_147 / total) * 100) if total else 0
    pct_0369 = round((cav_0369 / total) * 100) if total else 0

    fam_dict = {"Cavalo 0/3/6/9": pct_0369, "Cavalo 2/5/8": pct_258, "Cavalo 1/4/7": pct_147}
    fam_quente = max(fam_dict, key=fam_dict.get)

    # Montagem do Relatório
    relatorio = f"""📊 *ANÁLISE DE MESA — ROLETA IMERSIVA*
⏱ _Amostra processada: {total} giros_

---

### 1. Mapeamento Geral do Racetrack
* **Lado Direito:** **{pct_direito}%** ({qtd_direito}x)
* **Lado Esquerdo:** **{pct_esquerdo}%** ({qtd_esquerdo}x)

### 2. Raio-X da Jogada KP
* **Núcleo 14 (+5 vizinhos):** {qtd_kp14} saídas (**{pct_kp14}%**)
* **Núcleo 25 (+2 vizinhos):** {qtd_kp25} saídas (**{pct_kp25}%**)
* **Núcleo 11 (+2 vizinhos):** {qtd_kp11} saídas (**{pct_kp11}%**)
> 🔥 **Dominância:** {nucleo_dominante} em destaque.

### 3. Famílias de Cavalos (Terminais)
* **Cavalo 0/3/6/9:** **{pct_0369}%**
* **Cavalo 2/5/8:** **{pct_258}%**
* **Cavalo 1/4/7:** **{pct_147}%**
> 🧬 **Família Quente:** {fam_quente}

### 4. Direcionamento e Jogada Sugerida
🎯 **ENTRADA RECOMENDADA:**
* **Aposta Base:** **{nucleo_dominante}** no Racetrack
* **Terminais em Foco:** Cruzar com as saídas da família **{fam_quente}**

---
⚡ _Aguardando a próxima foto da mesa..._"""

    return relatorio

async def processar_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gemini_client = obter_gemini_client()
    if not gemini_client:
        await update.message.reply_text("❌ Erro: A variável `GEMINI_API_KEY` não está configurada corretamente no Railway.")
        return

    msg_status = await update.message.reply_text("🔍 *Lendo histórico da imagem...*", parse_mode="Markdown")

    try:
        foto = await update.message.photo[-1].get_file()
        foto_bytes = await foto.download_as_bytearray()
        imagem_pil = Image.open(io.BytesIO(foto_bytes))

        prompt = "Liste todos os números do histórico de roleta visíveis nesta imagem na sequência exata."
        
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[imagem_pil, prompt]
        )

        texto_resposta = response.text if response and response.text else ""
        texto_limpo = re.sub(r'[^\x00-\x7F]+', ' ', texto_resposta)
        
        encontrados = re.findall(r'\b\d+\b', texto_limpo)
        numeros = [int(n) for n in encontrados if 0 <= int(n) <= 36]

        relatorio_final = analisar_matematica_roleta(numeros)

        await msg_status.delete()
        await update.message.reply_text(relatorio_final, parse_mode="Markdown")

    except Exception as e:
        await msg_status.delete()
        erro_bruto = str(e)
        erro_limpo = re.sub(r'[^\x00-\x7F]+', '', erro_bruto)
        await update.message.reply_text(f"⚠️ Erro ao processar a imagem. Certifique-se de que o print está bem nítido.\n\nDetalhes: {erro_limpo}")

def main():
    token = os.getenv("TELEGRAM_TOKEN", "")
    clean_token = re.sub(r'[^\x00-\x7F]+', '', token).strip()
    
    if not clean_token:
        print("Erro: TELEGRAM_TOKEN não encontrado!")
        return

    app = Application.builder().token(clean_token).build()
    app.add_handler(MessageHandler(filters.PHOTO, processar_foto))

    print("⚡ Robô da Roleta rodando com sucesso!")
    app.run_polling()

if __name__ == "__main__":
    main()
