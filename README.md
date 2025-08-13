# JIIT Portal Monitor

A comprehensive Python application that automatically monitors the JIIT Webportal for attendance, marks, and notices, with WhatsApp notifications and chatbot functionality.

## Features

- **Automatic Login**: Uses existing CAPTCHA handling logic from `captcha.py` (preserved without modifications)
- **Periodic Monitoring**: Configurable intervals for checking portal updates
- **WhatsApp Notifications**: Automatic alerts for low attendance, new marks, and notices
- **WhatsApp Chatbot**: Interactive bot for real-time portal queries
- **Robust Error Handling**: Automatic re-login on session expiry
- **Production Ready**: Structured for deployment on VPS/cloud platforms

## Prerequisites

- Python 3.8 or higher
- Twilio account with WhatsApp API access
- JIIT student credentials

## Installation

1. **Clone/Download the project**
   ```bash
   git clone <repository_url>
   cd jiit-portal-monitor
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   
   Copy the `.env.example` to `.env` and fill in your credentials:
   ```bash
   cp .env .env.local
   ```
   
   Edit `.env` with your details:
   ```
   # JIIT Portal Credentials
   JIIT_USERNAME=your_student_id
   JIIT_PASSWORD=your_password
   
   # Twilio Configuration
   TWILIO_ACCOUNT_SID=your_account_sid
   TWILIO_AUTH_TOKEN=your_auth_token
   TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
   WHATSAPP_TO=whatsapp:+1234567890
   
   # Alert Configuration
   ATTENDANCE_THRESHOLD=75
   CHECK_INTERVAL_MINUTES=60
   
   # Server Configuration
   WEBHOOK_PORT=5000
   WEBHOOK_HOST=0.0.0.0
   
   # Logging Configuration
   LOG_LEVEL=INFO
   ```

## Twilio Setup

1. **Create a Twilio Account**
   - Sign up at [twilio.com](https://www.twilio.com)
   - Get your Account SID and Auth Token

2. **Enable WhatsApp Sandbox**
   - Go to Console → Messaging → Try it out → Send a WhatsApp message
   - Follow instructions to connect your WhatsApp number
   - Note the sandbox WhatsApp number (usually +1 415 523 8886)

3. **Configure Webhook**
   - In Twilio Console, go to Phone Numbers → Manage → WhatsApp sandbox settings
   - Set webhook URL to: `https://your-domain.com/webhook`
   - For local testing: Use ngrok to expose local port

## Usage

### Running Locally

1. **Start the application**
   ```bash
   python main.py
   ```

2. **Test the webhook (optional)**
   
   For local development, use ngrok to expose your webhook:
   ```bash
   # Install ngrok first
   ngrok http 5000
   ```
   
   Then update your Twilio webhook URL to the ngrok URL.

### WhatsApp Bot Commands

Send these commands to your WhatsApp bot:

- `attendance` - Get current attendance summary
- `marks` - Get latest marks and GPA
- `notices` - Get recent notices and announcements
- `help` - Show available commands

### Automatic Alerts

The bot will automatically send alerts for:

- **Low Attendance**: When attendance drops below configured threshold
- **New Marks**: When new marks or GPA updates are available
- **Important Notices**: When new announcements are posted

## File Structure

```
jiit-portal-monitor/
├── main.py                 # Main application entry point
├── jiit_checker.py         # Portal login and data fetching
├── notifier.py            # WhatsApp notifications and bot
├── session_manager.py     # Session management and login logic
├── captcha.py            # CAPTCHA handling (preserved from original)
├── simple_login.py       # Original login implementation
├── .env                  # Environment variables (create from template)
├── requirements.txt      # Python dependencies
├── README.md            # This file
└── jiit_monitor.log     # Application logs (created automatically)
```

## Key Components

### JIITChecker (`jiit_checker.py`)
- Handles portal login using preserved CAPTCHA logic
- Fetches attendance, marks, and notices data
- Manages session state and automatic re-login
- Provides formatted summaries for WhatsApp responses

### WhatsAppNotifier (`notifier.py`)
- Sends alerts via Twilio WhatsApp API
- Handles incoming WhatsApp messages (chatbot)
- Creates webhook endpoints for Twilio integration
- Formats messages for different types of notifications

