import os
import requests
import base64
import re
import json
import shutil
from collections import defaultdict
from urllib.parse import unquote

# --- دیکشنری کامل‌تر برای نگاشت کدهای کشور به نام کامل ---
COUNTRY_ALIASES = {
    "Germany": ["Germany", "Deutschland", "DE", "🇩🇪"],
    "USA": ["United States", "USA", "US", "🇺🇸"],
    "Netherlands": ["Netherlands", "NL", "🇳🇱"],
    "France": ["France", "FR", "🇫🇷"],
    "UK": ["United Kingdom", "UK", "GB", "�🇧"],
    "Canada": ["Canada", "CA", "🇨🇦"],
    "Japan": ["Japan", "JP", "🇯🇵"],
    "Singapore": ["Singapore", "SG", "🇸🇬"],
    "Finland": ["Finland", "FI", "🇫🇮"],
    "Iran": ["Iran", "IR", "🇮🇷"],
    "Turkey": ["Turkey", "TR", "🇹🇷"],
    "Russia": ["Russia", "RU", "🇷🇺"],
    "Austria": ["Austria", "AT", "🇦🇹"],
    "Poland": ["Poland", "PL", "🇵🇱"],
    "Sweden": ["Sweden", "SE", "🇸🇪"],
    "Switzerland": ["Switzerland", "CH", "🇨🇭"],
    "Italy": ["Italy", "IT", "🇮🇹"],
    "Spain": ["Spain", "ES", "🇪🇸"],
    "Estonia": ["Estonia", "EE", "🇪🇪"],
    "UAE": ["UAE", "United Arab Emirates", "AE", "🇦🇪"],
    "Armenia": ["Armenia", "AM", "🇦🇲"],
    "Argentina": ["Argentina", "AR", "🇦🇷"],
    "Czechia": ["Czechia", "Czech", "CZ", "🇨🇿"],
    "Dominican": ["Dominican", "DO", "🇩🇴"],
    "Korea": ["Korea", "KR", "🇰🇷"],
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
            remark += " " + unquote(config.split('#')[-1])
        
        if config.startswith('vmess://'):
            b64_part = config[8:]
            b64_part += '=' * (-len(b64_part) % 4)
            decoded_part = base64.b64decode(b64_part).decode('utf-8')
            vmess_data = json.loads(decoded_part)
            remark += " " + vmess_data.get('ps', '')
    except Exception:
        pass
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

    # --- لیست کامل پروتکل‌های معتبر ---
    valid_protocols = ('vless://', 'vmess://', 'ss://', 'ssr://', 'trojan://', 'tuic://', 'hysteria://', 'hysteria2://')
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
        
        found_country_name = None
        # اولویت با کدهای طولانی‌تر است تا از تشخیص اشتباه جلوگیری شود
        for country_name, aliases in COUNTRY_ALIASES.items():
            for alias in sorted(aliases, key=len, reverse=True):
                # استفاده از regex برای پیدا کردن کد کشور به صورت یک کلمه جدا
                pattern = r'(?<![a-zA-Z0-9])' + re.escape(alias.upper()) + r'(?![a-zA-Z0-9])'
                if re.search(pattern, remark.upper()):
                    found_country_name = country_name
                    break
            if found_country_name:
                break
    
        if found_country_name:
            by_country[found_country_name].append(config)
        else:
            by_country["Unknown"].append(config)
            
    # --- نوشتن فایل‌ها ---
    # پاک کردن فایل‌ها و پوشه‌های قدیمی برای شروع تمیز
    if os.path.exists('sub'):
        shutil.rmtree('sub')
        
    os.makedirs('sub/protocol', exist_ok=True)
    os.makedirs('sub/country', exist_ok=True)

    with open('v2ray_configs.txt', 'w', encoding='utf-8') as f:
        for config in unique_configs:
            f.write(config + '\n')
    
    for proto, configs in by_protocol.items():
        with open(f'sub/protocol/{proto}.txt', 'w', encoding='utf-8') as f:
            for config in list(dict.fromkeys(configs)): # حذف تکراری
                f.write(config + '\n')
    
    for country, configs in by_country.items():
        if configs:
            with open(f'sub/country/{country}.txt', 'w', encoding='utf-8') as f:
                for config in list(dict.fromkeys(configs)): # حذف تکراری
                    f.write(config + '\n')

    print("\n✅ Success! All configs have been sorted accurately and saved.")

if __name__ == "__main__":
    main()
�
