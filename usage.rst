=============================
PortalPlus - Technical Flow
=============================

Overview
========

The PortalPlus is a comprehensive Python application that provides automated monitoring of the JIIT (Jaypee Institute of Information Technology) Webportal. It monitors student attendance and delivers real-time notifications via Telegram bot, providing an interactive interface for instant attendance queries and marks viewing.

Architecture Overview
====================

The application follows a modular architecture with the following core components:

.. code-block::

    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │   Main Module   │    │  JIIT Checker   │    │ Session Manager │
    │   (main.py)     │◄──►│ (jiit_checker.py)│◄──►│(session_manager.py)│
    └─────────────────┘    └─────────────────┘    └─────────────────┘
             │                        │                       │
             │                        │                       │
             ▼                        ▼                       ▼
    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │   Telegram      │    │  Data Storage   │    │   CAPTCHA       │
    │   Notifier      │    │  (In-Memory)    │    │   Handler       │
    │(telegram_notifier.py)│                 │    │  (captcha.py)   │
    └─────────────────┘    └─────────────────┘    └─────────────────┘

Core Components
===============

1. Main Module (main.py)
------------------------

**Purpose**: Central orchestrator managing all services and background monitoring

**Key Functions**:

- **Environment Setup**: Loads and validates environment variables
- **Service Initialization**: Initializes JIIT checker and Telegram notifier
- **Background Monitoring**: Runs periodic attendance checks
- **Signal Handling**: Graceful shutdown on SIGINT/SIGTERM
- **Error Recovery**: Automatic retry logic for portal connections

**Technical Flow**:

.. code-block::

    main() → setup_logging() → load_environment() → initialize_services()

2. JIIT Checker (jiit_checker.py)
---------------------------------

**Purpose**: Core business logic for JIIT portal interaction and data processing

**Key Functions**:

- **Portal Authentication**: Handles login with CAPTCHA solving
- **Attendance Monitoring**: Fetches and processes attendance data
- **Marks Retrieval**: Extracts marks from API and PDF sources
- **Data Caching**: Implements intelligent caching for performance
- **Error Handling**: Robust error recovery and retry mechanisms

**Data Processing Flow**:

.. code-block::

    Login → Fetch Attendance → Process Subjects → Calculate Percentages → Cache Data

3. Session Manager (session_manager.py)
---------------------------------------

**Purpose**: Manages JIIT portal sessions and authentication state

**Key Functions**:

- **Session Lifecycle**: Creates and maintains portal sessions
- **CAPTCHA Handling**: Automated CAPTCHA solving for login
- **Connection Management**: Handles session timeouts and reconnections
- **Security**: Secure credential management and session cleanup

4. Telegram Notifier (telegram_notifier.py)
-------------------------------------------

**Purpose**: Telegram bot interface for user interaction and notifications

**Key Functions**:

- **Command Processing**: Handles user commands (/attendance, /marks, /interval)
- **Message Formatting**: Creates formatted HTML messages for Telegram
- **Real-time Notifications**: Sends alerts for attendance changes
- **Interactive Interface**: Provides inline keyboards for semester selection
- **Background Processing**: Runs bot polling in separate thread

**Command Flow**:

.. code-block::

    User Command → Parse Command → Fetch Data → Format Response → Send Message

5. CAPTCHA Handler (captcha.py)
-------------------------------

**Purpose**: Automated CAPTCHA solving for JIIT portal authentication

**Key Functions**:

- **Image Processing**: Downloads and processes CAPTCHA images
- **OCR Recognition**: Extracts text from CAPTCHA images
- **Fallback Handling**: Manual CAPTCHA input when OCR fails
- **Error Recovery**: Handles CAPTCHA solving failures gracefully

Data Flow Architecture
======================

1. **Initialization Phase**
   - Load environment variables
   - Initialize services and dependencies
   - Start background monitoring thread
   - Launch Telegram bot

2. **Authentication Phase**
   - Attempt automated login with CAPTCHA solving
   - Handle authentication failures and retries
   - Establish persistent session

