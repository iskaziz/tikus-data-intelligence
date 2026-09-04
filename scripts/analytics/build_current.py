#!/usr/bin/env python3
"""Compatibility wrapper: rebuild all browser products from history."""
from pathlib import Path
from scripts.analytics.build_products import build_all_products

if __name__ == "__main__":
    build_all_products(Path(__file__).resolve().parents[2])
