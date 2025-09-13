# SCP: Roleplay Server Startup Discord Bot

A feature-rich Discord bot for server startup/shutdown/poll announcements.

## 🚀 Deploy on Railway

1. **Fork/clone this repo.**
2. **Go to [railway.app](https://railway.app/) and create a new project.**
3. **Connect your GitHub repo or upload your code.**
4. **Add your Discord bot token as an environment variable:**
   - Key: `DISCORD_BOT_TOKEN`
   - Value: `Your token here`

5. **Deploy! Railway will install dependencies and start your bot.**

---

## 🛠 Commands

| Command | Description |
|---------|-------------|
| `!SSU [server_name] [@host] [@ping] [description]` | Start and log a server startup |
| `!SSD` | Shut down the currently running server |
| `!SSUP [server_name] [time] [@role] [description]` | Create a startup poll |
| `!USSUP <message_id>` | Manually refresh a poll |
| `!config` | Configure channels/roles |
| `!help` | Show help message |

---

## 💡 Credits

Built with Python + discord.py for SCP: Roleplay Server Community.