import os
import json
import asyncio
import secrets
import string
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "").strip()

try:
    OWNER_ID = int(os.getenv("OWNER_ID", "0").strip())
except ValueError:
    OWNER_ID = 0

# Server Lock ID (0 = all servers allowed)
try:
    ALLOWED_GUILD_ID = int(os.getenv("ALLOWED_GUILD_ID", "0").strip())
except ValueError:
    ALLOWED_GUILD_ID = 0

# Channel Lock ID (0 = all channels allowed)
try:
    ALLOWED_CHANNEL_ID = int(os.getenv("ALLOWED_CHANNEL_ID", "0").strip())
except ValueError:
    ALLOWED_CHANNEL_ID = 0

# Log Channel ID
try:
    LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0").strip())
except ValueError:
    LOG_CHANNEL_ID = 0

# ✅ WORKING GIF URL (direct .gif link)
GIF_URL = "https://imagetourl.cloud/78y8cpendiyh.gif"

KEYS_FILE = "keys.json"
ACCESS_FILE = "access_codes.json"
SETTINGS_FILE = "settings.json"

claim_lock = asyncio.Lock()

ALLOWED_GUILDS = set()
if ALLOWED_GUILD_ID != 0:
    ALLOWED_GUILDS.add(ALLOWED_GUILD_ID)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================
# SECURITY CHECK (OWNER ONLY)
# =========================
def owner_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            embed = discord.Embed(
                title="❌ ACCESS DENIED",
                description="Yeh command sirf **Bot Owner** use kar sakta hai.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)


# =========================
# JSON FUNCTIONS - KEYS
# =========================

def create_keys_file():
    if not os.path.exists(KEYS_FILE):
        data = {"stock": {}, "claimed": {}, "owner_claims": []}
        with open(KEYS_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)


def load_keys():
    create_keys_file()
    try:
        with open(KEYS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            data = {"stock": {}, "claimed": {}, "owner_claims": []}

        if "keys" in data:
            old_keys = data.pop("keys", [])
            stock = data.setdefault("stock", {})
            for item in old_keys:
                if isinstance(item, str):
                    stock.setdefault("1", []).append(item)
                elif isinstance(item, dict):
                    d = str(item.get("days", 1))
                    k = item.get("key", "")
                    if k:
                        stock.setdefault(d, []).append(k)

        if not isinstance(data.get("stock"), dict):
            data["stock"] = {}
        if not isinstance(data.get("claimed"), dict):
            data["claimed"] = {}
        if not isinstance(data.get("owner_claims"), list):
            data["owner_claims"] = []

        return data
    except (json.JSONDecodeError, OSError):
        return {"stock": {}, "claimed": {}, "owner_claims": []}


def save_keys(data):
    temp_file = KEYS_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)
    os.replace(temp_file, KEYS_FILE)


# =========================
# JSON FUNCTIONS - SETTINGS
# =========================

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        data = {"free_key_enabled": True}
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return data
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "free_key_enabled" not in data:
            data["free_key_enabled"] = True
        return data
    except Exception:
        return {"free_key_enabled": True}

def save_settings(data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# =========================
# JSON FUNCTIONS - ACCESS CODES
# =========================

def load_access_codes():
    if not os.path.exists(ACCESS_FILE):
        with open(ACCESS_FILE, "w", encoding="utf-8") as f:
            json.dump({"codes": {}}, f, indent=4)
        return {"codes": {}}
    try:
        with open(ACCESS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"codes": {}}
        data.setdefault("codes", {})
        return data
    except (json.JSONDecodeError, OSError):
        return {"codes": {}}


def save_access_codes(data):
    temp = ACCESS_FILE + ".tmp"
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    os.replace(temp, ACCESS_FILE)


def generate_code(length=8):
    chars = string.ascii_uppercase + string.digits
    return "AXB-" + "".join(secrets.choice(chars) for _ in range(length))


# =========================
# CHECKS
# =========================

def is_owner_user(user_id: int):
    return user_id == OWNER_ID

def is_allowed_server(guild):
    if guild is None:
        return False
    if ALLOWED_GUILD_ID == 0:
        return True
    return guild.id in ALLOWED_GUILDS

def is_allowed_channel(user_id: int, channel_id: int):
    if is_owner_user(user_id):
        return True
    if ALLOWED_CHANNEL_ID != 0 and channel_id != ALLOWED_CHANNEL_ID:
        return False
    return True


# =========================
# EMBEDS (GIF ADDED HERE)
# =========================

def success_embed(user, key, expires_at, days, access_name="PREMIUM"):
    embed = discord.Embed(
        title="💎 LIB BYPASS KEY ACTIVATED 💎",
        color=discord.Color.from_rgb(147, 51, 234)
    )

    # ✅ GIF as big image
    if GIF_URL and GIF_URL.startswith("http"):
        embed.set_image(url=GIF_URL)

    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="👤 USER", value=f"```{key}```", inline=False)
    embed.add_field(name="🔒 PASSWORD", value="```1```", inline=False)
    embed.add_field(name="👤 USER", value=user.mention, inline=True)
    embed.add_field(name="🟢 STATUS", value="✅ ACTIVE", inline=True)
    embed.add_field(name="👑 ACCESS", value=f"{access_name}", inline=True)
    embed.add_field(name="🔒HWID", value="LOOK", inline=True)
    embed.add_field(name="📅 ACTIVE", value=f"{days} DAY", inline=True)
    embed.add_field(name="⏰ EXPIRES ON", value=f"{expires_at.strftime('%d-%m-%Y %H:%M')}", inline=True)
    embed.set_footer(text="AXB OFFICIAL")
    return embed


def error_embed(title: str, description: str):
    embed = discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=discord.Color.from_rgb(239, 68, 68)
    )
    embed.set_footer(text="AXB OFFICIAL")
    return embed