### SessionManager (`session_manager.py`)
- Manages JIIT portal sessions
- Integrates with existing CAPTCHA solving logic
- Handles login, logout, and session validation
- Provides error handling for various failure scenarios

### CAPTCHA Handling (`captcha.py`)
- **PRESERVED WITHOUT MODIFICATIONS** as per requirements
- Contains the exact CAPTCHA solving logic from original implementation
- Should not be replaced with OCR or manual input methods

## Deployment

### Heroku Deployment

1. **Create Heroku app**
   ```bash
   heroku create your-app-name
   ```

2. **Set environment variables**
   ```bash
   heroku config:set JIIT_USERNAME=your_username
   heroku config:set JIIT_PASSWORD=your_password
   # ... set all other variables
   ```

3. **Deploy**
   ```bash
   git add .
   git commit -m "Initial deployment"
   git push heroku main
   ```

4. **Update Twilio webhook**
   - Set webhook URL to: `https://your-app-name.herokuapp.com/webhook`

### Railway Deployment

1. **Connect GitHub repository** to Railway
2. **Set environment variables** in Railway dashboard
3. **Deploy** automatically on push

### VPS Deployment

1. **Setup server**
   ```bash
   # Install Python, pip, and dependencies
   sudo apt update
   sudo apt install python3 python3-pip python3-venv
   
   # Clone repository
   git clone <your-repo>
   cd jiit-portal-monitor
   
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Configure service**
   
   Create systemd service file `/etc/systemd/system/jiit-monitor.service`:
   ```ini
   [Unit]
   Description=JIIT Portal Monitor
   After=network.target
   
   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/path/to/jiit-portal-monitor
   Environment=PATH=/path/to/jiit-portal-monitor/venv/bin
   ExecStart=/path/to/jiit-portal-monitor/venv/bin/python main.py
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   ```

3. **Start service**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable jiit-monitor
   sudo systemctl start jiit-monitor
   ```

4. **Setup reverse proxy** (nginx)
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location /webhook {
           proxy_pass http://localhost:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `JIIT_USERNAME` | Student ID/username | Required |
| `JIIT_PASSWORD` | Password | Required |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID | Required |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token | Required |
| `TWILIO_WHATSAPP_FROM` | Twilio WhatsApp number | Required |
| `WHATSAPP_TO` | Your WhatsApp number | Required |
| `ATTENDANCE_THRESHOLD` | Minimum attendance % | 75 |
| `CHECK_INTERVAL_MINUTES` | Check frequency | 60 |
| `WEBHOOK_PORT` | Server port | 5000 |
| `WEBHOOK_HOST` | Server host | 0.0.0.0 |
| `LOG_LEVEL` | Logging level | INFO |

## Monitoring and Logs

- **Application logs**: Written to `jiit_monitor.log`
- **Health check endpoint**: `GET /health`
- **Webhook endpoint**: `POST /webhook`

## Security Considerations

- **Environment Variables**: Never commit `.env` file to version control
- **Session Storage**: Sessions stored securely in memory, not on disk
- **HTTPS**: Use HTTPS for webhook endpoints in production
- **Credentials**: Use strong passwords and secure Twilio credentials

## Troubleshooting

### Common Issues

1. **Login Failures**
   - Check JIIT credentials in `.env`
   - Verify CAPTCHA logic is working
   - Check portal availability

2. **WhatsApp Not Working**
   - Verify Twilio credentials
   - Check webhook URL configuration
   - Ensure WhatsApp sandbox is properly setup

3. **Deployment Issues**
   - Check all environment variables are set
   - Verify port configuration
   - Check application logs

### Debug Mode

Enable detailed logging:
```bash
LOG_LEVEL=DEBUG python main.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes (do not modify `captcha.py`)
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review application logs
3. Create an issue in the repository

## Important Notes

- **CAPTCHA Logic**: The `captcha.py` file contains the original CAPTCHA handling logic and must not be modified
- **Session Management**: Sessions are kept in memory for security
- **Production Deployment**: Ensure proper SSL/TLS setup for webhook endpoints
- **Rate Limiting**: Be mindful of JIIT portal rate limits to avoid being blocked
