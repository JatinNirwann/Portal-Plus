# PortalPlus

An automated attendance monitoring bot for JIIT Webportal that checks your attendance regularly and sends real-time notifications via Telegram. Features an interactive Telegram bot interface for instant attendance queries and configurable monitoring intervals.

**Note: You need to deploy this somewhere in order to use it continuously.**

## 🚀 Features

- **Automated Attendance Monitoring**: Periodically checks your JIIT portal attendance
- **Real-time Telegram Notifications**: Instant updates when attendance changes
- **Interactive Bot Commands**: Query attendance on-demand via Telegram
- **Configurable Intervals**: Set custom monitoring frequency (5-1440 minutes)
- **Clean Attendance Reports**: Formatted reports with subject-wise breakdown
- **Robust Error Handling**: Automatic retry and graceful error recovery

## 📋 Prerequisites

- Python 3.11 or higher
- JIIT Webportal credentials
- Telegram Bot Token (create via [@BotFather](https://t.me/botfather))
- A server or cloud platform for continuous deployment

## 🛠 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/JatinNirwann/Portal-Plus.git
   cd Portal-Plus
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   # Copy example configuration
   cp .env.example .env
   
   # Edit .env with your credentials
   nano .env
   ```

4. **Set up your environment variables in `.env`**
   ```bash
   JIIT_USERNAME=your_enrollment_number
   JIIT_PASSWORD=your_portal_password
   TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
   TELEGRAM_CHAT_ID=your_telegram_chat_id
   CHECK_INTERVAL_MINUTES=60
   ATTENDANCE_THRESHOLD=75
   LOG_LEVEL=INFO
   ```

## 🤖 Telegram Bot Setup

1. **Create a Telegram Bot**
   - Message [@BotFather](https://t.me/botfather) on Telegram
   - Use `/newbot` command and follow instructions
   - Copy the bot token to your `.env` file

2. **Get Your Chat ID**
   
   There are several ways to find your Telegram Chat ID:
   
   **Method 1: Using Bot (Recommended)**
   - Start a conversation with your newly created bot
   - Send `/start` message to your bot
   - Run the included `get_chat_id.py` script:
     ```bash
     python get_chat_id.py
     ```
   - Copy the displayed chat ID to your `.env` file
   
   **Method 2: Using @userinfobot**
   - Search for `@userinfobot` on Telegram
   - Start a conversation and send any message
   - The bot will reply with your chat ID
   
   **Method 3: Using Telegram Web**
   - Open [web.telegram.org](https://web.telegram.org)
   - Start a chat with your bot
   - Look at the URL: `https://web.telegram.org/z/#123456789`
   - The number after `#` is your chat ID
   
   **Method 4: Using Bot API directly**
   - Send a message to your bot
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Look for `"chat":{"id":123456789}` in the response
   
   Add the chat ID to your `.env` file:
   ```bash
   TELEGRAM_CHAT_ID=123456789
   ```

## 🚀 Usage

### Running Locally (for testing)
```bash
python main.py
```

### Bot Commands
- `/start` - Initialize the bot and get welcome message
- `/help` - Show available commands
- `/attendance` - Get current attendance report
- `/interval [minutes]` - Set monitoring interval (5-1440 minutes)
- `/status` - Check bot and portal connection status

### Sample Attendance Report
```
Attendance Report

Subject-wise:
COA: 75.5%
Data Structures: 82.3%
Operating Systems: 68.9%
Computer Networks: 91.2%
```

## 🌐 Deployment

**Important: You need to deploy this on a server for continuous monitoring.**

### Recommended Deployment Options

1. **VPS/Cloud Server** (Recommended)
   - DigitalOcean, AWS EC2, Google Cloud, Azure
   - Provides 24/7 uptime and reliable internet

2. **Raspberry Pi** (Cost-effective)
   - Home deployment with stable internet
   - Low power consumption

3. **Process Manager** (For server deployments)
   ```bash
   # Using PM2
   npm install -g pm2
   pm2 start main.py --name portalplus --interpreter python3
   pm2 startup
   pm2 save
   ```

### Environment Variables for Production
```bash
# Production .env example
JIIT_USERNAME=x
JIIT_PASSWORD=x
TELEGRAM_BOT_TOKEN=x
TELEGRAM_CHAT_ID=x
CHECK_INTERVAL_MINUTES=60
ATTENDANCE_THRESHOLD=75
LOG_LEVEL=INFO
```

## 📊 Monitoring & Logs

- **Console Output**: Real-time logging information
- **Log Files**: Stored in `jiit_monitor.log` for historical analysis
- **Status Command**: Use `/status` to check system health
- **Error Recovery**: Automatic retry on portal connection failures

## 🔧 Configuration

### Monitoring Interval
- **Minimum**: 5 minutes
- **Maximum**: 1440 minutes (24 hours)
- **Default**: 60 minutes
- **Change via Bot**: `/interval 30` (sets to 30 minutes)

### Attendance Threshold
- **Default**: 75%
- **Purpose**: Alert threshold for low attendance
- **Configurable**: Via `ATTENDANCE_THRESHOLD` in `.env`

## 🚨 Troubleshooting

### Common Issues

1. **Bot not responding**
   - Check if the bot token is correct
   - Verify chat ID is accurate
   - Ensure bot has been started with `/start`

2. **Portal login failures**
   - Verify JIIT credentials are correct
   - Check if portal is accessible
   - Review logs for specific error messages

3. **Deployment issues**
   - Ensure Python 3.11+ is installed
   - Verify all environment variables are set
   - Check internet connectivity on deployment server

### Getting Help
- Check the logs in `jiit_monitor.log`
- Use `/status` command to diagnose issues
- Review the technical documentation in `usage[1].rst`

## 📁 Project Structure

```
Portal-Plus/
├── main.py                 # Application entry point
├── telegram_notifier.py    # Telegram bot functionality
├── jiit_checker.py        # JIIT portal integration
├── session_manager.py     # Portal session management
├── captcha.py            # CAPTCHA handling
├── requirements.txt      # Python dependencies
├── .env.example         # Environment configuration template
├── README.md           # This file
└── usage[1].rst       # Technical documentation
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
