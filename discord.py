import requests
import json
import re

# 傳送 POST 請求到您的 Webhook
payload = {"direction": "Position"}
response = requests.post("http://54.165.204.25:80/webhook", json=payload)
response_data = response.json()

# 分解得到的回應
trades = response_data.get("message", "").split(" | ")

# 建構 Discord Embed
embeds = []

pattern = re.compile(r'交易對:(.*?)交易編號:(.*?)倉位方向:(.*)')

for trade in trades:
    match = pattern.search(trade)
    if match:
        pair = match.group(1).strip()
        trade_id = match.group(2).strip()
        direction = match.group(3).strip()

        embeds.append({
            "title": f"交易對: {pair}",
            "description": f"交易編號: {trade_id}\n倉位方向: {direction}",
            "color": 0x39FF14,  # Neon Green
            "author": {
                "name": "Hana",
                "icon_url": "https://m.media-amazon.com/images/I/71cu980UfuL.jpg"
            }
        })


# 發送到 Discord Webhook
WEBHOOK_URL = "https://discord.com/api/webhooks/1163857162204872724/RuNwLVZQ0jE5q7NHUk4DZ_1d7auShXiYVJaYRUBACSwkKuvxvUtDDEU_PiA63l3nLU_Q"
data = {"embeds": embeds}
discord_response = requests.post(WEBHOOK_URL, json=data)

if discord_response.status_code == 204:
    print("成功發送到 Discord.")
else:
    print(f"發送失敗: {discord_response.status_code}")
