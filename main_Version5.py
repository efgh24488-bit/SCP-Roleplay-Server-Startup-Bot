import discord
from discord.ext import commands, tasks
import json
import os
import asyncio
from datetime import datetime, timedelta

CONFIG_FILE = "config.json"
LAST_SSU_FILE = "last_ssu.json"
SSU_LOGS_DIR = "logs"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ----- Utility Functions -----
def load_config():
    if not os.path.exists(CONFIG_FILE):
        config = {
            "token": "",  # Leave blank for Railway; use DISCORD_BOT_TOKEN env var
            "ssu_channel_id": None,
            "ssd_channel_id": None,
            "ssup_channel_id": None,
            "guild_id": None,
            "allowed_roles": []
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        return config
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

def has_role(ctx, config):
    if not config["allowed_roles"]:
        return True
    user_roles = [role.id for role in ctx.author.roles]
    return any(role in user_roles for role in config["allowed_roles"])

def log_ssu(ssu_data):
    if not os.path.exists(SSU_LOGS_DIR):
        os.makedirs(SSU_LOGS_DIR)
    log_file = os.path.join(SSU_LOGS_DIR, f"{datetime.utcnow().date()}.json")
    data = []
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            data = json.load(f)
    data.append(ssu_data)
    with open(log_file, "w") as f:
        json.dump(data, f, indent=2)

def save_last_ssu(ssu_data):
    with open(LAST_SSU_FILE, "w") as f:
        json.dump(ssu_data, f, indent=2)

def load_last_ssu():
    if not os.path.exists(LAST_SSU_FILE):
        return None
    with open(LAST_SSU_FILE, "r") as f:
        return json.load(f)

config = load_config()

# ----- Events -----
@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")

# ----- Commands -----

@bot.command()
async def config_(ctx, *args):
    """Config command to set channels/roles"""
    global config
    if not has_role(ctx, config):
        await ctx.send("You don't have permission to use this command.")
        return
    if not args:
        embed = discord.Embed(title="Bot Configuration", color=0x5865F2)
        for k, v in config.items():
            embed.add_field(name=k, value=str(v), inline=False)
        await ctx.send(embed=embed)
        return
    # Example: !config ssu_channel 1234567890
    if args[0] == "ssu_channel":
        channel_id = int(args[1])
        config["ssu_channel_id"] = channel_id
    elif args[0] == "ssd_channel":
        config["ssd_channel_id"] = int(args[1])
    elif args[0] == "ssup_channel":
        config["ssup_channel_id"] = int(args[1])
    elif args[0] == "add_role":
        role = ctx.guild.get_role(int(args[1]))
        if role and role.id not in config["allowed_roles"]:
            config["allowed_roles"].append(role.id)
    elif args[0] == "remove_role":
        role = ctx.guild.get_role(int(args[1]))
        if role and role.id in config["allowed_roles"]:
            config["allowed_roles"].remove(role.id)
    elif args[0] == "clear_roles":
        config["allowed_roles"] = []
    save_config(config)
    await ctx.send("Configuration updated.")

@bot.command()
async def SSU(ctx, server_name:str, host:str, ping:str, description:str):
    """Start and log server startup"""
    global config
    if not has_role(ctx, config):
        await ctx.send("You don't have permission to use this command.")
        return
    embed = discord.Embed(title="🟢 SERVER STARTUP", color=0x43b581, timestamp=datetime.utcnow())
    embed.add_field(name="Server Name", value=server_name, inline=True)
    embed.add_field(name="Host", value=host, inline=True)
    embed.add_field(name="Ping", value=ping, inline=True)
    embed.add_field(name="Description", value=description, inline=False)
    msg = await ctx.send(embed=embed)
    ssu_data = {
        "server_name": server_name,
        "host": host,
        "ping": ping,
        "description": description,
        "msg_id": msg.id,
        "timestamp": str(datetime.utcnow())
    }
    log_ssu(ssu_data)
    save_last_ssu(ssu_data)

@bot.command()
async def SSD(ctx):
    """Safely shut down the currently running server"""
    global config
    if not has_role(ctx, config):
        await ctx.send("You don't have permission to use this command.")
        return
    last_ssu = load_last_ssu()
    if not last_ssu:
        await ctx.send("No active server session found.")
        return
    embed = discord.Embed(title="🔴 SERVER SHUTDOWN", color=0xf04747, timestamp=datetime.utcnow())
    embed.add_field(name="Server Name", value=last_ssu["server_name"], inline=True)
    embed.add_field(name="Host", value=last_ssu["host"], inline=True)
    embed.add_field(name="Ping", value=last_ssu["ping"], inline=True)
    embed.add_field(name="Description", value=last_ssu["description"], inline=False)
    await ctx.send(embed=embed)
    os.remove(LAST_SSU_FILE)

@bot.command()
async def SSUP(ctx, server_name:str, time:str, role:str, description:str):
    """Create a server startup poll with auto-updating countdown"""
    global config
    if not has_role(ctx, config):
        await ctx.send("You don't have permission to use this command.")
        return
    # time parsing (e.g., '45min', '1d30min')
    seconds = parse_time(time)
    end_time = datetime.utcnow() + timedelta(seconds=seconds)
    embed = discord.Embed(title="📊 SERVER STARTUP POLL", color=0x7289da, timestamp=datetime.utcnow())
    embed.add_field(name="Server Name", value=server_name, inline=True)
    embed.add_field(name="Host Role", value=role, inline=True)
    embed.add_field(name="Description", value=description, inline=False)
    embed.add_field(name="Time Left", value=format_time(seconds), inline=False)
    msg = await ctx.send(embed=embed)
    bot.loop.create_task(update_poll(msg, seconds, end_time))

async def update_poll(msg, seconds, end_time):
    while seconds > 0:
        await asyncio.sleep(60)
        seconds = int((end_time - datetime.utcnow()).total_seconds())
        embed = msg.embeds[0]
        embed.set_field_at(-1, name="Time Left", value=format_time(seconds), inline=False)
        await msg.edit(embed=embed)

def parse_time(timestr):
    # Basic parser for formats like 45min, 1d30min, etc.
    units = {"min":60, "d":86400, "w":604800, "mo":2592000, "y":31536000}
    import re
    pattern = r'(\d+)(y|mo|w|d|min)'
    matches = re.findall(pattern, timestr)
    total = 0
    for val, unit in matches:
        total += int(val)*units[unit]
    return total if total > 0 else 1800  # default 30min

def format_time(seconds):
    # Returns human-readable countdown
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    if s: parts.append(f"{s}s")
    return " ".join(parts) if parts else "0s"

@bot.command()
async def USSUP(ctx, message_id:int):
    """Manually refresh a poll"""
    try:
        msg = await ctx.channel.fetch_message(message_id)
        # simulate refresh by updating timestamp
        embed = msg.embeds[0]
        embed.timestamp = datetime.utcnow()
        await msg.edit(embed=embed)
        await ctx.send("Poll refreshed!")
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

@bot.command()
async def help(ctx):
    help_msg = """**SCP: Roleplay Server Startup Bot Commands**
!SSU [server_name] [@host] [@ping] [description] — Start server
!SSD — Shut down current server
!SSUP [server_name] [time] [@role] [description] — Startup poll
!USSUP <message_id> — Refresh poll
!config — Configure bot channels/roles
!help — Show this help
"""
    await ctx.send(help_msg)

# ----- Run Bot -----
if __name__ == "__main__":
    import os
    bot.run(os.getenv("DISCORD_BOT_TOKEN"))