=============================
PortalPlus - Technical Flow
=============================

Overview
========

The PortalPlus is a comprehensive Python application that provides automated monitoring of the JIIT (Jaypee Institute of Information Technology) Webportal. It monitors student attendance and delivers real-time notifications via Telegram bot, providing an interactive interface for on-demand queries.

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
       │
       ├─ Start Background Thread: periodic_check()
       │
       └─ Start Telegram Bot: telegram_notifier.start_bot()

**Error Handling Strategy**:

- Automatic portal connection retry with exponential backoff
- Separate error tracking for portal and notification services
- Graceful degradation when portal is unavailable

2. JIIT Checker (jiit_checker.py)
---------------------------------

**Purpose**: Handles all interactions with JIIT Webportal

**Key Capabilities**:

- **Authentication Management**: Login with automatic session renewal
- **Attendance Fetching**: Retrieves current attendance data
- **Change Detection**: Monitors attendance changes over time
- **Threshold Monitoring**: Tracks attendance against configurable thresholds

**Data Structures**:

.. code-block:: python

    # Attendance Data Structure
    {
        'attendance_percentage': float,
        'subjects': {
            'subject_name': {
                'percentage': float,
                'present': int,
                'total': int
            }
        }
    }
                'marks': str,
                'grade': str,
                'credits': int
            }
        ]
    }

**Change Detection Algorithm**:

1. Fetch current data from portal
2. Compare with last stored snapshot
3. Identify differences in:
   - Attendance percentages
   - New marks/grades
   - New notices
4. Store current data as new baseline
5. Return change summary

3. Session Manager (session_manager.py)
---------------------------------------

**Purpose**: Manages authentication and session persistence with JIIT portal

**Technologies Used**:
- **PyJIIT Library**: Third-party library for JIIT portal integration
- **Default CAPTCHA**: Uses pre-configured CAPTCHA solving mechanism

**Session Lifecycle**:

.. code-block::

    login_simple() → validate_credentials() → get_session_token()
        │
        ├─ Success: Store session headers and client ID
        │
        └─ Failure: Log error and return False

**Session Persistence**:

- Maintains session headers for API requests
- Tracks client ID for request validation
- Provides session validity checking
- Handles automatic logout and cleanup

4. WhatsApp Notifier (notifier.py)
----------------------------------

**Purpose**: Manages WhatsApp communication via Twilio API

3. Telegram Notifier (telegram_notifier.py)
-------------------------------------------

**Purpose**: Manages all Telegram bot interactions and notifications

**Key Capabilities**:

- **Bot Management**: Handles Telegram bot initialization and polling
- **Command Processing**: Processes user commands and queries
- **Message Formatting**: Formats attendance data with HTML markup
- **Interactive Interface**: Provides real-time portal data access

**Supported Commands**:

.. code-block::

    '/start' → Welcome message and setup
    '/help' → Available commands list  
    '/attendance' → Current attendance report
    '/interval [minutes]' → Set monitoring interval (5-1440 minutes)
    '/status' → Bot and portal connection status

**Message Features**:

1. **Attendance Reports**: Clean formatted attendance with bold subject names
2. **Interval Management**: User-configurable monitoring frequency
3. **Status Updates**: Real-time system health information
4. **Error Handling**: User-friendly error messages and guidance

**Message Formatting**:
- HTML parsing enabled for bold text formatting
- Clean subject-wise attendance display
- Minimal, focused information presentation

4. Session Manager (session_manager.py)
--------------------------------------

**Purpose**: Handles JIIT portal authentication and session management

**Key Functions**:
- Portal login with PyJIIT integration
- Session validation and renewal
- CAPTCHA handling with default solver
- Login state management

5. CAPTCHA Handler (captcha.py)
-------------------------------

**Purpose**: Provides CAPTCHA solving mechanism for portal login

**Implementation**:

- Uses default solving logic (ABC123)
- Integrates with PyJIIT library
- Provides fallback mechanism for CAPTCHA failures
- Logs solving attempts for debugging

Technical Workflow
==================

Application Startup Sequence
-----------------------------

.. code-block::

    1. Load Environment Variables
       ├─ JIIT credentials (username, password)
       ├─ Telegram configuration (bot token, chat ID)
       └─ Operational settings (intervals, thresholds)

    2. Initialize Logging System
       ├─ Console output (INFO level)
       └─ File logging (jiit_monitor.log)

    3. Initialize Services
       ├─ JIIT Checker with session manager
       ├─ Telegram Bot with command handlers
       └─ Background monitoring thread

    4. Start Operations
       ├─ Portal login attempt
       ├─ Telegram bot polling
       └─ Periodic attendance monitoring

Telegram Bot Interaction Flow
-----------------------------

**Command Processing**:

.. code-block::

    User sends command → Bot receives update → Parse command → Execute action → Send formatted response

**Supported Interaction Patterns**:

1. **Attendance Queries**:
   - User sends /attendance command
   - Bot fetches live data from portal
   - Formatted HTML response with bold subject names

