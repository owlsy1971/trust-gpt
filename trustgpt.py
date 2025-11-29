# Upgraded Discord bot with trustee logic, equity-based responses, threat detection, and full legal strategy formatting

import discord
import os
from discord.ext import commands
from openai import OpenAI
import aiohttp
from google.cloud import vision
from google.oauth2 import service_account
import json
import base64
import re
from datetime import datetime

# Load environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Load and decode Google Cloud credentials from base64
creds_b64 = os.getenv("GCRED")
if not creds_b64:
    raise Exception("GOOGLE_CREDS_B64 environment variable is missing!")
creds_json = base64.b64decode(creds_b64).decode("utf-8")
GCREDS = json.loads(creds_json)

# Initialize OpenAI and Google Vision clients
client = OpenAI(api_key=OPENAI_API_KEY)
vision_creds = service_account.Credentials.from_service_account_info(GCREDS)
vision_client = vision.ImageAnnotatorClient(credentials=vision_creds)

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Tracking state per user
user_case_rotation = {}
case_laws = [
    "Knight v Knight (1840) - The Three Certainties",
    "Paul v Constance (1976) - Intention over formality",
    "Milroy v Lord (1862) - Constitution of Trusts",
    "Re Kayford (1975) - Separation of funds",
    "Tinsley v Milligan (1994) - Resulting trust despite illegality"
]
maxims = [
    "Equity will not assist a volunteer",
    "Equity acts in personam",
    "Equity looks to intent, not form",
    "A trustee must act in good conscience"
]

# System prompt for OpenAI
LETTER_PROMPT_TEMPLATE = """
You are a Private Trustee Strategist AI operating solely under English equity and conscience. You serve trustees of private irrevocable express trusts. Your responses are honourable, strategic, and strictly non-statutory.

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

REPLY FORMAT:
1. Introduction
2. Trustee Position
3. Case Law
4. Trademarks (if applicable)
5. Right of Access (if applicable)
6. Maxim
7. Threat Level

COMMUNICATION:
- Never mention legal terms or court systems
- Never say "I am an AI"
- Respond as a strategist in private equity
"""

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user.name}")

@bot.command(name="ask")
async def ask_trust(ctx, *, question):
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": LETTER_PROMPT_TEMPLATE},
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

        name_match = re.search(r"(?i)(Mr\.?|Mrs\.?|Ms\.?|Miss|Dr\.?)\s+([A-Z][a-z]+\s[A-Z][a-z]+)", extracted_text)
        full_name = name_match.group(0) if name_match else "[Name Unknown]"

        user_id = str(ctx.author.id)
        index = user_case_rotation.get(user_id, 0)
        case_law = case_laws[index % len(case_laws)]
        maxim = maxims[index % len(maxims)]
        user_case_rotation[user_id] = index + 1

        trademark_clause = f"The name {full_name} is protected by Trademarks Classes 36 and 45. Any unauthorized use is denied."
        access_clause = "The implied right of access is revoked. Your presence or communication is not consented to by the Trust."

        composed_prompt = f"""Letter received:\n---\n{extracted_text}\n\nTrustee Statement:\nThe name {full_name} is held in a Private Irrevocable Express Trust. All liabilities and claims are rebutted in equity.\n\nInstructions:\n- Case Law: {case_law}\n- Maxim: {maxim}\n- {trademark_clause}\n- {access_clause}"""

        reply = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": LETTER_PROMPT_TEMPLATE},
                {"role": "user", "content": composed_prompt}
            ],
            max_tokens=1800
        )

        draft = reply.choices[0].message.content
        if len(draft) > 1900:
            filename = f"trust_letter_{datetime.utcnow().isoformat()}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(draft)
            await ctx.author.send("Response exceeds message limit. See attached:", file=discord.File(filename))
        else:
            await ctx.author.send(f"**Trustee Letter Response:**\n\n{draft}")

    except Exception as e:
        await ctx.send(f"Error: {e}")
        print(f"Error: {e}")

bot.run(DISCORD_TOKEN)