# =========================
# LOG FUNCTION
# =========================

async def send_log(user, key, days, access_name):
    if LOG_CHANNEL_ID == 0:
        return
    try:
        channel = bot.get_channel(LOG_CHANNEL_ID)
        if not channel:
            return
        log_embed = discord.Embed(title="📝 NEW KEY CLAIMED", color=discord.Color.green())
        log_embed.set_thumbnail(url=user.display_avatar.url)
        log_embed.add_field(name="👤 User", value=user.mention, inline=True)
        log_embed.add_field(name="🆔 User ID", value=f"`{user.id}`", inline=True)
        log_embed.add_field(name="🔑 Key", value=f"```{key}```", inline=False)
        log_embed.add_field(name="📅 Days", value=f"`{days}`", inline=True)
        log_embed.add_field(name="👑 Access Type", value=f"`{access_name}`", inline=True)
        log_embed.set_footer(text=f"AXB OFFICIAL | {datetime.now(timezone.utc).strftime('%d-%m-%Y %H:%M:%S UTC')}")
        await channel.send(embed=log_embed)
    except Exception as e:
        print(f"Log send error: {e}")


# =========================
# BOT EVENTS (SINGLE CLEAN on_ready)
# =========================

@bot.event
async def on_ready():
    create_keys_file()
    load_settings()

    tree_cmds = bot.tree.get_commands()
    print(f"🔍 DEBUG: Tree mein {len(tree_cmds)} commands hain:")
    for cmd in tree_cmds:
        print(f"   - /{cmd.name}")

    try:
        if ALLOWED_GUILD_ID != 0:
            guild_obj = discord.Object(id=ALLOWED_GUILD_ID)

            # ✅ STEP 1: Guild mein commands deploy karein
            bot.tree.copy_global_to(guild=guild_obj)
            synced = await bot.tree.sync(guild=guild_obj)
            print("=" * 55)
            print(f"BOT ONLINE: {bot.user}")
            print(f"SLASH COMMANDS SYNCED TO GUILD {ALLOWED_GUILD_ID}: {len(synced)}")
            print("=" * 55)

            # ✅ STEP 2: Discord se GLOBAL commands clear karein (no duplicates)
            try:
                await bot.http.bulk_upsert_global_commands(bot.application_id, [])
                print("🧹 Global commands cleared from Discord (no duplicates).")
            except Exception as e:
                print(f"Global clear error: {e}")

        else:
            synced = await bot.tree.sync()
            print("=" * 55)
            print(f"BOT ONLINE: {bot.user}")
            print("⚠️ ALLOWED_GUILD_ID not set — commands deployed globally!")
            print(f"SLASH COMMANDS SYNCED: {len(synced)}")
            print("=" * 55)

    except Exception as error:
        print(f"Slash command sync error: {error}")


