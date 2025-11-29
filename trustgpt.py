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
import re

# -----------------------------------------------------------
# Load environment variables
# -----------------------------------------------------------

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
creds_b64 = os.getenv("GCRED")
if not creds_b64:
    raise Exception("GOOGLE_CREDS_B64 environment variable is missing!")

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

TRUST_PROMPT = """
You are a Private Trustee Strategist AI acting under English Equity and Conscience...
"""

LETTER_PROMPT = """
You are a Private Trustee Strategist AI operating solely under English equity and conscience...
"""

# -----------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------

def extract_name(text):
    match = re.search(r"Mrs?\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+", text)
    return match.group(0) if match else None

def determine_threat_level(text):
    if any(word in text.lower() for word in ["court", "legal", "summons", "deadline", "proceedings"]):
        return "HIGH"
    elif any(word in text.lower() for word in ["payment", "reminder", "notice"]):
        return "MEDIUM"
    return "LOW"

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
                {"role": "system", "content": TRUST_PROMPT},
                {"role": "user", "content": question}
            ],
            max_tokens=700,
            temperature=0.7
        )
        await ctx.author.send(response.choices[0].message.content)
    except Exception as e:
        await ctx.send(f"Error: {e}")
        print(f"Error: {e}")

@bot.command(name="letter")
async def process_letter(ctx):
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

        name = extract_name(extracted_text) or "the name in question"
        threat_level = determine_threat_level(extracted_text)

        prompt = f"""
The following letter was uploaded by a trustee:

{extracted_text}

Generate a formal trustee response including:
- Recognition that the name {name} is held in a Private Irrevocable Express Trust
- Confirmation the Trustee holds legal title and trademark Classes 36 and 45
- Reference to relevant equity case law
- Application of one appropriate maxim of equity
- A brief assessment of threat level: {threat_level}
- Strategic tone avoiding legal jurisdiction while honouring fiduciary duty
"""

        reply = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": LETTER_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=900
        )

        draft = reply.choices[0].message.content
        await ctx.author.send(f"**Trustee Letter Response:**\n\n{draft}")
        await ctx.send("Response sent via private message.")

    except Exception as e:
        await ctx.send(f"Error: {e}")
        print(f"Error: {e}")

# -----------------------------------------------------------
# Run the bot
# -----------------------------------------------------------

bot.run(DISCORD_TOKEN)

