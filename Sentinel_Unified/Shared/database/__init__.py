"""
Sentinel Database Package
==========================
Shared database connection management for all Python microservices.

Author: Sentinel System
"""

from .mongo_manager import MongoManager

__all__ = ['MongoManager']
