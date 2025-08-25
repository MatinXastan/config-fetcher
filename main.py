import os
import requests
import base64
import re
import json
from collections import defaultdict

# --- دیکشنری کامل‌تر برای نگاشت کدهای کشور به نام کامل ---
COUNTRY_MAP = {
    "DE": "Germany", "🇩🇪": "Germany",
    "US": "USA", "🇺🇸": "USA",
    "NL": "Netherlands", "🇳🇱": "Netherlands",
    "FR": "France", "🇫🇷": "France",
    "GB": "UK", "🇬🇧": "UK", "UK": "UK",
    "CA": "Canada", "🇨🇦": "Canada",
    "JP": "Japan", "🇯🇵": "Japan",
    "SG": "Singapore", "🇸🇬": "Singapore",
    "FI": "Finland", "🇫🇮": "Finland",
    "IR": "Iran", "🇮🇷": "Iran",
    "TR": "Turkey", "🇹🇷": "Turkey",
    "RU": "Russia", "🇷🇺": "Russia",
    "AT": "Austria", "🇦🇹": "Austria",
    "PL": "Poland", "🇵🇱": "Poland",
    "SE": "Sweden", "🇸🇪": "Sweden",
    "CH": "Switzerland", "🇨🇭": "Switzerland",
    "IT": "Italy", "🇮🇹": "Italy",
    "ES": "Spain", "🇪🇸": "Spain",
    "EE": "Estonia", "🇪🇪": "Estonia",
    "AE": "UAE", "🇦🇪": "UAE",
    "AM": "Armenia", "🇦🇲": "Armenia",
    "AR": "Argentina", "🇦🇷": "Argentina",
    "CZ": "Czechia", "🇨🇿": "Czechia",
    "DO": "Dominican", "🇩🇴": "Dominican",
    "KR": "Korea", "🇰🇷": "Korea",
}

def fetch_and_decode_content(url):
    """محتوای یک URL را دریافت کرده و اگر با Base64 کد شده باشد، آن را دیکود می‌کند."""
    try:
        response = requests.get(url, timeout=15)
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

def get_remark_from_vmess(config):
    """نام کانفیگ (ps) را از داخل vmess استخراج می‌کند."""
    try:
        if config.startswith('vmess://'):
            decoded_part = base64.b64decode(config[8:]).decode('utf-8')
            vmess_data = json.loads(decoded_part)
            return vmess_data.get('ps', '')
    except Exception:
        return ''
    return ''

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

    valid_protocols = ('vless://', 'vmess://', 'ss://', 'trojan://', 'tuic://')
    initial_valid_configs = [c for c in all_configs if c and c.strip().startswith(valid_protocols)]
    unique_configs = list(dict.fromkeys(initial_valid_configs))
    
    print(f"\nFound {len(unique_configs)} unique configs. Now sorting...")

    by_protocol = defaultdict(list)
    by_country = defaultdict(list)

    for config in unique_configs:
        proto = config.split('://')[0]
        by_protocol[proto.upper()].append(config)

        # ترکیب نام بعد از # و نام داخل vmess برای جستجوی بهتر
        remark_part = ''
        if '#' in config:
            remark_part = config.split('#')[-1]
        
        if proto == 'vmess':
            remark_part += " " + get_remark_from_vmess(config)

        found_country = False
        for code, name in COUNTRY_MAP.items():
            # استفاده از regex برای پیدا کردن کد کشور به صورت یک کلمه جدا
            if re.search(rf'[^a-zA-Z0-9]{re.escape(code)}[^a-zA-Z0-9]|^{re.escape(code)}[^a-zA-Z0-9]|[^a-zA-Z0-9]{re.escape(code)}$', remark_part, re.IGNORECASE):
                by_country[name].append(config)
                found_country = True
                break
        if not found_country:
            by_country["Unknown"].append(config)
            
    # --- نوشتن فایل‌ها ---
    os.makedirs('sub/protocol', exist_ok=True)
    os.makedirs('sub/country', exist_ok=True)

    # نوشتن فایل کلی (با حذف نهایی تکراری)
    with open('v2ray_configs.txt', 'w', encoding='utf-8') as f:
        for config in list(dict.fromkeys(unique_configs)):
            f.write(config + '\n')
    
    # نوشتن فایل‌های پروتکل (با حذف نهایی تکراری)
    for proto, configs in by_protocol.items():
        with open(f'sub/protocol/{proto}.txt', 'w', encoding='utf-8') as f:
            for config in list(dict.fromkeys(configs)):
                f.write(config + '\n')
    
    # نوشتن فایل‌های کشور (با حذف نهایی تکراری)
    for country, configs in by_country.items():
        with open(f'sub/country/{country}.txt', 'w', encoding='utf-8') as f:
            for config in list(dict.fromkeys(configs)):
                f.write(config + '\n')

    print("\n✅ Success! All configs have been sorted accurately and saved.")

if __name__ == "__main__":
    main()
