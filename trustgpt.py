# Full Discord bot script with gpt-4o-mini, Google Vision OCR, and equity-based trust prompts

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

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
creds_b64 = os.getenv("GCRED")
if not creds_b64:
    raise Exception("GOOGLE_CREDS_B64 environment variable is missing!")
creds_json = base64.b64decode(creds_b64).decode("utf-8")
GCREDS = json.loads(creds_json)

client = OpenAI(api_key=OPENAI_API_KEY)
vision_creds = service_account.Credentials.from_service_account_info(GCREDS)
vision_client = vision.ImageAnnotatorClient(credentials=vision_creds)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

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

LETTER_PROMPT_TEMPLATE = """
You are a Private Equity Strategist AI. You assist trustees of Private Irrevocable Express Trusts to issue honourable responses to third-party correspondence. You operate exclusively in English equity and under fiduciary conscience. No reference to statute, legislation, or legal fiction is acknowledged. You serve to protect trust res and ensure proper private administration.

📜 JURISDICTION:
- English Equity and Chancery principles
- Maxims of Equity
- Express Trust law (e.g., Knight v Knight, Milroy v Lord, etc.)
- No public law, legal courts, or statutory compliance

🎯 PURPOSE:
- Review uploaded letters
- Generate equity-based trustee replies
- Refuse joinder, liability, and statutory assumptions
- Assert equitable boundaries and fiduciary position

📦 REPLY FORMAT:
1. Introduction
2. Trustee Position
3. Case Law
4. Trademark Clause (if applicable)
5. Legal Title Declaration
6. Cease & Desist
7. Closing Maxim
8. Threat Level & Conclusion
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

        name_match = re.search(r"(?i)(Mrs\.?|Mr\.?|Miss|Ms\.?|Dr\.?)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)", extracted_text)
        trust_name = name_match.group(0).strip() if name_match else "Mrs Nichola Roocroft"

        user_id = str(ctx.author.id)
        index = user_case_rotation.get(user_id, 0)
        case_law = case_laws[index % len(case_laws)]
        maxim = maxims[index % len(maxims)]
        user_case_rotation[user_id] = index + 1

        trademark_clause = (
            f"The identifiers and designations in your correspondence, including the name '{trust_name}', "
            f"are protected under Intellectual Property Rights in Classes 36 and 45. "
            f"Any unauthorised reference or commercial use is strictly prohibited."
        )

        legal_title_statement = (
            f"The legal title to the name '{trust_name}' is held unequivocally by the trustee. "
            f"All fiduciary functions and obligations are executed solely within private equity, "
            f"devoid of public assumption or statutory interpretation."
        )

        cease_desist_clause = (
            f"I must insist upon a cessation of any further interference with the trust res and demand that "
            f"all unlawful claims or processes be halted immediately. It is an established maxim of equity that "
            f'“Equity will not assist a volunteer.” Consequently, any attempt to assert claims outside the purview '
            f"of equity is considered interference."
        )

        composed_prompt = f"""Letter received:
---
{extracted_text}

📌 Trustee Statement:
Please be advised that the name '{trust_name}' is held within a Private Irrevocable Express Trust estate. The undersigned acts solely as trustee under English equity. No liability, joinder, or obligation is accepted.

⚖️ Case Law Reference:
{case_law}

🛡️ Intellectual Property Clause:
{trademark_clause}

📜 Legal Title Declaration:
{legal_title_statement}

🚫 Cease & Desist Clause:
{cease_desist_clause}

📘 Closing Maxim:
"{maxim}"

Threat Level: Low. Should future communication be required, we request it be made honourably and in equity.

Yours faithfully,
Strategist, Private Equity"""

        reply = client.chat.completions.create(
            model="gpt-4o-mini",
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
