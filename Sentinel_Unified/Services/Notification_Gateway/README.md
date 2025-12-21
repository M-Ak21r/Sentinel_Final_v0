# Notification Gateway Microservice

## Overview

The Notification Gateway microservice ingests critical security events from MQTT and dispatches SMS alerts via Twilio.

## Purpose

This service acts as a stateless consumer of the MQTT event bus, listening for critical security events and forwarding them as SMS notifications to designated recipients.

## Features

- MQTT event bus consumer
- SMS alert dispatching via Twilio
- Stateless architecture for reliability and scalability

## Configuration

See the root `.env.example` file for required environment variables:
- `SMS_PROVIDER_SID` - Twilio Account SID
- `SMS_PROVIDER_TOKEN` - Twilio Auth Token
- `SMS_FROM_NUMBER` - Twilio phone number for sending SMS
- `ALERT_TARGET_PHONE` - Recipient phone number for alerts
- `NOTIFICATION_GATEWAY_PORT` - Service port (default: 5005)

## Installation

Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

```bash
cd Sentinel_Unified/Services/Notification_Gateway
python main.py
```

## Dependencies

- `paho-mqtt` - MQTT client for event bus integration
- `python-dotenv` - Environment configuration
- `requests` - HTTP client for API calls (Phase 2)