3. **Monitoring Phase**
   - Periodic attendance data fetching
   - Compare with previous data for changes
   - Trigger notifications on threshold breaches
   - Update cached data

4. **Interaction Phase**
   - Process Telegram commands
   - Fetch requested data (attendance/marks)
   - Format and send responses
   - Handle user callbacks and selections

5. **Data Processing Phase**
   - Parse raw portal data
   - Extract relevant information
   - Calculate statistics and summaries
   - Format for user presentation

Key Features
============

**Automated Monitoring**
- Configurable monitoring intervals (5-1440 minutes)
- Real-time attendance tracking
- Automatic notifications for low attendance
- Background processing without user intervention

**Intelligent Data Processing**
- PDF marks extraction with OCR
- Subject-wise attendance breakdown
- T1 marks display (simplified format)
- GPA and CGPA tracking

**Robust Error Handling**
- Automatic retry on connection failures
- CAPTCHA solving with fallback options
- Graceful degradation on data unavailability
- Comprehensive logging for debugging

**User-Friendly Interface**
- Simple Telegram commands
- Formatted HTML messages
- Interactive semester selection
- Clear error messages and guidance

**Performance Optimizations**
- Intelligent caching system
- Background processing threads
- Efficient data structures
- Minimal resource usage

Configuration
=============

**Environment Variables**
- ``JIIT_USERNAME``: Student enrollment number
- ``JIIT_PASSWORD``: Portal password
- ``TELEGRAM_BOT_TOKEN``: Bot token from @BotFather
- ``TELEGRAM_CHAT_ID``: Target chat ID for notifications

**Optional Settings**
- Monitoring interval (default: 1440 minutes)
- Attendance threshold (default: 75%)
- Cache timeout settings

Deployment
==========

**Local Development**
1. Clone repository
2. Install dependencies: ``pip install -r requirements.txt``
3. Configure environment variables
4. Run: ``python src/main.py``

**Production Deployment**
- Use Docker for containerized deployment
- Configure environment variables securely
- Set up monitoring and logging
- Enable automatic restarts

**Cloud Platforms**
- Compatible with Heroku, Railway, Render
- Supports persistent background processes
- Environment variable configuration
- Automatic scaling capabilities

Troubleshooting
===============

**Common Issues**
- **Login Failures**: Check credentials and CAPTCHA solving
- **Connection Timeouts**: Verify network connectivity
- **Data Not Available**: Check portal data upload status
- **Telegram Errors**: Validate bot token and chat ID

**Debug Mode**
- Enable detailed logging
- Check portal connectivity
- Verify data parsing
- Test individual components

**Performance Tuning**
- Adjust monitoring intervals
- Configure cache settings
- Optimize background processes
- Monitor resource usage

API Integration
===============

**JIIT Portal Integration**
- Uses pyjiit library for portal access
- Handles session management automatically
- Supports multiple authentication methods
- Robust error handling for API changes

**Telegram Bot API**
- Asynchronous message handling
- HTML formatting support
- Inline keyboard interactions
- Background polling mechanism

**PDF Processing**
- pdfplumber for text extraction
- OCR fallback for image-based PDFs
- Structured data parsing
- Error recovery for malformed documents

Security Considerations
=======================

**Credential Management**
- Environment variable storage
- No hardcoded credentials
- Secure session handling
- Automatic cleanup on exit

**Data Protection**
- In-memory data storage
- No persistent sensitive data
- Secure communication channels
- Minimal data retention

**Access Control**
- Single-user bot design
- Chat ID validation
- Command authorization
- Rate limiting capabilities

Future Enhancements
===================

**Planned Features**
- Multi-user support
- Advanced analytics dashboard
- Custom notification rules
- Integration with other platforms
- Mobile app companion

**Technical Improvements**
- Database integration for persistence
- Advanced caching strategies
- Machine learning for CAPTCHA solving
- API rate limiting and optimization
- Enhanced error reporting

**User Experience**
- Web dashboard interface
- Customizable themes
- Advanced filtering options
- Export capabilities
- Historical data analysis</content>
<parameter name="filePath">d:\Development\Python\Portal-Plus\usage.rst