2. **Interval Management**:
   - User sets monitoring frequency with /interval
   - Validation for 5-1440 minute range
   - Persistent configuration update

3. **Status Monitoring**:
   - Real-time portal connection status
   - Bot operational health reporting
   - System uptime information
       ├─ File logging (portalplus.log)
       └─ External library filtering

    3. Create Service Instances
       ├─ JIITChecker with credentials
       └─ WhatsAppNotifier with Twilio config

    4. Establish Portal Connection
       ├─ Attempt login to JIIT portal
       ├─ Send startup notification via WhatsApp
       └─ Handle connection failures gracefully

    5. Start Background Services
       ├─ Launch periodic monitoring thread
       └─ Start Flask webhook server

Periodic Monitoring Cycle
--------------------------

.. code-block::

    While application is running:
        │
        ├─ 1. Validate Session
        │    ├─ Check if logged in
        │    └─ Re-login if session expired
        │
        ├─ 2. Fetch Current Data
        │    ├─ Get attendance data
        │    ├─ Get marks/grades
        │    └─ Get recent notices
        │
        ├─ 3. Detect Changes
        │    ├─ Compare with previous data
        │    ├─ Check attendance threshold
        │    └─ Identify new content
        │
        ├─ 4. Send Notifications
        │    ├─ Attendance alerts (if below threshold)
        │    ├─ Marks updates (if new grades)
        │    └─ Notice alerts (if new notices)
        │
        ├─ 5. Update Baseline
        │    └─ Store current data for next comparison
        │
        └─ 6. Wait for Next Interval
             └─ Sleep for configured duration (default: 60 minutes)

WhatsApp Interaction Flow
-------------------------

**Incoming Message Processing**:

.. code-block::

    Webhook receives message → Parse command → Execute action → Send response

**Supported Interaction Patterns**:

1. **Command Execution**:
   - User sends command (e.g., "attendance")
   - Bot fetches live data from portal
   - Formatted response sent back

2. **Status Queries**:
   - Real-time portal data retrieval
   - Current session validation
   - System health reporting

3. **Help System**:
   - Command discovery
   - Usage instructions
   - Feature explanations

Error Handling and Recovery
===========================

Error Handling and Recovery
===========================

Portal Connection Failures
---------------------------

.. code-block::

    Connection Attempt → Failure Detected → Log Error → Continue Monitoring
        │
        ├─ Network Issues: Automatic retry on next cycle
        │
        └─ Authentication Failures: Session renewal attempt

Telegram Service Failures
--------------------------

- Automatic retry for transient network issues
- Graceful degradation if Telegram API unavailable
- Connection pooling for reliable message delivery

Session Management Failures
----------------------------

- Automatic re-login on session expiry
- CAPTCHA failure handling with retry logic
- Session state validation before portal requests

Deployment and Infrastructure
=============================

Deployment Requirements
-----------------------

.. code-block::

    Production Environment:
    ├─ Python 3.11+ Runtime
    ├─ Stable internet connection
    ├─ Process Manager (PM2/Supervisor) - optional
    ├─ Environment variable management (.env file)
    └─ Telegram Bot Token and Chat ID configuration

**Resource Requirements**:
- **CPU**: Minimal (single-threaded polling)
- **RAM**: 256MB (lightweight bot application)
- **Storage**: 500MB (dependencies and logs)
- **Network**: Stable internet for Telegram API and JIIT portal

**Scalability Considerations**:
- Single-instance design (per student)
- Stateless bot architecture
- Easy horizontal scaling for multiple students

Configuration Management
========================

Environment Variables
----------------------

.. code-block:: bash

    # JIIT Portal Credentials
    JIIT_USERNAME=your_enrollment_number
    JIIT_PASSWORD=your_portal_password

    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN=your_bot_token
    TELEGRAM_CHAT_ID=your_chat_id

    # Monitoring Configuration
    CHECK_INTERVAL_MINUTES=60
    ATTENDANCE_THRESHOLD=75

    # Logging Configuration
    LOG_LEVEL=INFO
- Credential validation and error reporting

Data Consistency and Storage
============================

In-Memory Data Management
-------------------------

**Storage Strategy**:
- Current data stored in JIITChecker instance variables
- Previous data maintained for change detection
- No persistent storage (fresh start on restart)

**Data Synchronization**:
- Thread-safe access to shared data structures
- Atomic updates during periodic checks
- Consistent state management across threads

**Performance Optimization**:
- Minimal memory footprint
- Efficient data comparison algorithms
- Optimized message formatting

Security Considerations
=======================

Credential Management
---------------------

- Environment variables for sensitive data
- No hardcoded credentials in source code
- Secure transmission over HTTPS/TLS

API Security
------------

- Twilio webhook validation
- Session token management
- Request rate limiting considerations

Error Information Exposure
--------------------------

- Sanitized error messages in user notifications
- Detailed logging for debugging (local only)
- No sensitive data in external communications

Deployment Architecture
=======================

Recommended Infrastructure
--------------------------

