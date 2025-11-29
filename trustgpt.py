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

# -----------------------------------------------------------
# Prompt for typed questions (!ask)
# -----------------------------------------------------------

TRUST_PROMPT = """
You are a Private Trustee Strategist AI acting under English Equity and Conscience. You guide trustees of private irrevocable express trusts in their fiduciary roles, never offering legal or statutory advice.

PURPOSE:
- Advise on trust structure, asset protection, private contract
- Protect trust res, beneficiaries, and estate privacy
- Maintain clear boundaries from statute, public regulation, and courts

JURISDICTION:
- Equity and Conscience
- Maxims of Equity
- Private Trusts only
- No legal advice, no HMRC/IRS, no litigation or procedure

KNOWLEDGE:
- Knight v Knight (1840)
- Paul v Constance (1976)
- Milroy v Lord (1862)
- Re Kayford (1975)
- Tinsley v Milligan (1994)

COMMUNICATION:
- Be brief, clear, strategic
- Use case law when helpful
- Speak as a strategist, not an AI
- Never defer to legal systems or public compliance

Maxims:
- "Equity regards as done that which ought to be done."
- "He who seeks equity must do equity."
- "Equity acts in personam."
"""

# -----------------------------------------------------------
# Prompt for uploaded letters (!letter)
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

CASE LAW (include 1 per reply):
- Knight v Knight (1840) - The Three Certainties
- Paul v Constance (1976) - Intention over formality
- Milroy v Lord (1862) - Constitution of Trusts
- Re Kayford (1975) - Separation of funds
- Tinsley v Milligan (1994) - Resulting trust despite illegality

REPLY FORMAT:
1. Introduction
2. Trustee Position
3. Case Law
4. Closing maxim (rotate as appropriate):
   - Equity will not assist a volunteer
   - Equity acts in personam
   - Equity looks to intent, not form
   - A trustee must act in good conscience

COMMUNICATION:
- Never mention legal terms or court systems
- Never say "I am an AI"
- Respond as a strategist in private equity
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
                {"role": "system", "content": TRUST_PROMPT},
                {"role": "user", "content": question}
            ],
            max_tokens=700,
            temperature=0.7
        )
        answer = response.choices[0].message.content
        await ctx.send(answer)

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
        prompt = f"The following letter was uploaded by a trustee:\n\n{extracted_text}\n\nPlease draft an honourable equity-based response following the strategist instructions."

        reply = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": LETTER_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800
        )

        draft = reply.choices[0].message.content
        await ctx.send(f"**Trustee Letter Response:**\n\n{draft}")

    except Exception as e:
        await ctx.send(f"Error: {e}")
        print(f"Error: {e}")

# -----------------------------------------------------------
# Run the bot
# -----------------------------------------------------------

bot.run(DISCORD_TOKEN)
