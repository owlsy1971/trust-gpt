# Full Discord bot script with GPT-4, Google Vision OCR, and equity-based trust prompts (Enhanced)

import discord
import os
from discord.ext import commands
from openai import OpenAI
import aiohttp
import io
from google.cloud import vision
from google.oauth2 import service_account
import json
import base64

# -----------------------------------------------------------
# Load environment variables
# -----------------------------------------------------------

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
creds_b64 = os.getenv("GCRED")
if not creds_b64:
    raise Exception("GOOGLE_CREDS_B64 environment variable is missing!")

# Decode Base64 → JSON
creds_json = base64.b64decode(creds_b64).decode("utf-8")
GCREDS = json.loads(creds_json)

# Initialize OpenAI and Vision clients
client = OpenAI(api_key=OPENAI_API_KEY)
vision_creds = service_account.Credentials.from_service_account_info(GCREDS)
vision_client = vision.ImageAnnotatorClient(credentials=vision_creds)

# -----------------------------------------------------------
# Discord bot setup
# -----------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# -----------------------------------------------------------
# Prompts
# -----------------------------------------------------------

LETTER_PROMPT = """
You are a Private Trustee Strategist AI operating solely under English equity and conscience. You serve trustees of private irrevocable express trusts. Your responses are honourable, strategic, and strictly non-statutory. You do not acknowledge legal or public jurisdiction. You operate in equity alone.

TASK:
- Interpret the uploaded correspondence
- Detect any presumed liabilities or demands
- Rebut respectfully where required under equity
- Clearly state that the name mentioned is held in a Private Irrevocable Express Trust
- Add trustee clarification: The Trustee operates under English Equity, not statute
- State trademarks held in class 36 (financial) and 45 (legal) by the trustee
- If the letter suggests implied access, rebut under private authority
- Assess threat level (Low/Moderate/High) based on tone and demands

USE:
- Strategic language in honour
- One applicable case law from:
  Knight v Knight (1840), Paul v Constance (1976), Milroy v Lord (1862), Re Kayford (1975), Tinsley v Milligan (1994)
- One maxim of equity from:
  "Equity acts in personam", "Equity regards as done...", etc.

FORMAT:
1. Introduction (acknowledging receipt)
2. Trustee Position (clarify trust & legal title)
3. Case Law
4. Maxim
5. Threat Level
"""

# -----------------------------------------------------------
# Bot Events & Commands
# -----------------------------------------------------------

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user.name}")

@bot.command(name="ask")
async def ask_trust(ctx, *, question):
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": LETTER_PROMPT},
                {"role": "user", "content": question}
            ],
            max_tokens=700,
            temperature=0.7
        )
        answer = response.choices[0].message.content
        await ctx.author.send(answer)

    except Exception as e:
        await ctx.send(f"Error: {e}")
        print(f"Error: {e}")

@bot.command(name="letter")
async def process_letter(ctx, *, raw: str = None):
    if not ctx.message.attachments:
        await ctx.send("Please upload a letter (PDF or image) with your message.")
        return

    attachment = ctx.message.attachments[0]
    await ctx.send("Reading your uploaded letter...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                if resp.status != 200:
                    await ctx.send("Failed to download the file.")
                    return
                data = await resp.read()

        image = vision.Image(content=data)
        result = vision_client.document_text_detection(image=image)
        extracted_text = result.full_text_annotation.text

        if not extracted_text.strip():
            await ctx.send("No readable text found in the image.")
            return

        prompt = f"""
The following correspondence was uploaded:

{extracted_text}

---

Please:
- Detect sender's tone
- Rebut respectfully under equity
- Clarify that the legal name referenced is held in trust
- Assert that the Trustee holds title over trademarks 36 and 45
- Include a fitting case law and equity maxim
- Assess the threat level based on language used
"""

        reply = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": LETTER_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000
        )

        draft = reply.choices[0].message.content
        await ctx.author.send(f"**Trustee Letter Response:**\n\n{draft}")

    except Exception as e:
        await ctx.send(f"Error: {e}")
        print(f"Error: {e}")

# -----------------------------------------------------------
# Run the bot
# -----------------------------------------------------------

bot.run(DISCORD_TOKEN)