.. code-block::

    Production Environment:
    ├─ Cloud Server (VPS/EC2/DigitalOcean)
    ├─ Python 3.8+ Runtime
    ├─ Process Manager (PM2/Supervisor)
    ├─ Reverse Proxy (Nginx) for webhook endpoint
    ├─ SSL Certificate for HTTPS
    └─ Environment Variable Management

**Resource Requirements**:
- **CPU**: 1 vCPU (minimal computational load)
- **RAM**: 512MB (lightweight Python application)
- **Storage**: 1GB (logs and dependencies)
- **Network**: Stable internet for API calls

**Scalability Considerations**:
- Single-instance design (per student)
- Horizontal scaling for multiple students
- Stateless architecture for easy replication

Configuration Management
========================

Environment Variables
----------------------

.. code-block:: bash

    # JIIT Portal Credentials
    JIIT_USERNAME=your_enrollment_number
    JIIT_PASSWORD=your_portal_password

    # Twilio WhatsApp Configuration
    TWILIO_ACCOUNT_SID=your_twilio_sid
    TWILIO_AUTH_TOKEN=your_twilio_token
    TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
    WHATSAPP_TO=whatsapp:+91your_number

    # Monitoring Configuration
    CHECK_INTERVAL_MINUTES=60
    ATTENDANCE_THRESHOLD=75.0

    # Server Configuration
    WEBHOOK_HOST=0.0.0.0
    WEBHOOK_PORT=5000
    LOG_LEVEL=INFO

Customization Options
---------------------

**Monitoring Intervals**:
- Adjustable check frequency (minutes)
- Different intervals for different data types
- Peak/off-peak scheduling

**Notification Thresholds**:
- Attendance percentage thresholds
- Grade change sensitivity
- Notice filtering criteria

**Message Formatting**:
- Subject name abbreviations
- Custom message templates
- Localization support

Performance Metrics
===================

System Performance
------------------

**Response Times**:
- Portal login: 2-5 seconds
- Data fetching: 3-8 seconds per category
- WhatsApp message delivery: 1-3 seconds

**Resource Usage**:
- Memory footprint: 50-100MB
- CPU usage: <5% during active operations
- Network bandwidth: <1MB per monitoring cycle

**Availability Metrics**:
- Uptime target: 99.5%
- Maximum downtime per failure: 5 minutes
- Recovery time objective: <2 minutes

Monitoring and Observability
=============================

Logging Strategy
----------------

**Log Levels**:

.. code-block::

    DEBUG: Detailed execution flow
    INFO:  Normal operations and status
    WARN:  Recoverable errors and retries
    ERROR: Serious issues requiring attention

**Log Management**:

.. code-block::

    DEBUG: Detailed execution flow
    INFO:  Normal operations and status  
    WARN:  Recoverable errors and retries
    ERROR: Serious issues requiring attention

**Log Destinations**:
- Console output for real-time monitoring
- File logging (jiit_monitor.log) for historical analysis
- Structured format for operational insights

**Key Metrics Tracked**:
- Portal login success/failure rates
- Attendance data fetch response times
- Telegram bot message delivery rates
- Error frequency and types

Health Monitoring
-----------------

**System Health Indicators**:
- Portal connection status
- Telegram bot availability
- Background monitoring thread health
- Memory and process status

**Monitoring Commands**:
- /status command for real-time health check
- Log analysis for operational issues
- Telegram notifications for critical issues

Future Enhancement Opportunities
================================

Potential Improvements
----------------------

1. **Enhanced Features**:
   - Multi-student support
   - Attendance prediction and trends
   - Grade monitoring integration
   - Notice monitoring capabilities

2. **Advanced Analytics**:
   - Historical attendance tracking
   - Performance trend analysis
   - Automated alerts and reminders

3. **Platform Extensions**:
   - Discord bot integration
   - Web dashboard interface
   - Mobile app development

4. **Enhanced Security**:
   - Encrypted credential storage
   - Rate limiting for bot commands
   - User authentication and authorization

Technical Debt and Limitations
==============================

Current Limitations
-------------------

1. **Single User Design**: Supports one student per bot instance
2. **Memory-Only Storage**: No persistent data across restarts
3. **Basic Monitoring**: Limited to attendance data only
4. **Static Configuration**: Requires restart for some configuration changes

Known Technical Debt
--------------------

1. **Hardcoded Subject Mappings**: Should be externalized to configuration
2. **Limited Error Recovery**: Could benefit from more sophisticated retry strategies
3. **Basic Logging**: Could benefit from structured logging with metrics
4. **Manual Bot Setup**: Requires manual Telegram bot creation and configuration

Conclusion
==========

The PortalPlus Telegram bot represents a streamlined, efficient solution for automated attendance monitoring. Its simplified architecture focuses on core functionality while maintaining reliability and ease of use.

The current implementation provides:
- Real-time attendance monitoring via Telegram
- User-friendly command interface
- Configurable monitoring intervals
- Robust error handling and recovery
- Clean, formatted attendance reports

The bot's design prioritizes simplicity, reliability, and user experience, making it an effective tool for students to stay informed about their attendance status through a familiar messaging platform. Its modular architecture allows for easy maintenance and future enhancements.