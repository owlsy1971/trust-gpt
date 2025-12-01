# Full Discord bot script with gpt-4o-mini, Google Vision OCR, and Intelligent Equity Engine

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
creds_b64 = os.getenv("GCRED")
if not creds_b64:
    raise Exception("GCRED environment variable is missing!")
creds_json = base64.b64decode(creds_b64).decode("utf-8")
GCREDS = json.loads(creds_json)

# Initialize OpenAI and Vision clients
client = OpenAI(api_key=OPENAI_API_KEY)
vision_creds = service_account.Credentials.from_service_account_info(GCREDS)
vision_client = vision.ImageAnnotatorClient(credentials=vision_creds)

# Discord setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Case law and maxims logic
user_case_rotation = {}

case_laws_by_type = {
    "council": [
        "Padfield v Minister of Agriculture (1968) – Lawful exercise of discretionary power",
        "Entick v Carrington (1765) – No interference with private property without lawful authority"
    ],
    "trust": [
        "Knight v Knight (1840) - The Three Certainties",
        "Paul v Constance (1976) - Intention over formality",
        "Milroy v Lord (1862) - Constitution of Trusts",
        "Re Kayford (1975) - Separation of funds",
        "Tinsley v Milligan (1994) - Resulting trust despite illegality",
        "Re Vandervell’s Trusts (No. 2) (1974) – Separation of legal and equitable title",
        "Barclays Bank v Quistclose Investments (1970) – Purpose trusts / Resulting trust",
        "Rochefoucauld v Boustead (1897) – Equity will not allow statute to cloak fraud",
        "Keech v Sandford (1726) – Fiduciary loyalty / No personal gain from trust"
    ],
    "commercial": [
        "Tournier v National Provincial Bank (1924) – Confidentiality in financial affairs",
        "Re Hallett’s Estate (1880) – Tracing in equity",
        "Salomon v A Salomon & Co Ltd (1897) – Legal personality / Entity separation"
    ]
}

maxims = [
    "Equity will not assist a volunteer",
    "Equity acts in personam",
    "Equity looks to intent, not form",
    "A trustee must act in good conscience",
    "Equity regards as done that which ought to be done",
    "Equity imputes an intention to fulfil an obligation",
    "He who comes to equity must come with clean hands",
    "Equity follows the law",
    "Delay defeats equity",
    "Where equities are equal, the first in time prevails",
    "Equity is equality",
    "Equity aids the vigilant, not those who sleep on their rights",
    "Equity will not suffer a wrong to be without a remedy"
]

LETTER_PROMPT_TEMPLATE = """
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

REPLY FORMAT:
1. Introduction
2. Trustee Position
3. Case Law
4. Trademark Clause (if applicable)
5. Legal Title Declaration
6. Closing maxim
7. Cease and Desist on trust property

COMMUNICATION:
- Never mention legal terms or court systems
- Never say "I am an AI"
- Respond as a strategist in private equity
"""

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user.name}")

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

        name_match = re.search(r"(?i)(Mr\\.?|Mrs\\.?|Miss|Ms\\.?|Dr\\.?)\\s+([A-Z][a-z]+\\s[A-Z][a-z]+)", extracted_text)
        full_name = name_match.group(0) if name_match else "[Name Unknown]"

        date_match = re.search(r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})", extracted_text)
        found_date = date_match.group(0) if date_match else "[Date Missing]"

        text_lower = extracted_text.lower()
        if any(keyword in text_lower for keyword in ["council tax", "liability order", "magistrates court"]):
            letter_type = "council"
        elif any(keyword in text_lower for keyword in ["trust", "trustee", "beneficiary"]):
            letter_type = "trust"
        else:
            letter_type = "commercial"

        user_id = str(ctx.author.id)
        index = user_case_rotation.get(user_id, 0)
        case_law_list = case_laws_by_type[letter_type]
        case_law = case_law_list[index % len(case_law_list)]
        maxim = maxims[index % len(maxims)]
        user_case_rotation[user_id] = index + 1

        trademark_clause = f"The identifiers in your correspondence, including the name {full_name}, are protected under IP rights (Classes 36 and 45). Unauthorized use is prohibited."
        legal_title_statement = f"Legal title to the name '{full_name}' is held by the trustee. All fiduciary activity operates strictly in equity, beyond public/statutory reach."

        composed_prompt = f"""Letter received (dated {found_date}) referencing name: {full_name}

Trustee Statement:
The name {full_name} is held in a Private Irrevocable Express Trust. All liability is disclaimed under English equity. Respond appropriately.

Include the following in your structured reply:
- Case Law: {case_law}
- Maxim: {maxim}
- {trademark_clause}
- {legal_title_statement}

OCR Extract:
---
{extracted_text}
---
"""

        reply = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": LETTER_PROMPT_TEMPLATE},
                {"role": "user", "content": composed_prompt}
            ],
            max_tokens=1800
        )

        draft = reply.choices[0].message.content
        draft = draft.replace("*", "")

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

