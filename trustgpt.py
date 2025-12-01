# Full Discord bot script with Intelligent Equity Engine
# Updated for FIRST‑PERSON trustee voice, strict Chancery language,
# full equitable separation of persons, and correct fiduciary positioning.

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

# -----------------------------------------------------------
# Environment
# -----------------------------------------------------------

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
creds_b64 = os.getenv("GCRED")
if not creds_b64:
    raise Exception("GCRED environment variable is missing!")
creds_json = base64.b64decode(creds_b64).decode("utf-8")
GCREDS = json.loads(creds_json)

client = OpenAI(api_key=OPENAI_API_KEY)
vision_creds = service_account.Credentials.from_service_account_info(GCREDS)
vision_client = vision.ImageAnnotatorClient(credentials=vision_creds)

# -----------------------------------------------------------
# Discord
# -----------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# -----------------------------------------------------------
# Intelligence Tables
# -----------------------------------------------------------

user_case_rotation = {}

case_laws_by_type = {
    "council": [
        "Padfield v Minister of Agriculture (1968) – Proper exercise of discretionary power",
        "Entick v Carrington (1765) – No interference with private property without lawful warrant",
    ],
    "trust": [
        "Knight v Knight (1840) – The Three Certainties",
        "Paul v Constance (1976) – Intention may perfect a trust",
        "Milroy v Lord (1862) – A trust must be properly constituted",
        "Re Kayford (1975) – Separation of trust property",
        "Re Vandervell’s Trusts (No. 2) (1974) – Separation of legal and equitable title",
        "Rochefoucauld v Boustead (1897) – Equity prevents fraud despite lack of form",
        "Keech v Sandford (1726) – Fiduciary loyalty is absolute",
    ],
    "commercial": [
        "Tournier v National Provincial Bank (1924) – Duty of confidentiality in financial affairs",
        "Re Hallett’s Estate (1880) – Tracing principles in equity",
        "Salomon v A Salomon & Co Ltd (1897) – Legal personality must be respected",
    ]
}

maxims = [
    "Equity will not assist a volunteer",
    "Equity acts in personam",
    "Equity looks to intent rather than form",
    "A trustee must act in good conscience",
    "Equity regards as done that which ought to be done",
    "He who seeks equity must do equity",
    "He who comes to equity must come with clean hands",
    "Equity follows the law",
    "Delay defeats equity",
    "Where equities are equal, the first in time prevails",
    "Equity is equality",
    "Equity aids the vigilant, not the indolent",
    "Equity will not suffer a wrong without a remedy",
]

# -----------------------------------------------------------
# Chancery‑Correct Prompt Template (First‑Person Trustee Voice)
# -----------------------------------------------------------

LETTER_PROMPT_TEMPLATE = """
You respond STRICTLY in first-person as the acting Trustee of a Private Irrevocable Express Trust.
You write in correct Chancery and equitable language.
You NEVER refer to the trustee as “you” and NEVER speak in third-person.
You speak ONLY as:

    "I, in my capacity as Trustee…"

You maintain absolute separation between:
- The MAN/WOMAN (equitable person)
- The NAME (legal person) held as trust property

You DO NOT acknowledge:
- Public jurisdiction
- Statutory obligations
- Contract by presumption
- Joinder

You DO affirm:
- Fiduciary conscience
- Trust res separation
- Equitable title vs legal title distinctions
- Right of private administration

Your letter MUST follow this 7‑section structure:
1. Introduction (first-person trustee voice)
2. Trustee Position (separation of persons + equitable standing)
3. Case Law (insert dynamically)
4. Trademark Clause (first-person assertion of title)
5. Legal Title Declaration (trustee holds title; no joinder)
6. Closing Maxim (dynamic)
7. Cease & Desist (first-person directive)

Write with honour, clarity, and private authority.
"""

# -----------------------------------------------------------
# Bot Events
# -----------------------------------------------------------

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user.name}")

# -----------------------------------------------------------
# Letter Command
# -----------------------------------------------------------

@bot.command(name="letter")
async def process_letter(ctx):

    if not ctx.message.attachments:
        await ctx.send("Upload a letter with !letter (image only).")
        return

    attachment = ctx.message.attachments[0]
    await ctx.send("Reading your uploaded letter…")

    try:
        # Download
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                if resp.status != 200:
                    await ctx.send("Failed to download file.")
                    return
                data = await resp.read()

        # OCR
        image = vision.Image(content=data)
        result = vision_client.document_text_detection(image=image)
        extracted_text = result.full_text_annotation.text

        # ---------------------------
        # Name Detection (robust)
        # ---------------------------
        try:
            name_match = re.search(r"(?i)(Mr\\.?|Mrs\\.?|Miss|Ms\\.?|Dr\\.?)\\s+[A-Z][a-z]+\\s+[A-Z][a-z]+", extracted_text)
            if name_match:
                full_name = name_match.group(0)
            else:
                fallback_match = re.search(r"\\b([A-Z][a-z]+|[A-Z]+)\\s+([A-Z][a-z]+|[A-Z]+)\\b", extracted_text)
                full_name = fallback_match.group(0) if fallback_match else "[Name Unknown]"
        except Exception:
            full_name = "[Name Unknown]"

        # Date
        date_match = re.search(r"\\b\\d{1,2}/\\d{1,2}/\\d{2,4}\\b", extracted_text)
        letter_date = date_match.group(0) if date_match else "[Undated]"

        # Type detection
        low = extracted_text.lower()
        if "council tax" in low or "liability order" in low:
            letter_type = "council"
        elif "mortimer clarke" in low or "cabot" in low or "debt" in low:
            letter_type = "commercial"
        else:
            letter_type = "trust"

        # Rotation logic
        user_id = str(ctx.author.id)
        idx = user_case_rotation.get(user_id, 0)
        user_case_rotation[user_id] = idx + 1

        case_law_list = case_laws_by_type.get(letter_type, case_laws_by_type["trust"])
        case_law = case_law_list[idx % len(case_law_list)]
        maxim = maxims[idx % len(maxims)]

        # Clauses
        trademark_clause = (
            f"I assert that the identifiers utilised in your correspondence, including the designation '{full_name}', "
            f"constitute property of this Private Trust and are protected under intellectual property classes 36 and 45. "
            f"No party may employ or presume upon these identifiers without my express fiduciary consent."
        )

        legal_title_statement = (
            f"I hold the legal title to the designation '{full_name}' strictly in my capacity as Trustee. "
            f"Such title is administered solely in equity, entirely separate from any public, statutory or presumed liability." 
        )

        # Prompt to GPT
        composed_prompt = f"""
Letter Date: {letter_date}
Designated Name: {full_name}

OCR Extract:
---
{extracted_text}
---

Compose the full 7‑section trustee response using:
Case Law: {case_law}
Maxim: {maxim}
Trademark Clause: {trademark_clause}
Legal Title Declaration: {legal_title_statement}
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
        print(e)

# -----------------------------------------------------------
# Run Bot
# -----------------------------------------------------------

bot.run(DISCORD_TOKEN)


