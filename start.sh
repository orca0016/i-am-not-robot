#!/usr/bin/env bash

echo "DEBUG ENV VARS:"
echo "TELEGRAM_TOKEN is: $TELEGRAM_TOKEN"
echo "OPENROUTER_KEY length: ${#OPENROUTER_KEY}"

echo "RUNNING BOT..."
python main.py
