# Full Discord bot script with GPT-4, Google Vision OCR, and equity-based trust prompts
# Includes: Auto-Tone Classification, Threat Scoring, Correspondence Type Detection,
# Private Trustee Response Generation, Always DM Output.

import discord
import os
from discord.ext import commands
from openai import OpenAI
import aiohttp
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

creds_json = base64.b64decode(creds_b64).decode("utf-8")
GCREDS = json.loads(creds_json)

client = OpenAI(api_key=OPENAI_API_KEY)
vision_creds = service_account.Credentials.from_service_account_info(GCREDS)
vision_client = vision.ImageAnnotatorClient(credentials=vision_creds)

# -----------------------------------------------------------
# Discord bot setup
# -----------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# -----------------------------------------------------------
# CLASSIFIER PROMPTS
# -----------------------------------------------------------

TONE_CLASSIFIER = """
Classify this letter by severity only.

Categories:
ADMIN — harmless information, statements, admin updates
REQUEST — asking for something, requesting action or contact
DEMAND — overdue, payment demand, firm tone, no threat
ESCALATION — final notice, "we may take action", transfer warning
THREAT — mentions enforcement, visits, recovery teams, or strong pressure

Reply with ONE word: ADMIN, REQUEST, DEMAND, ESCALATION, THREAT.
"""

TYPE_CLASSIFIER = """
Identify the type of correspondence:

Options:
COUNCIL_TAX
ENERGY
WATER
DEBT_COLLECTION
SOLICITOR
BANK_FINANCE
LOCAL_AUTHORITY
GENERAL

Choose ONLY one.
"""

THREAT_SCORE_CLASSIFIER = """
Score the severity of this letter on a scale of 0–100:

0 = harmless admin letter  
100 = severe aggressive threat  

Return only a number.
"""

# -----------------------------------------------------------
# UNIVERSAL TRUSTEE LETTER PROMPT WITH MODE C SUPPORT
# -----------------------------------------------------------

LETTER_PROMPT = """
You are a Private Trustee Strategist operating under English Equity and Conscience.
You respond ONLY in private equity, never legal, never statutory, never regulatory. 
You act calmly, honourably, and in good conscience. No legal terminology, no legal 
rights, no consequences, no demands, no refusal, no enforcement language.

You will be given:
- The extracted letter text
- The detected severity category
- The detected letter type
- A threat score (0–100)

Your response must adapt:

TONE MODES:
ADMIN (0–20): Gentle, courteous clarification.  
REQUEST (20–40): Clear boundary, request for proper constitution.  
DEMAND (40–60): Firm non-recognition of obligation without evidence.  
ESCALATION (60–80): Strong firm position, request strict proof + authority.  
THREAT (80–100): Activate MODE C — Firm Trustee Position.  
    - Strong boundaries  
    - Honourable  
    - Calm  
    - No acceptance of obligation  
    - No legal advice  
    - Still non-adversarial  
    - Protect trust res and beneficiaries  

Apply exactly ONE equity case law:
- Knight v Knight (1840)
- Paul v Constance (1976)
- Milroy v Lord (1862)
- Re Kayford (1975)
- Tinsley v Milligan (1994)

Follow this structure:

1. Introduction  
   - Acknowledge receipt in honour  
   - Maintain trustee capacity

2. Trustee Position  
   - Adapt strength using tone mode  
   - Never accept obligation unless properly constituted  
   - Request proof, authority, origin, documentation  
   - Maintain private jurisdiction  
   - Avoid joinder

3. Case Law (one only)  
   - Apply it briefly and relevantly

4. Closing Maxim  
   - Equity will not assist a volunteer  
   - Equity acts in personam  
   - Equity looks to intent, not form  
   - A trustee must act in good conscience

Never mention:
- Law
- Statutes
- Courts
- Enforcement
- Public rights
- Legal processes
- "AI" or "model"
"""

# -----------------------------------------------------------
# BOT COMMANDS
# -----------------------------------------------------------

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user.name}")

@bot.command(name="letter")
async def process_letter(ctx):

    # Always send DM; notify in channel
    await ctx.send("Your trustee response is being prepared and will be sent privately.")

    if not ctx.message.attachments:
        await ctx.author.send("Please upload a letter (PDF or image).")
        return

    attachment = ctx.message.attachments[0]

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                data = await resp.read()

        # OCR extraction
        image = vision.Image(content=data)
        result = vision_client.document_text_detection(image=image)
        extracted_text = result.full_text_annotation.text

        # CLASSIFY TONE
        tone_result = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": TONE_CLASSIFIER},
                {"role": "user", "content": extracted_text}
            ],
            max_tokens=10
        )
        tone = tone_result.choices[0].message.content.strip().upper()

        # CLASSIFY TYPE
        type_result = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": TYPE_CLASSIFIER},
                {"role": "user", "content": extracted_text}
            ],
            max_tokens=10
        )
        letter_type = type_result.choices[0].message.content.strip().upper()

        # THREAT SCORE
        score_result = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": THREAT_SCORE_CLASSIFIER},
                {"role": "user", "content": extracted_text}
            ],
            max_tokens=10
        )
        threat_score = score_result.choices[0].message.content.replace("\n", "").strip()

        # TRUSTEE RESPONSE
        combined_prompt = f"""
Severity Category: {tone}
Letter Type: {letter_type}
Threat Score: {threat_score}

Letter Content:
{extracted_text}

Please prepare the trustee's equity-based response.
"""

        reply = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": LETTER_PROMPT},
                {"role": "user", "content": combined_prompt}
            ],
            max_tokens=1000
        )

        final_response = reply.choices[0].message.content

        # SEND TO USER PRIVATELY
        await ctx.author.send(f"**Your Private Trustee Response:**\n\n{final_response}")

    except Exception as e:
        await ctx.author.send(f"Error: {e}")

# -----------------------------------------------------------
# RUN BOT
# -----------------------------------------------------------

bot.run(DISCORD_TOKEN)
