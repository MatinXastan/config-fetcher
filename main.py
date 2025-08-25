import os
import requests
import base64
import re
from collections import defaultdict

# --- دیکشنری برای نگاشت کدهای کشور به نام کامل ---
# این لیست را می‌توانید در آینده کامل‌تر کنید
COUNTRY_MAP = {
    "DE": "Germany", "🇩🇪": "Germany",
    "US": "USA", "🇺🇸": "USA",
    "NL": "Netherlands", "🇳🇱": "Netherlands",
    "FR": "France", "🇫🇷": "France",
    "GB": "UK", "🇬🇧": "UK",
    "CA": "Canada", "🇨🇦": "Canada",
    "JP": "Japan", "🇯🇵": "Japan",
    "SG": "Singapore", "🇸🇬": "Singapore",
    "FI": "Finland", "🇫🇮": "Finland",
    "IR": "Iran", "🇮🇷": "Iran",
    "TR": "Turkey", "🇹🇷": "Turkey",
    "RU": "Russia", "🇷🇺": "Russia",
    # ... می‌توانید کشورهای بیشتری اضافه کنید
}

def fetch_and_decode_content(url):
    """محتوای یک URL را دریافت کرده و اگر با Base64 کد شده باشد، آن را دیکود می‌کند."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        content = response.text
        try:
            decoded_content = base64.b64decode(content.strip()).decode('utf-8')
            return decoded_content.strip().split('\n')
        except Exception:
            return content.strip().split('\n')
    except requests.exceptions.RequestException as e:
        print(f"Error fetching from {url}: {e}")
        return []

def main():
    """تابع اصلی برنامه که تمام مراحل را مدیریت می‌کند."""
    urls_str = os.environ.get('CONFIG_URLS')
    if not urls_str:
        print("CONFIG_URLS secret not found or is empty.")
        return

    urls = urls_str.strip().split('\n')
    all_configs = []

    print(f"Processing {len(urls)} URLs...")
    for url in urls:
        if url.strip():
            print(f"Fetching from: {url.strip()}")
            configs = fetch_and_decode_content(url.strip())
            if configs:
                all_configs.extend(configs)

    # فیلتر کردن کانفیگ‌های معتبر و حذف تکراری‌ها
    valid_protocols = ('vless://', 'vmess://', 'ss://', 'trojan://', 'tuic://')
    initial_valid_configs = [c for c in all_configs if c and c.strip().startswith(valid_protocols)]
    unique_configs = list(dict.fromkeys(initial_valid_configs))
    
    print(f"\nFound {len(unique_configs)} unique configs. Now sorting...")

    # --- بخش دسته‌بندی ---
    by_protocol = defaultdict(list)
    by_country = defaultdict(list)

    for config in unique_configs:
        # ۱. دسته‌بندی بر اساس پروتکل
        proto = config.split('://')[0]
        by_protocol[proto.upper()].append(config)

        # ۲. دسته‌بندی بر اساس کشور
        remark = config.split('#')[-1] # بخش بعد از #
        found_country = False
        for code, name in COUNTRY_MAP.items():
            if code in remark:
                by_country[name].append(config)
                found_country = True
                break # با پیدا کردن اولین کشور، از حلقه خارج شو
        if not found_country:
            by_country["Unknown"].append(config)
            
    # --- بخش نوشتن فایل‌ها ---
    # نوشتن فایل کلی
    with open('v2ray_configs.txt', 'w', encoding='utf-8') as f:
        for config in unique_configs:
            f.write(config + '\n')
    
    # ایجاد پوشه‌ها
    os.makedirs('sub/protocol', exist_ok=True)
    os.makedirs('sub/country', exist_ok=True)

    # نوشتن فایل‌های پروتکل
    for proto, configs in by_protocol.items():
        with open(f'sub/protocol/{proto}.txt', 'w', encoding='utf-8') as f:
            for config in configs:
                f.write(config + '\n')
    
    # نوشتن فایل‌های کشور
    for country, configs in by_country.items():
        with open(f'sub/country/{country}.txt', 'w', encoding='utf-8') as f:
            for config in configs:
                f.write(config + '\n')

    print("\n✅ Success! All configs have been sorted and saved.")

if __name__ == "__main__":
    main()
