"""
Django demo/seed settings.

Used only to initialize demo data before switching to production.
"""

from config.settings.production import *  # noqa: F401,F403

DEBUG = True
DEMO_MODE = True
