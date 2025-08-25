import os
import requests
import base64
import re
import json
from collections import defaultdict

# --- دیکشنری کامل‌تر برای نگاشت کدهای کشور به نام کامل ---
COUNTRY_MAP = {
    # اولویت با کدهای طولانی‌تر و خاص‌تر است
    "Germany": "Germany", "Deutschland": "Germany",
    "United States": "USA", "USA": "USA",
    "Netherlands": "Netherlands",
    "France": "France",
    "United Kingdom": "UK", "UK": "UK",
    "Canada": "Canada",
    "Japan": "Japan",
    "Singapore": "Singapore",
    "Finland": "Finland",
    "Iran": "Iran",
    "Turkey": "Turkey",
    "Russia": "Russia",
    "Austria": "Austria",
    "Poland": "Poland",
    "Sweden": "Sweden",
    "Switzerland": "Switzerland",
    "Italy": "Italy",
    "Spain": "Spain",
    "Estonia": "Estonia",
    "UAE": "UAE", "United Arab Emirates": "UAE",
    "Armenia": "Armenia",
    "Argentina": "Argentina",
    "Czechia": "Czechia", "Czech": "Czechia",
    "Dominican": "Dominican",
    "Korea": "Korea",
    # کدهای دو حرفی و ایموجی‌ها
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

def get_remark_from_config(config):
    """نام کانفیگ (remark/ps) را از انواع کانفیگ استخراج می‌کند."""
    remark = ''
    try:
        if '#' in config:
            remark += " " + config.split('#')[-1]
        
        if config.startswith('vmess://'):
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
        
        # توکن‌سازی دقیق‌تر نام کانفیگ
        tokens = set(re.split(r'[\s|\(\)\[\]\-_,]+', remark))
        
        found_country = False
        for code, name in COUNTRY_MAP.items():
            if code in tokens:
                by_country[name].append(config)
                found_country = True
                break
        if not found_country:
            by_country["Unknown"].append(config)
            
    # --- نوشتن فایل‌ها ---
    # پاک کردن فایل‌ها و پوشه‌های قدیمی برای جلوگیری از باقی ماندن فایل‌های حذف شده
    if os.path.exists('sub'):
        import shutil
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
            for config in list(dict.fromkeys(configs)): # حذف تکراری
                f.write(config + '\n')
    
    # نوشتن فایل‌های کشور
    for country, configs in by_country.items():
        with open(f'sub/country/{country}.txt', 'w', encoding='utf-8') as f:
            for config in list(dict.fromkeys(configs)): # حذف تکراری
                f.write(config + '\n')

    print("\n✅ Success! All configs have been sorted accurately and saved.")

if __name__ == "__main__":
    main()
