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
from collections import defaultdict

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

# Initialize clients
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
letter_counts = defaultdict(int)

# -----------------------------------------------------------
# PROMPTS
# -----------------------------------------------------------

LETTER_PROMPT_TEMPLATE = """
You are a Private Trustee Strategist AI operating under English equity and conscience.
You draft highly strategic, non-generic private responses to uploaded letters from trustees of private express trusts.

Each response includes:
- Clarification that the legal name is held in trust.
- Rebuttal of any implied rights of access (if present).
- Reference to ownership of Trademark Classes 36 and 45.
- Relevant case law (choose best fit).
- Appropriate equity maxim (rotate as needed).
- Threat level assessment (low, moderate, high).
- Organic structure responding directly to content.

NEVER use legal language or imply statutory compliance.
Respond in honour as a strategist only. Respond as if each letter is unique.

Example style:
1. Introduction
2. Trustee Position (roles, trust, name)
3. Specific Response
4. Case Law
5. Equity Maxim
6. Threat Level
7. Close in Honour
"""

# -----------------------------------------------------------
# Events & Commands
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
    letter_counts[user_id] += 1
    letter_number = letter_counts[user_id]

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

        # Name extraction (e.g., Mrs Nichola Roocroft)
        name_match = re.search(r"(Mr|Mrs|Ms|Miss|Dr)\s+[A-Z][a-z]+\s+[A-Z][a-z]+", extracted_text)
        name = name_match.group(0) if name_match else "[Name not found]"

        # Threat detection (basic keywords)
        threat_keywords = ["court", "bailiff", "summons", "prosecution", "legal action"]
        threat_level = "LOW"
        if any(kw in extracted_text.lower() for kw in threat_keywords):
            threat_level = "HIGH"
        elif "payment" in extracted_text.lower() or "final notice" in extracted_text.lower():
            threat_level = "MODERATE"

        # Trigger right of access logic
        if any(word in extracted_text.lower() for word in ["bailiff", "council", "access", "entry"]):
            right_of_access = "An implied right of access is expressly rebutted under trust jurisdiction."
        else:
            right_of_access = ""

        prompt = f"Letter {letter_number} received from user {ctx.author.name} ({ctx.author.id}):\n\n"
        prompt += f"Trustee Name: {name}\n\n"
        prompt += f"Letter Content:\n{extracted_text}\n\n"
        prompt += f"{right_of_access}\nThreat Level: {threat_level}\n\n"
        prompt += "Please generate a private trust strategist response."

        reply = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": LETTER_PROMPT_TEMPLATE},
                {"role": "user", "content": prompt}
            ],
            max_tokens=900
        )

        draft = reply.choices[0].message.content

        # Send privately to user
        try:
            await ctx.author.send(f"**Letter Response #{letter_number}:**\n\n{draft}")
            await ctx.send("Response sent to your private DM.")
        except discord.Forbidden:
            await ctx.send("Couldn't DM you. Please check your privacy settings.")

    except Exception as e:
        await ctx.send(f"Error: {e}")
        print(f"Error: {e}")

# -----------------------------------------------------------
# Run the bot
# -----------------------------------------------------------

bot.run(DISCORD_TOKEN)

