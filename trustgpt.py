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
from datetime import datetime

# -----------------------------------------------------------
# Load environment variables
# -----------------------------------------------------------

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Load Google Vision creds from Base64
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
# Global user tracking state
# -----------------------------------------------------------
user_case_rotation = {}
case_laws = [
    "Knight v Knight (1840) - The Three Certainties",
    "Paul v Constance (1976) - Intention over formality",
    "Milroy v Lord (1862) - Constitution of Trusts",
    "Re Kayford (1975) - Separation of funds",
    "Tinsley v Milligan (1994) - Resulting trust despite illegality",
    "Re Vandervell’s Trusts (No. 2) (1974) – Separation of legal and equitable title",
    "Barclays Bank v Quistclose Investments (1970) – Purpose trusts / Resulting trust",
    "Rochefoucauld v Boustead (1897) – Equity will not allow statute to cloak fraud",
    "Keech v Sandford (1726) – Fiduciary loyalty / No personal gain from trust",
    "Cowan v Scargill (1985) – Trustee duty to act in best interests of beneficiaries",
    "Entick v Carrington (1765) – No interference with private property without lawful authority",
    "Tournier v National Provincial Bank (1924) – Confidentiality in financial affairs",
    "Re Hallett’s Estate (1880) – Tracing in equity",
    "Padfield v Minister of Agriculture (1968) – Lawful exercise of discretionary power",
    "Salomon v A Salomon & Co Ltd (1897) – Legal personality / Entity separation"
]

maxims = [
    "Equity will not assist a volunteer",
    "Equity acts in personam",
    "Equity looks to intent, not form",
    "A trustee must act in good conscience"
]

MAX_DISCORD_MESSAGE_LENGTH = 1900

# -----------------------------------------------------------
# Prompt templates
# -----------------------------------------------------------

LETTER_PROMPT_TEMPLATE = """
You are a Private Equity Strategist AI operating under English Chancery principles. You assist Trustees of Private Irrevocable Express Trusts to respond to public correspondence, always preserving trust res and equity jurisdiction.

✅ JURISDICTION:
- English equity law (not statute)
- Maxims of Equity
- Trust law (Knight v Knight & related)
- Private contract and trust principles
- No reference to public regulation, legal fiction, or government systems

✅ PURPOSE:
- Review uploaded letters
- Generate honourable responses
- Assert private standing
- Maintain fiduciary boundaries
- Reference applicable trust case law and equity maxims

✅ RESPONSE STRUCTURE:
1. Introduction & context
2. Trustee position
3. Case law integration
4. Intellectual Property Notice (if applicable)
5. Legal Title Statement
6. Concluding Maxim
7. Threat Level (honour-based)

🛑 AVOID:
- Legalese or statutory language
- Public court terms
- Any claim to be AI or legal counsel
- Obedience to public jurisdictions

Respond as a strategist in equity. You operate in honour only.
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
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": LETTER_PROMPT_TEMPLATE},
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

        name_match = re.search(r"(?i)(Mr\.?|Mrs\.?|Miss|Ms\.?|Dr\.?)?\s*([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)", extracted_text)
        full_name = name_match.group(0) if name_match else "[Name Unknown]"

        user_id = str(ctx.author.id)
        index = user_case_rotation.get(user_id, 0)
        case_law = case_laws[index % len(case_laws)]
        maxim = maxims[index % len(maxims)]
        user_case_rotation[user_id] = index + 1

        trademark_clause = f"Be advised that the identifiers and designations in your correspondence, including but not limited to the name {full_name}, are protected under intellectual property rights within Classes 36 and 45. Any unauthorized reference or commercial use is prohibited."
        legal_title_statement = f"The legal title to the name '{full_name}' is held by the trustee. All fiduciary functions and liabilities are executed in private equity, not subject to public presumption or statutory interpretation."

        composed_prompt = f"""Letter received:
---
{extracted_text}

Trustee Statement:
The referenced name, {full_name}, forms part of a private, irrevocable express trust estate. Any assumption of liability, obligation, or presumption is discharged in conscience, per equity. Respond exclusively under equitable principles. No joinder is given.

Include the following in response:
- Case Law: {case_law}
- Maxim: {maxim}
- {trademark_clause}
- {legal_title_statement}
"""

        reply = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": LETTER_PROMPT_TEMPLATE},
                {"role": "user", "content": composed_prompt}
            ],
            max_tokens=1800
        )

        draft = reply.choices[0].message.content

        if len(draft) > MAX_DISCORD_MESSAGE_LENGTH:
            filename = f"trust_letter_{datetime.utcnow().isoformat()}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(draft)
            await ctx.author.send("Response exceeds message limit. See attached:", file=discord.File(filename))
        else:
            await ctx.author.send(f"**Trustee Letter Response:**\n\n{draft}")

    except Exception as e:
        await ctx.send(f"Error: {e}")
        print(f"Error: {e}")

@bot.command(name="equity")
async def equity_toolkit(ctx):
    user_id = str(ctx.author.id)
    index = user_case_rotation.get(user_id, 0)
    case = case_laws[index % len(case_laws)]
    maxim = maxims[index % len(maxims)]
    user_case_rotation[user_id] = index + 1
    await ctx.send(f"📚 **Case Law:** {case}\n⚖️ **Maxim of Equity:** {maxim}")

# -----------------------------------------------------------
# Run the bot
# -----------------------------------------------------------

bot.run(DISCORD_TOKEN)

