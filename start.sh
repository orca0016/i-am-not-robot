echo "DEBUG ENV VARS:"
echo "TELEGRAM_TOKEN is: $TELEGRAM_TOKEN"
echo "HF_TOKEN length: ${#OPENROUTER_KEY }"

echo "RUNNING BOT..."
python main.py
