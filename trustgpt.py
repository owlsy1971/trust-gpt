# Full Discord bot script with GPT-4, Google Vision OCR, and equity-based trust prompts

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
from datetime import datetime

# -----------------------------------------------------------
# Load environment variables
# -----------------------------------------------------------

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Load Google Vision creds from Base64 (Railway-safe)
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

# Letter tracking per user
user_letter_counts = {}

# -----------------------------------------------------------
# Prompts
# -----------------------------------------------------------

LETTER_PROMPT = """
You are a Private Trustee Strategist AI operating solely under English equity and conscience. You serve trustees of private irrevocable express trusts. Your responses are honourable, strategic, and strictly non-statutory. You do not acknowledge legal or public jurisdiction. You operate in equity alone.

PURPOSE:
- Read uploaded correspondence
- Protect trust res and estate privacy
- Respond in honour with case law support
- Maintain fiduciary boundaries

JURISDICTION:
- English Equity and Chancery tradition
- Maxims of Equity
- Private contractual law
- No public regulation, compliance or litigation

ADDITIONAL:
- Automatically detect and include:
  - Implied Right of Access rebuttals (e.g. council tax, bailiff)
  - Settlor/Trustee role clarification if a name is detected
  - Reference Trademark Classes 36 & 45 if applicable
  - Case law (auto) and Equity Maxim (rotate)
  - Threat level (LOW, MODERATE, HIGH)
  - Unique organic response (no templates)

REPLY FORMAT:
1. Introduction
2. Trustee Position
3. Case Law
4. Equity Maxim
5. Threat Level
6. Closing in honour

COMMUNICATION:
- Never mention legal terms or court systems
- Never say "I am an AI"
- Speak as a strategist in private equity
"""

# -----------------------------------------------------------
# Bot Events & Commands
# -----------------------------------------------------------

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user.name}")

@bot.command(name="letter")
async def process_letter(ctx):
    if not ctx.message.attachments:
        await ctx.send("Please upload a letter (PDF or image) with your message.")
        return

    user_id = ctx.author.id
    user_letter_counts[user_id] = user_letter_counts.get(user_id, 0) + 1
    letter_number = user_letter_counts[user_id]

    attachment = ctx.message.attachments[0]
    await ctx.send("📄 Reading and processing your uploaded letter...")

    try:
        # Download file
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                if resp.status != 200:
                    await ctx.send("Failed to download the file.")
                    return
                data = await resp.read()

        # OCR
        image = vision.Image(content=data)
        result = vision_client.document_text_detection(image=image)
        extracted_text = result.full_text_annotation.text

        # Draft response
        prompt = f"Letter #{letter_number} uploaded by a trustee:\n\n{extracted_text}\n\nDraft an equity-based response per strategist instructions."

        reply = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": LETTER_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000
        )

        draft = reply.choices[0].message.content

        # Send via DM as file if too long
        if len(draft) > 2000:
            with open("trustee_reply.txt", "w", encoding="utf-8") as f:
                f.write(draft)
            with open("trustee_reply.txt", "rb") as file:
                await ctx.author.send("📎 Response exceeds message limit. See attached file.", file=discord.File(file, filename="trustee_reply.txt"))
        else:
            await ctx.author.send(f"**Trustee Letter Response – Letter #{letter_number}:**\n\n{draft}")

        await ctx.send("✅ Trustee response sent to your direct messages.")

    except Exception as e:
        await ctx.send(f"Error: {e}")
        print(f"Error: {e}")

# -----------------------------------------------------------
# Run the bot
# -----------------------------------------------------------

bot.run(DISCORD_TOKEN)


