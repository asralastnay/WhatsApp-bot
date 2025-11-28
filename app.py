import logging
import json
from flask import Flask, request

app = Flask(__name__)

# إجبار البايثون على الطباعة في اللوج فوراً
logging.basicConfig(level=logging.INFO)

@app.route("/webhook", methods=['POST'])
def webhook():
    # 1. استلام البيانات الخام وتحويلها لنص
    raw_data = request.get_data(as_text=True)
    
    # 2. طباعة فاصل واضح جداً عشان تشوفه بعينك
    print("\n" + "="*50)
    print("🔥 وصل شيء جديد من Green-API!")
    print(f"📄 المحتوى الكامل: {raw_data}")
    print("="*50 + "\n")

    # نرد بـ OK عشان Green-API ما يزعل
    return "OK", 200

if __name__ == "__main__":
    app.run(port=5000)
