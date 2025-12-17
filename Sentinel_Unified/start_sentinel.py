#!/usr/bin/env python3
"""
Sentinel Unified - Service Orchestrator
========================================
This script starts and manages all Sentinel microservices.

Usage:
    python start_sentinel.py [--service SERVICE_NAME]
    
Options:
    --service    Start a specific service only (door_sentry, interior_watch, web)
    --all        Start all services (default)
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def load_env():
    """Load environment variables from .env file."""
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            print("✅ Environment variables loaded")
        else:
            print("⚠️  .env file not found, using defaults")
    except ImportError:
        print("⚠️  python-dotenv not installed, skipping .env loading")


def start_service(service_name: str):
    """Start a specific Sentinel service."""
    services = {
        "door_sentry": "Services/Door_Sentry",
        "interior_watch": "Services/Interior_Watch",
        "web": "Web_Interface",
    }
    
    if service_name not in services:
        print(f"❌ Unknown service: {service_name}")
        print(f"Available services: {', '.join(services.keys())}")
        return False
    
    service_path = Path(__file__).parent / services[service_name]
    
    if not service_path.exists():
        print(f"❌ Service directory not found: {service_path}")
        return False
    
    print(f"🚀 Starting {service_name}...")
    # TODO: Implement actual service startup logic
    print(f"   Service path: {service_path}")
    print(f"   (Implementation pending)")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Sentinel Unified Service Orchestrator")
    parser.add_argument(
        "--service",
        choices=["door_sentry", "interior_watch", "web", "all"],
        default="all",
        help="Service to start (default: all)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🛡️  SENTINEL UNIFIED - Service Orchestrator")
    print("=" * 60)
    
    load_env()
    
    if args.service == "all":
        print("\n🚀 Starting all services...")
        start_service("door_sentry")
        start_service("interior_watch")
        start_service("web")
    else:
        start_service(args.service)
    
    print("\n" + "=" * 60)
    print("✅ Orchestrator setup complete")
    print("⚠️  Note: Service startup logic needs to be implemented")
    print("=" * 60)


if __name__ == "__main__":
    main()
