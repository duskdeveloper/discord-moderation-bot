# Discord Moderation Bot

An advanced Discord moderation bot built with Python and discord.py featuring automated filtering, comprehensive user management, and detailed logging capabilities.

## Features

### 🔨 Core Moderation Commands
- **Warn System**: Progressive warning system with configurable actions
- **Timeout Management**: Temporary user restrictions with custom durations
- **User Management**: Kick and ban users with detailed logging
- **Message Management**: Bulk message deletion and content filtering

### 🤖 Auto-Moderation
- **Spam Detection**: Rate limiting and duplicate message detection
- **Profanity Filter**: Customizable word blacklist with automatic actions
- **Excessive Mentions**: Prevent mention spam and raids
- **Emoji Limits**: Control excessive emoji usage
- **Zalgo Text Detection**: Block distorted text that can crash clients

### 📊 Administrative Features
- **Server Configuration**: Flexible per-server settings
- **Moderation Logs**: Comprehensive audit trail with Discord integration
- **User Analytics**: Detailed user information and warning history
- **Welcome System**: Customizable welcome messages for new members
- **Permission Analysis**: Security audits and role hierarchy management

### 🛡️ Security Features
- **Role-based Permissions**: Hierarchical moderation system
- **Immune Roles**: Protect specific roles from auto-moderation
- **Database Security**: SQLite with proper data validation
- **Error Handling**: Robust error management and logging

## Installation

### Prerequisites
- Python 3.8 or higher
- Discord Bot Token
- Required Python packages (installed automatically)

### Setup Steps

1. **Clone or Download** this repository
2. **Install Dependencies**:
   ```bash
   pip install discord.py aiosqlite
   ```

3. **Configure the Bot**:
   - Edit `config.json` to customize default settings
   - Modify blacklist words, spam thresholds, and role permissions

4. **Set Environment Variable**:
   ```bash
   export DISCORD_TOKEN="your_bot_token_here"
   ```
   Or create a `.env` file:
   ```
   DISCORD_TOKEN=your_bot_token_here
   ```

5. **Run the Bot**:
   ```bash
   python main.py
   ```

## Configuration

### Basic Settings (config.json)
```json
{
    "prefix": "!",
    "default_settings": {
        "automod_enabled": true,
        "spam_detection": true,
        "profanity_filter": true,
        "max_warnings": 3,
        "timeout_duration": 300
    },
    "blacklist_words": [
        "word1", "word2"
    ],
    "spam_thresholds": {
        "messages_per_minute": 10,
        "duplicate_messages": 3,
        "mention_limit": 5,
        "emoji_limit": 10
    },
    "moderation_roles": [
        "Moderator", "Admin", "Staff"
    ],
    "immune_roles": [
        "Admin", "Owner", "Bot"
    ]
}
```

### Per-Server Configuration
Use these commands to configure server-specific settings:

- `!config` - View current server settings
- `!config logchannel #channel` - Set moderation log channel
- `!config welcomechannel #channel` - Set welcome message channel
- `!config automod true/false` - Toggle auto-moderation
- `!config maxwarnings 5` - Set maximum warnings before action
- `!config timeoutduration 600` - Set default timeout duration (seconds)

## Commands

### Moderation Commands (Requires Moderator Role)

| Command | Description | Usage |
|---------|-------------|--------|
| `!warn <user> <reason>` | Warn a user | `!warn @user Spamming messages` |
| `!warnings <user>` | View user's warnings | `!warnings @user` |
| `!unwarn <warning_id>` | Remove a specific warning | `!unwarn 123` |
| `!clearwarns <user>` | Clear all warnings for user | `!clearwarns @user` |
| `!timeout <user> <seconds> <reason>` | Timeout a user | `!timeout @user 300 Being disruptive` |
| `!untimeout <user> <reason>` | Remove user timeout | `!untimeout @user Appeal accepted` |
| `!kick <user> <reason>` | Kick a user | `!kick @user Rule violation` |
| `!ban <user> [days] <reason>` | Ban a user | `!ban @user 7 Serious rule violation` |
| `!unban <user_id> <reason>` | Unban a user | `!unban 123456789 Appeal accepted` |
| `!purge <amount> [user]` | Delete messages | `!purge 50` or `!purge 20 @user` |

