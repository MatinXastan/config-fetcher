import os
import requests
import base64
import re
import json
import shutil
from collections import defaultdict

# --- دیکشنری کامل‌تر برای نگاشت کدهای کشور به نام کامل ---
# اولویت با کدهای طولانی‌تر و خاص‌تر است تا از تشخیص اشتباه جلوگیری شود
COUNTRY_MAP = {
    "Germany": "Germany", "Deutschland": "Germany", "DE": "Germany", "🇩🇪": "Germany",
    "United States": "USA", "USA": "USA", "US": "USA", "🇺🇸": "USA",
    "Netherlands": "Netherlands", "NL": "Netherlands", "🇳🇱": "Netherlands",
    "France": "France", "FR": "France", "🇫🇷": "France",
    "United Kingdom": "UK", "UK": "UK", "GB": "UK", "🇬🇧": "UK",
    "Canada": "Canada", "CA": "Canada", "🇨🇦": "Canada",
    "Japan": "Japan", "JP": "Japan", "🇯🇵": "Japan",
    "Singapore": "Singapore", "SG": "Singapore", "🇸🇬": "Singapore",
    "Finland": "Finland", "FI": "Finland", "🇫🇮": "Finland",
    "Iran": "Iran", "IR": "Iran", "🇮🇷": "Iran",
    "Turkey": "Turkey", "TR": "Turkey", "🇹🇷": "Turkey",
    "Russia": "Russia", "RU": "Russia", "🇷🇺": "Russia",
    "Austria": "Austria", "AT": "Austria", "🇦🇹": "Austria",
    "Poland": "Poland", "PL": "Poland", "🇵🇱": "Poland",
    "Sweden": "Sweden", "SE": "Sweden", "🇸🇪": "Sweden",
    "Switzerland": "Switzerland", "CH": "Switzerland", "🇨🇭": "Switzerland",
    "Italy": "Italy", "IT": "Italy", "🇮🇹": "Italy",
    "Spain": "Spain", "ES": "Spain", "🇪🇸": "Spain",
    "Estonia": "Estonia", "EE": "Estonia", "🇪🇪": "Estonia",
    "UAE": "UAE", "United Arab Emirates": "UAE", "AE": "UAE", "🇦🇪": "UAE",
    "Armenia": "Armenia", "AM": "Armenia", "🇦🇲": "Armenia",
    "Argentina": "Argentina", "AR": "Argentina", "🇦🇷": "Argentina",
    "Czechia": "Czechia", "Czech": "Czechia", "CZ": "Czechia", "🇨🇿": "Czechia",
    "Dominican": "Dominican", "DO": "Dominican", "🇩🇴": "Dominican",
    "Korea": "Korea", "KR": "Korea", "🇰🇷": "Korea",
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

def get_remark_from_config(config):
    """نام کانفیگ (remark/ps) را از انواع کانفیگ استخراج می‌کند."""
    remark = ''
    try:
        if '#' in config:
            # URL Decode simple parts of the remark
            from urllib.parse import unquote
            remark += " " + unquote(config.split('#')[-1])
        
        if config.startswith('vmess://'):
            # For vmess, decode the base64 part to get the 'ps' key
            decoded_part = base64.b64decode(config[8:]).decode('utf-8')
            vmess_data = json.loads(decoded_part)
            remark += " " + vmess_data.get('ps', '')
    except Exception:
        pass # Ignore errors in remark extraction
    return remark

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

        remark = get_remark_from_config(config)
        
        # توکن‌سازی دقیق‌تر نام کانفیگ برای جستجوی دقیق کلمات
        tokens = set(re.split(r'[\s|\(\)\[\]\-_,]+', remark.upper()))
        
        found_country = False
        # اولویت با کدهای طولانی‌تر است تا از تشخیص اشتباه جلوگیری شود
        for code in sorted(COUNTRY_MAP.keys(), key=len, reverse=True):
            if code.upper() in tokens:
                country_name = COUNTRY_MAP[code]
                by_country[country_name].append(config)
                found_country = True
                break
        if not found_country:
            by_country["Unknown"].append(config)
            
    # --- نوشتن فایل‌ها ---
    # پاک کردن فایل‌ها و پوشه‌های قدیمی برای شروع تمیز
    if os.path.exists('sub'):
        shutil.rmtree('sub')
        
    os.makedirs('sub/protocol', exist_ok=True)
    os.makedirs('sub/country', exist_ok=True)

    # نوشتن فایل کلی
    with open('v2ray_configs.txt', 'w', encoding='utf-8') as f:
        for config in unique_configs:
            f.write(config + '\n')
    
    # نوشتن فایل‌های پروتکل
    for proto, configs in by_protocol.items():
        with open(f'sub/protocol/{proto}.txt', 'w', encoding='utf-8') as f:
            for config in list(dict.fromkeys(configs)):
                f.write(config + '\n')
    
    # نوشتن فایل‌های کشور
    for country, configs in by_country.items():
        with open(f'sub/country/{country}.txt', 'w', encoding='utf-8') as f:
            for config in list(dict.fromkeys(configs)):
                f.write(config + '\n')

    print("\n✅ Success! All configs have been sorted accurately and saved.")

if __name__ == "__main__":
    main()
