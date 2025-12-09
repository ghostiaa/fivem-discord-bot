# bot.py
import os
import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from dotenv import load_dotenv

load_dotenv()  # .env dosyasını yükle

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
SERVER_CODE = os.getenv("FIVEM_SERVER_CODE", "xjx5kr")

# ---- INTENTS BURADA ----
intents = discord.Intents.default()
intents.message_content = True      # mesaj içerik izni
intents.members = True              # kullanıcı bilgisi izni
# Ses ile ilgili intents yok → audioop yüklenmez
# --------------------------

bot = commands.Bot(command_prefix="!", intents=intents)


async def fetch_players():
    """FiveM serverlist API üzerinden oyuncu listesi çeker."""
    url = f"https://servers-frontend.fivem.net/api/servers/single/{SERVER_CODE}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            players = data.get("Data", {}).get("players", [])
            return players


def parse_identifiers(identifiers):
    """Steam (hex -> 64) ve Discord ID'yi ayrıştırır."""
    steam = None
    discord_id = None

    for ident in identifiers:
        if ident.startswith("steam:"):
            try:
                hex_id = ident.split(":", 1)[1]
                steam = str(int(hex_id, 16))
            except Exception:
                steam = ident.split(":", 1)[1]
        if ident.startswith("discord:"):
            discord_id = ident.split(":", 1)[1]
    return steam, discord_id


@bot.tree.command(name="oyuncu", description="FiveM sunucusundaki ID'ye göre oyuncu bilgisi gösterir.")
@app_commands.describe(id="Sunucu içindeki oyuncu ID'si (sayı)")
async def oyuncu(interaction: discord.Interaction, id: int):
    await interaction.response.defer()

    players = await fetch_players()
    if players is None:
        await interaction.followup.send("Sunucuya erişemedim veya API hatası var.")
        return

    player = next((p for p in players if p.get("id") == id), None)
    if not player:
        await interaction.followup.send(f"ID {id} sunucuda bulunamadı.")
        return

    identifiers = player.get("identifiers", [])
    steam, discord_id = parse_identifiers(identifiers)

    embed = discord.Embed(title="Oyuncu Bilgisi", color=0x00b3ff)
    embed.add_field(name="Sunucu İsim", value=player.get("name") or "Bilinmiyor", inline=False)
    embed.add_field(name="Server ID", value=str(player.get("id")), inline=False)
    embed.add_field(name="SteamID64", value=steam if steam else "Yok", inline=False)

    if discord_id:
        embed.add_field(name="Discord ID", value=discord_id, inline=False)
        embed.add_field(name="Discord Mention", value=f"<@{discord_id}>", inline=False)
    else:
        embed.add_field(name="Discord", value="Bağlı değil", inline=False)

    await interaction.followup.send(embed=embed)


@bot.event
async def on_ready():
    print(f"Bot hazır: {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Slash komutları senkronize edildi: {len(synced)} komut.")
    except Exception as e:
        print("Komut sync hatası:", e)


if __name__ == "__main__":
    if not BOT_TOKEN:
        print("Hata: DISCORD_BOT_TOKEN .env içinde yok.")
    else:
        bot.run(BOT_TOKEN)