@bot.event
async def on_guild_join(guild: discord.Guild):
    print(f"✅ Bot joined: {guild.name} ({guild.id})")

    if ALLOWED_GUILD_ID != 0 and guild.id != ALLOWED_GUILD_ID:
        try:
            guild_obj = discord.Object(id=guild.id)
            bot.tree.clear_commands(guild=guild_obj)
            await bot.tree.sync(guild=guild_obj)
            print(f"🧹 Commands cleared for unauthorized guild: {guild.id}")
        except Exception as e:
            print(f"Clear commands error: {e}")

    try:
        owner = await bot.fetch_user(OWNER_ID)
        if owner:
            embed = discord.Embed(
                title="🎉 BOT ADDED TO NEW SERVER",
                description=f"**Server:** {guild.name}\n**ID:** `{guild.id}`",
                color=discord.Color.from_rgb(147, 51, 234)
            )
            await owner.send(embed=embed)
    except Exception:
        pass


@bot.tree.interaction_check
async def global_server_check(interaction: discord.Interaction) -> bool:
    if ALLOWED_GUILD_ID == 0:
        return True
    if not is_allowed_server(interaction.guild):
        embed = error_embed("SERVER NOT ALLOWED", "This bot is not authorized to work in this server.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return False
    return True


# =========================
# CORE CLAIM FUNCTION
# =========================

async def process_key_claim(user, days):
    async with claim_lock:
        data = load_keys()
        user_id = str(user.id)
        owner = is_owner_user(user.id)
        now = datetime.now(timezone.utc)
        days_str = str(days)

        if not owner and user_id in data["claimed"]:
            return error_embed(
                "ALREADY CLAIMED",
                "\n\n"
            ), None

        stock = data.get("stock", {})
        available = stock.get(days_str, [])

        if not available:
            return error_embed("OUT OF STOCK", f"**{days} DAY**"), None

        key = str(available.pop(0)).strip()
        if not available:
            del stock[days_str]
        else:
            stock[days_str] = available

        data["stock"] = stock
        expires = now + timedelta(days=days)

        if owner:
            owner_claims = data.setdefault("owner_claims", [])
            owner_claims.append({
                "username": str(user), "user_id": user_id, "key": key,
                "claimed_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "expires_at": expires.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "duration": f"{days} DAY(S)", "status": "ACTIVE"
            })
            access_name = "OWNER ACCESS"
        else:
            data["claimed"][user_id] = {
                "username": str(user), "key": key,
                "claimed_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "expires_at": expires.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "duration": f"{days} DAY(S)", "status": "ACTIVE"
            }
            access_name = "PREMIUM"

        save_keys(data)
        embed = success_embed(user, key, expires, days, access_name)
        await send_log(user, key, days, access_name)
        return embed, key


# =========================
# AUTO LISTEN: '!free key'
# =========================

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    content_clean = message.content.strip().lower()

    if content_clean in ["!free key", "!freekey", "!free-key"]:
        if ALLOWED_GUILD_ID != 0 and message.guild and message.guild.id != ALLOWED_GUILD_ID:
            return

        settings = load_settings()
        if not settings.get("free_key_enabled", True):
            embed = error_embed("FREE  TRIAL OFF", "**CONECT OWNER**  <@1312467813771907173> ")
            await message.channel.send(embed=embed)
            return

        embed, key = await process_key_claim(message.author, 1)
        await message.channel.send(embed=embed)
        return

    await bot.process_commands(message)


# =========================
# SLASH COMMANDS (PUBLIC)
# =========================

@bot.tree.command(name="claim", description="Claim a 1-day free trial key")
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
async def claim(interaction: discord.Interaction):
    if not is_allowed_channel(interaction.user.id, interaction.channel_id):
        embed = error_embed("WRONG CHANNEL", f"Use in <#{ALLOWED_CHANNEL_ID}>.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    embed, key = await process_key_claim(interaction.user, 1)
    if key:
        await interaction.response.send_message(embed=embed, ephemeral=False)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="create_key", description="Claim a key — 1, 7, or 30 days")
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.describe(days="Choose duration")
@app_commands.choices(days=[
    app_commands.Choice(name="1 Day", value=1),
    app_commands.Choice(name="7 Days", value=7),
    app_commands.Choice(name="30 Days", value=30),
])
async def create_key_command(interaction: discord.Interaction, days: app_commands.Choice[int]):
    if not is_allowed_channel(interaction.user.id, interaction.channel_id):
        embed = error_embed("WRONG CHANNEL", f"Use in <#{ALLOWED_CHANNEL_ID}>.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    embed, key = await process_key_claim(interaction.user, days.value)
    if key:
        await interaction.response.send_message(embed=embed, ephemeral=False)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=True)


# =========================
# OWNER COMMANDS (SECURED)
# =========================

@bot.tree.command(name="freekey-toggle", description="Owner: Turn !free key system ON or OFF")
@owner_only()
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.describe(status="Choose ON or OFF")
@app_commands.choices(status=[
    app_commands.Choice(name="ON (Enable)", value="on"),
    app_commands.Choice(name="OFF (Disable)", value="off"),
])
async def freekey_toggle_command(interaction: discord.Interaction, status: app_commands.Choice[str]):
    settings = load_settings()

    if status.value == "on":
        settings["free_key_enabled"] = True
        msg = "✅ **!free key** system is now **ON**."
        color = discord.Color.green()
    else:
        settings["free_key_enabled"] = False
        msg = "🛑 **!free key** system is now **OFF**."
        color = discord.Color.red()

    save_settings(settings)

    embed = discord.Embed(title="⚙️ SYSTEM UPDATED", description=msg, color=color)
    embed.set_footer(text="AXB OFFICIAL")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="owner_key", description="Owner: Add key to stock")
