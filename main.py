import os
import requests
import base64
import re
import json
import shutil
from collections import defaultdict
from urllib.parse import unquote, urlparse, parse_qs

# --- دیکشنری کامل‌تر برای نگاشت کدهای کشور به نام کامل ---
COUNTRY_ALIASES = {
    "Germany": ["Germany", "Deutschland", "DE", "🇩🇪"],
    "USA": ["United States", "USA", "US", "🇺🇸"],
    "Netherlands": ["Netherlands", "NL", "🇳🇱"],
    "France": ["France", "FR", "🇫🇷"],
    "UK": ["United Kingdom", "UK", "GB", "🇬🇧"],
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
        response = requests.get(url, timeout=20)
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
            remark += " " + unquote(config.split('#', 1)[-1])
        
        if config.startswith('vmess://'):
            b64_part = config[8:]
            b64_part += '=' * (-len(b64_part) % 4)
            decoded_part = base64.b64decode(b64_part).decode('utf-8')
            vmess_data = json.loads(decoded_part)
            remark += " " + vmess_data.get('ps', '')
    except Exception:
        pass
    return remark.strip()

def find_country(remark):
    """کشور را بر اساس اولویت (ایموجی > کد > نام) در متن پیدا می‌کند."""
    for country_name, aliases in COUNTRY_ALIASES.items():
        for alias in aliases:
            # اولویت با ایموجی‌ها
            if not alias.isalpha() and len(alias) > 1:
                if alias in remark:
                    return country_name
    
    # جستجو برای کدهای دو حرفی
    tokens = set(re.split(r'[\s|\(\)\[\]\-_,]+', remark.upper()))
    for country_name, aliases in COUNTRY_ALIASES.items():
        for alias in aliases:
            if len(alias) == 2 and alias.isalpha() and alias.upper() in tokens:
                return country_name

    # جستجو برای نام کامل کشور
    for country_name, aliases in COUNTRY_ALIASES.items():
        for alias in aliases:
            if len(alias) > 2 and alias.isalpha():
                pattern = r'(?<![a-zA-Z0-9])' + re.escape(alias) + r'(?![a-zA-Z0-9])'
                if re.search(pattern, remark, re.IGNORECASE):
                    return country_name
    return None

def get_config_identifier(config):
    """یک شناسه منحصر به فرد (اثر انگشت) برای هر کانفیگ بر اساس اطلاعات اصلی سرور ایجاد می‌کند."""
    try:
        if config.startswith('vmess://'):
            b64_part = config.split('://')[1]
            if '#' in b64_part:
                b64_part = b64_part.split('#')[0]
            
            b64_part += '=' * (-len(b64_part) % 4)
            decoded_part = base64.b64decode(b64_part).decode('utf-8')
            vmess_data = json.loads(decoded_part)
            # شناسه بر اساس اطلاعات اصلی سرور ساخته می‌شود و 'ps' (نام) نادیده گرفته می‌شود
            identifier_tuple = (
                vmess_data.get('add', ''),
                str(vmess_data.get('port', '')),
                vmess_data.get('id', ''),
                vmess_data.get('net', ''),
                vmess_data.get('type', ''),
                vmess_data.get('path', ''),
                vmess_data.get('host', '')
            )
            return f"vmess://{str(identifier_tuple)}"

        # --- منطق جدید و هوشمند برای کانفیگ‌های مبتنی بر URL ---
        config_no_fragment = config.split('#', 1)[0]
        parsed_url = urlparse(config_no_fragment)
        
        protocol = parsed_url.scheme
        hostname = parsed_url.hostname
        port = parsed_url.port
        path = parsed_url.path

        # پارامترهای کوئری را مرتب می‌کنیم تا ترتیب آن‌ها در شناسه تأثیری نداشته باشد
        query_params = parse_qs(parsed_url.query)
        sorted_params = []
        for key in sorted(query_params.keys()):
            sorted_values = sorted(query_params[key])
            sorted_params.append(f"{key}={'&'.join(sorted_values)}")
        
        # شناسه را از اجزای اصلی سرور می‌سازیم
        identifier_parts = [
            protocol,
            f"{hostname}:{port}",
            path,
        ] + sorted_params

        return "||".join(filter(None, identifier_parts))

    except Exception:
        # در صورت بروز هرگونه خطا در پارس کردن، از روش ساده‌تر قبلی استفاده می‌شود
        return config.split('#', 1)[0]

def remove_duplicates(configs):
    """کانفیگ‌های تکراری را با استفاده از شناسه منحصر به فرد حذف می‌کند."""
    seen_identifiers = set()
    unique_list = []
    for config in configs:
        identifier = get_config_identifier(config)
        if identifier not in seen_identifiers:
            seen_identifiers.add(identifier)
            unique_list.append(config)
    return unique_list

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

    valid_protocols = ('vless://', 'vmess://', 'ss://', 'ssr://', 'trojan://', 'tuic://', 'hysteria://', 'hysteria2://')
    initial_valid_configs = [c.strip() for c in all_configs if c and c.strip().startswith(valid_protocols)]
    
    unique_configs = remove_duplicates(initial_valid_configs)
    
    print(f"\nFound {len(unique_configs)} unique configs. Now sorting...")

    by_protocol = defaultdict(list)
    by_country = defaultdict(list)

    for config in unique_configs:
        proto = config.split('://')[0]
        by_protocol[proto.upper()].append(config)

        remark = get_remark_from_config(config)
        country = find_country(remark)
        
        if country:
            by_country[country].append(config)
        else:
            by_country["Unknown"].append(config)
            
    # حذف و ایجاد مجدد پوشه‌ها
    if os.path.exists('sub'):
        shutil.rmtree('sub')
        
    os.makedirs('sub/protocol', exist_ok=True)
    os.makedirs('sub/country', exist_ok=True)
    os.makedirs('sub/split', exist_ok=True) # --- پوشه جدید برای فایل‌های تقسیم‌شده

    # نوشتن همه کانفیگ‌های منحصر به فرد در یک فایل
    with open('v2ray_configs.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(unique_configs))
    
    # --- بخش جدید: تقسیم فایل اصلی به فایل‌های کوچک‌تر ---
    chunk_size = 100
    for i in range(0, len(unique_configs), chunk_size):
        chunk = unique_configs[i:i + chunk_size]
        file_path = f'sub/split/v2ray_configs_{i // chunk_size + 1}.txt'
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(chunk))
    print(f"✅ Main config file split into smaller files in 'sub/split/' directory.")
    # --- پایان بخش جدید ---

    # نوشتن فایل‌ها بر اساس پروتکل
    for proto, configs in by_protocol.items():
        with open(f'sub/protocol/{proto}.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(configs))
    
    # نوشتن فایل‌ها بر اساس کشور
    for country, configs in by_country.items():
        if configs:
            with open(f'sub/country/{country}.txt', 'w', encoding='utf-8') as f:
                f.write('\n'.join(configs))

    print("\n✅ Success! All configs have been sorted accurately and saved.")

if __name__ == "__main__":
    main()
