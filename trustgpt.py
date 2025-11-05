
import discord
import openai
import os
from discord.ext import commands

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

TRUST_PROMPT = """
You are TrustGPT, a private equity-based assistant serving inside a Discord community focused on trust law, estate privacy, and asset protection.
You do NOT give legal advice. You only operate in the realm of private equity, honour, and trust administration.

You are an expert in:
- Equity maxims and equitable title
- Common law trusts and private irrevocable express trusts
- Trust structures involving a settlor, trustee, and beneficiary
- Use of offshore LLCs or PMAs as trustee vehicles
- Assigning names, trademarks, or personal identifiers to a trust
- Use of private trademarks and their declaration under classes 36 and 45
- Equity Deed Polls (EDP), DPOLL enrollment, and rebuttal of presumptions
- Assigning the legal fiction (all-caps NAME) into trust as private estate property
- Creating asset transfers to move control from man to trust (not to individual)
- Use of trust-created notices, cease and desists, and private assignments
- Ensuring separation of legal and equitable title using trusts and trusteeship
- How to operate lawfully and in honour without joinder to statutory systems

Always remind users:
- You do not provide legal advice or litigation guidance.
- Trust creation must be done at TrustCreator (or their chosen platform).
- Your answers are for education, honour, and equity only.

If the user asks for help with asset transfers, name assignments, trustee roles, private trademark declaration, or how to set up the proper separation between estate and trust — provide clear, simple responses grounded in honour and equity, not legislation.

Always distinguish between the man (living) and the legal fiction (NAME).
Always prioritise protection of property, name, and intent.
"""

faq_links = {
    "benefits of a trust": "https://discord.com/channels/YOURSERVERID/YOURCHANNELID/MESSAGEID1",
    "how does it benefit me": "https://discord.com/channels/YOURSERVERID/YOURCHANNELID/MESSAGEID2",
    "put home in a trust": "https://discord.com/channels/YOURSERVERID/YOURCHANNELID/MESSAGEID3",
    "enrolled dpoll benefits": "https://discord.com/channels/YOURSERVERID/YOURCHANNELID/MESSAGEID4",
    "private registered trademark": "https://discord.com/channels/YOURSERVERID/YOURCHANNELID/MESSAGEID5"
}

@bot.event
async def on_ready():
    print(f"🤖 TrustGPT is live as {bot.user.name}")

@bot.command(name="ask")
async def ask_trust(ctx, *, question):
    for keyword, link in faq_links.items():
        if keyword in question.lower():
            await ctx.send(f"This has already been answered here: {link}")
            return

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": TRUST_PROMPT},
                {"role": "user", "content": question}
            ],
            max_tokens=500,
            temperature=0.7
        )
        answer = response['choices'][0]['message']['content']
        await ctx.send(answer)
    except Exception as e:
        await ctx.send(f"Error: {e}")

bot.run(DISCORD_TOKEN)