@owner_only()
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.describe(key="Key string", days="Duration in days")
async def owner_key_command(interaction: discord.Interaction, key: str, days: int):
    key = key.strip()
    if not key or days <= 0:
        embed = error_embed("INVALID", "Key/days invalid.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    data = load_keys()
    days_str = str(days)

    for d, kl in data["stock"].items():
        if key in kl:
            embed = error_embed("DUPLICATE KEY", f"In stock ({d} days).")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
    for ud in data["claimed"].values():
        if ud.get("key") == key:
            embed = error_embed("CLAIMED KEY", "Already claimed.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
    for od in data.get("owner_claims", []):
        if od.get("key") == key:
            embed = error_embed("CLAIMED KEY", "Already claimed by owner.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

    data["stock"].setdefault(days_str, []).append(key)
    save_keys(data)
    total = len(data["stock"][days_str])
    embed = discord.Embed(title="✅ OWNER KEY ADDED", description=f"• **Key:** `{key}`\n• **Days:** `{days}`\n• **Stock:** `{total}`", color=discord.Color.from_rgb(147, 51, 234))
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="addkey", description="Owner: Add key to stock (default 1 day)")
@owner_only()
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.describe(key="Key string", days="Duration (default 1)")
async def addkey_command(interaction: discord.Interaction, key: str, days: int = 1):
    key = key.strip()
    if not key or days <= 0:
        embed = error_embed("INVALID", "Key/days invalid.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    data = load_keys()
    days_str = str(days)

    for d, kl in data["stock"].items():
        if key in kl:
            embed = error_embed("DUPLICATE KEY", f"In stock ({d} days).")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
    for ud in data["claimed"].values():
        if ud.get("key") == key:
            embed = error_embed("CLAIMED KEY", "Already claimed.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
    for od in data.get("owner_claims", []):
        if od.get("key") == key:
            embed = error_embed("CLAIMED KEY", "Already claimed by owner.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

    data["stock"].setdefault(days_str, []).append(key)
    save_keys(data)
    total = len(data["stock"][days_str])
    embed = discord.Embed(title="✅ KEY ADDED", description=f"• **Key:** `{key}`\n• **Days:** `{days}`\n• **Stock:** `{total}`", color=discord.Color.from_rgb(147, 51, 234))
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="all-keys-delete", description="Owner: Delete all records")
@owner_only()
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
async def all_keys_delete_command(interaction: discord.Interaction):
    async with claim_lock:
        data = load_keys()
        data["stock"] = {}
        data["claimed"] = {}
        data["owner_claims"] = []
        save_keys(data)
    embed = discord.Embed(title="🗑️ ALL KEYS DELETED", description="Saara data clear kar diya gaya hai.", color=discord.Color.from_rgb(147, 51, 234))
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="key", description="Owner: View latest owner claim")
@owner_only()
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
async def key_command(interaction: discord.Interaction):
    data = load_keys()
    oc = data.get("owner_claims", [])
    if not oc:
        embed = error_embed("NO OWNER KEYS", "No owner claims yet.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    latest = oc[-1]
    embed = discord.Embed(title="🔑 LATEST OWNER KEY", description=f"```{latest['key']}```", color=discord.Color.from_rgb(147, 51, 234))
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="status", description="Owner: Check trial status")
@owner_only()
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
async def status_command(interaction: discord.Interaction):
    data = load_keys()
    uid = str(interaction.user.id)
    oc = data.get("owner_claims", [])
    if oc:
        ud = oc[-1]
    elif uid in data["claimed"]:
        ud = data["claimed"][uid]
    else:
        embed = error_embed("NO KEY FOUND", "No active claim.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        expiry = datetime.strptime(ud["expires_at"], "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) >= expiry:
            ud["status"] = "EXPIRED"
            save_keys(data)
    except Exception:
        pass

    status = ud.get("status", "UNKNOWN")
    status_text = "`✅ ACTIVE`" if status == "ACTIVE" else "`🔴 EXPIRED`"
    embed = discord.Embed(title="📊 OWNER TRIAL STATUS", color=discord.Color.from_rgb(147, 51, 234))
    embed.add_field(name="🔑 KEY", value=f"```{ud.get('key', 'N/A')}```", inline=False)
    embed.add_field(name="🟢 STATUS", value=status_text, inline=True)
    embed.add_field(name="📅 DAYS", value=f"`{ud.get('duration', 'N/A')}`", inline=True)
    embed.add_field(name="⏰ EXPIRES", value=f"`{ud.get('expires_at', 'N/A')}`", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="stock", description="Owner: Check key stock")
@owner_only()
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
async def stock_command(interaction: discord.Interaction):
    data = load_keys()
    stock = data.get("stock", {})
    claimed = len(data.get("claimed", {}))
    owner_claimed = len(data.get("owner_claims", []))
    total_issued = claimed + owner_claimed
    total_stock = sum(len(v) for v in stock.values())

    embed = discord.Embed(title="💎 KEY STOCK (BY DAYS)", color=discord.Color.from_rgb(147, 51, 234))
    if not stock:
        embed.add_field(name="📦 STOCK", value="`Empty`", inline=False)
    else:
        for d in sorted(stock.keys(), key=lambda x: int(x) if x.isdigit() else 9999):
            embed.add_field(name=f"📅 {d} DAY(S)", value=f"`{len(stock[d])}`", inline=True)

    embed.add_field(name="🟢 TOTAL STOCK", value=f"`{total_stock}`", inline=True)
    embed.add_field(name="🔴 USER CLAIMED", value=f"`{claimed}`", inline=True)
    embed.add_field(name="👑 OWNER CLAIMED", value=f"`{owner_claimed}`", inline=True)
    embed.add_field(name="📦 TOTAL ISSUED", value=f"`{total_issued}`", inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="removeuser", description="Owner: Remove user's trial claim")
@owner_only()
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.describe(user="Discord user")
async def removeuser_command(interaction: discord.Interaction, user: discord.User):
    data = load_keys()
    uid = str(user.id)
    if uid not in data["claimed"]:
        embed = error_embed("USER NOT FOUND", "No claim record.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    del data["claimed"][uid]
    save_keys(data)
    embed = discord.Embed(title="✅ USER REMOVED", description=f"Claim removed for {user.mention}.", color=discord.Color.from_rgb(147, 51, 234))
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="reloadkeys", description="Owner: Reload key file")
@owner_only()
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
async def reloadkeys_command(interaction: discord.Interaction):
    data = load_keys()
    ts = sum(len(v) for v in data.get("stock", {}).values())
    embed = discord.Embed(title="✅ KEY FILE LOADED", description=f"Stock: `{ts}`\nClaimed: `{len(data['claimed'])}`", color=discord.Color.from_rgb(147, 51, 234))
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="list-access", description="Owner: List all access codes")
@owner_only()
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
async def list_access_command(interaction: discord.Interaction):
    data = load_access_codes()
    codes = data.get("codes", {})
    if not codes:
        embed = error_embed("NO CODES", "No access codes yet.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    embed = discord.Embed(title=f"📋 ALL ACCESS CODES ({len(codes)})", color=discord.Color.from_rgb(147, 51, 234))
    for code, info in list(codes.items())[:20]:
        embed.add_field(name=f"`{code}`", value=f"To: <@{info['given_to']}>\nUses: `{info['uses_left']}`", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="check-access", description="Check bot access in this server")
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
async def check_access_command(interaction: discord.Interaction):
    if not interaction.guild:
        embed = error_embed("ERROR", "Server only command.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    bm = interaction.guild.get_member(bot.user.id)
    if not bm:
        embed = error_embed("ERROR", "Bot member not found.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    perms = bm.guild_permissions
    checks = {
        "Administrator": perms.administrator,
        "Manage Server": perms.manage_guild,
        "Manage Channels": perms.manage_channels,
        "Manage Messages": perms.manage_messages,
        "Send Messages": perms.send_messages,
        "Embed Links": perms.embed_links,
        "Slash Commands": perms.use_application_commands,
    }

    embed = discord.Embed(title="🔐 BOT ACCESS STATUS", description=f"**Server:** {interaction.guild.name}", color=discord.Color.from_rgb(147, 51, 234) if perms.administrator else discord.Color.orange())
    for name, status in checks.items():
        emoji = "✅" if status else "❌"
        embed.add_field(name=f"{emoji} {name}", value="`Granted`" if status else "`Denied`", inline=True)

    embed.add_field(name="🎉 OVERALL", value="**FULL ACCESS**" if perms.administrator else "**LIMITED**", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="server-list", description="Owner: List all bot servers")
@owner_only()
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
async def server_list_command(interaction: discord.Interaction):
    guilds = bot.guilds
    if not guilds:
        embed = error_embed("NO SERVERS", "Bot is not in any server.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    embed = discord.Embed(title=f"🌐 BOT SERVERS ({len(guilds)})", color=discord.Color.from_rgb(147, 51, 234))
    for i, g in enumerate(guilds[:25], start=1):
        embed.add_field(name=f"{i}. {g.name}", value=f"ID: `{g.id}` | Members: `{g.member_count}`", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# =========================
# ERROR HANDLER
# =========================

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        return
    print(f"COMMAND ERROR: {error}")
    embed = error_embed("AN ERROR OCCURRED", "Please try again.")
    try:
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception:
        pass


# =========================
# RUN BOT
# =========================

if not TOKEN:
    print("❌ DISCORD_TOKEN IS MISSING FROM .env")
elif OWNER_ID == 0:
    print("❌ OWNER_ID IS MISSING OR INVALID")
else:
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("❌ ERROR: INVALID DISCORD BOT TOKEN")
    except Exception as error:
        print(f"❌ BOT START ERROR: {error}")