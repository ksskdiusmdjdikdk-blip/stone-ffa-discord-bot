"""Pytest fixtures – ensure a dummy token exists so bot.config can import."""

import os

# Must be set before any bot.* import that pulls config
os.environ.setdefault("DISCORD_TOKEN", "test_token_for_unit_tests_only")