### Administrative Commands (Requires Administrator)

| Command | Description | Usage |
|---------|-------------|--------|
| `!config` | View server configuration | `!config` |
| `!modlogs [limit]` | View moderation logs | `!modlogs 25` |
| `!stats` | Server statistics | `!stats` |
| `!permissions` | Permission analysis | `!permissions` |

### Information Commands

| Command | Description | Usage |
|---------|-------------|--------|
| `!help` | Show all commands | `!help` |
| `!userinfo <user>` | Detailed user information | `!userinfo @user` |

## Auto-Moderation System

The bot automatically monitors messages for:

### Spam Detection
- **Rate Limiting**: Configurable messages per minute threshold
- **Duplicate Messages**: Detects repeated identical messages
- **Progressive Penalties**: Warnings → Timeout → Ban

### Content Filtering
- **Profanity Filter**: Customizable blacklist with automatic deletion
- **Excessive Mentions**: Prevents @everyone/@here spam and mass mentions
- **Emoji Control**: Limits custom and Unicode emoji spam
- **Zalgo Text**: Blocks corrupted text that can crash Discord clients

### Warning System
The bot uses a progressive punishment system:
1. **First Warning**: User notified, message deleted
2. **Second Warning**: User timed out (configurable duration)
3. **Third Warning**: User banned (configurable action)

Administrators can customize warning thresholds and actions per server.

## Database Structure

The bot uses SQLite with the following tables:

- **guilds**: Server configurations and settings
- **warnings**: User warning history with moderator info
- **moderation_logs**: Complete audit trail of all actions
- **user_timeouts**: Active timeout tracking
- **spam_tracking**: Real-time spam detection data

## Permissions Required

### Bot Permissions
- Send Messages
- Manage Messages (for message deletion)
- Kick Members
- Ban Members
- Moderate Members (for timeouts)
- View Audit Log
- Embed Links

### Role Hierarchy
- Bot role must be higher than users it moderates
- Moderators cannot moderate users with equal/higher roles
- Administrators have override capabilities

## Logging and Monitoring

### File Logging
- All actions logged to `bot.log`
- Configurable log levels (DEBUG, INFO, WARNING, ERROR)
- Structured log format with timestamps

### Discord Logging
- Optional per-server log channels
- Rich embeds with user information
- Action history and audit trails
- Message deletion logs

## Security Considerations

### Data Protection
- User IDs and message content stored securely
- Automatic cleanup of old data
- No sensitive information in logs

### Permission Management
- Role-based access control
- Immune roles for staff protection
- Hierarchical moderation enforcement

### Error Handling
- Graceful handling of missing permissions
- User-friendly error messages
- Comprehensive logging for debugging

## Customization

### Adding Custom Commands
Extend functionality by adding new cogs in the `cogs/` directory.

### Custom Auto-Moderation Rules
Modify `utils/automod.py` to add new detection patterns.

### Database Extensions
The modular database design allows easy addition of new features.

## Troubleshooting

### Common Issues

**Bot doesn't respond to commands:**
- Check bot permissions
- Verify role hierarchy
- Ensure bot is online

**Auto-moderation not working:**
- Check if auto-mod is enabled: `!config`
- Verify user isn't in immune role
- Check spam thresholds in config

**Database errors:**
- Ensure write permissions in bot directory
- Check SQLite installation
- Review logs for specific errors

**Permission errors:**
- Verify bot has required permissions
- Check role hierarchy
- Ensure bot role is high enough

### Support
Check the console logs and `bot.log` file for detailed error information.

## License

This project is open source and available for use and modification.

## Contributing

Feel free to submit issues, feature requests, and improvements.
