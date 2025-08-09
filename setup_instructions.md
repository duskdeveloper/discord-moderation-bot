# Setup Instructions

## Quick Start

### 1. Create Discord Application
1. Go to https://discord.com/developers/applications
2. Click "New Application" and name your bot
3. Go to the "Bot" section
4. Click "Add Bot"
5. Copy the bot token (keep it secret!)

### 2. Install Dependencies
```bash
pip install discord.py aiosqlite
```

### 3. Set Bot Token
**Option A: Environment Variable**
```bash
export DISCORD_TOKEN="your_bot_token_here"
```

**Option B: Create .env file**
```env
DISCORD_TOKEN=your_bot_token_here
```

### 4. Run the Bot
```bash
python main.py
```

## Bot Permissions Setup

When inviting your bot to servers, ensure it has these permissions:
- Send Messages
- Manage Messages
- Kick Members
- Ban Members
- Moderate Members (for timeouts)
- View Audit Log
- Embed Links

**Invite URL Template:**
```
https://discord.com/oauth2/authorize?client_id=YOUR_BOT_ID&permissions=1099511627862&scope=bot
```

Replace `YOUR_BOT_ID` with your bot's application ID from the Discord Developer Portal.

## Configuration

### Basic Configuration
Edit `config.json` to customize:
- Command prefix
- Default auto-moderation settings
- Blacklisted words
- Spam detection thresholds
- Moderation roles

### Server-Specific Settings
Once the bot is in your server, use these commands:
- `!config` - View current settings
- `!config logchannel #logs` - Set moderation log channel
- `!config automod true` - Enable auto-moderation
- `!config maxwarnings 3` - Set warning limit

## Required Bot Permissions

The bot needs these Discord permissions to function properly:

| Permission | Purpose |
|------------|---------|
| Send Messages | Basic communication |
| Manage Messages | Delete rule-violating messages |
| Kick Members | Remove problematic users |
| Ban Members | Permanently remove users |
| Moderate Members | Apply timeouts |
| View Audit Log | Track moderation actions |
| Embed Links | Send rich message embeds |

## Troubleshooting

### Bot doesn't respond
- Check if bot is online in Discord
- Verify bot has "Send Messages" permission
- Ensure command prefix is correct (default: `!`)

### Moderation commands fail
- Check bot role hierarchy (bot role must be higher than target users)
- Verify bot has required permissions
- Check console/log files for error details

### Database issues
- Ensure bot has write permissions in its directory
- Check if SQLite is properly installed
- Review error logs for specific database errors