import os
import requests
import base64
import re
import json
import shutil
from collections import defaultdict
from urllib.parse import unquote, urlparse, parse_qs, urlencode

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
        # افزایش timeout برای افزایش احتمال موفقیت
        response = requests.get(url, timeout=30) 
        response.raise_for_status()
        content = response.text
        try:
            # دیکود Base64
            decoded_content = base64.b64decode(content.strip()).decode('utf-8')
            return decoded_content.strip().split('\n')
        except Exception:
            # اگر Base64 نبود، محتوای خام را برمی‌گرداند
            return content.strip().split('\n')
    except requests.exceptions.RequestException as e:
        print(f"Error fetching from {url}: {e}")
        return []

def get_remark_from_config(config):
    """نام کانفیگ (remark/ps) را از انواع کانفیگ استخراج می‌کند (برای مرحله تشخیص کشور)."""
    remark = ''
    try:
        # 1. استخراج از بخش fragment (#) برای اکثر پروتکل‌ها
        if '#' in config:
            remark += " " + unquote(config.split('#', 1)[-1])
        
        # 2. استخراج از داخل payload برای vmess
        if config.startswith('vmess://'):
            b64_part = config[8:]
            # برای اطمینان از صحت دیکود، padding اضافه می‌شود
            b64_part += '=' * (-len(b64_part) % 4)
            decoded_part = base64.b64decode(b64_part).decode('utf-8')
            vmess_data = json.loads(decoded_part)
            remark += " " + vmess_data.get('ps', '')
    except Exception as e:
        #print(f"Error extracting remark: {e}")
        pass
    return remark.strip()

def find_country(remark):
    """کشور را بر اساس اولویت (ایموجی > کد > نام) در متن پیدا می‌کند و اموجی/نام کشور را برمی‌گرداند."""
    
    # 1. جستجو برای ایموجی
    for country_name, aliases in COUNTRY_ALIASES.items():
        for alias in aliases:
            # ایموجی‌ها معمولاً بیش از یک کاراکتر هستند و الفبا نیستند
            if not alias.isalpha() and len(alias) > 1:
                if alias in remark:
                    return country_name, alias # برمی‌گرداند (نام کشور، اموجی)
    
    # 2. جستجو برای کدهای دو حرفی و نام کامل (در این حالت، نام کامل کشور برگردانده می‌شود)
    tokens = set(re.split(r'[\s|\(\)\[\]\-_,]+', remark.upper()))
    
    # جستجو برای کدهای دو حرفی
    for country_name, aliases in COUNTRY_ALIASES.items():
        for alias in aliases:
            if len(alias) == 2 and alias.isalpha() and alias.upper() in tokens:
                return country_name, country_name # برمی‌گرداند (نام کشور، نام کامل کشور)

    # جستجو برای نام کامل کشور
    for country_name, aliases in COUNTRY_ALIASES.items():
        for alias in aliases:
            if len(alias) > 2 and alias.isalpha():
                # regex برای جستجوی دقیق کلمه
                pattern = r'(?<![a-zA-Z0-9])' + re.escape(alias) + r'(?![a-zA-Z0-9])'
                if re.search(pattern, remark, re.IGNORECASE):
                    return country_name, country_name # برمی‌گرداند (نام کشور، نام کامل کشور)
                    
    return None, None

def get_config_identifier(config):
    """یک شناسه منحصر به فرد (اثر انگشت) برای هر کانفیگ بر اساس اطلاعات اصلی سرور ایجاد می‌کند."""
    try:
        # برای vmess
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

        # برای سایر پروتکل‌ها (VLESS, SS, Trojan و...)
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

def modify_config_remark(config, new_remark):
    """یک کانفیگ را دریافت کرده و بخش ریمارک (#...) آن را با new_remark جایگزین می‌کند."""
    
    # 1. بخش هش (fragment) را حذف می‌کند
    config_no_fragment = config.split('#', 1)[0]
    
    # 2. ریمارک جدید را اضافه می‌کند. باید URL-encode شود.
    # توجه: برای سابسکریپشن‌های V2Ray، ریمارک معمولاً نباید انکود شود،
    # اما در اینجا برای اطمینان از رفتار صحیح در URL، این کار انجام می‌شود.
    # با این حال، چون V2Ray عموماً انکود شده نمی‌خواهد، new_remark را مستقیماً اضافه می‌کنیم.
    
    # برای VLESS, Trojan و ... که ریمارک در پایان URL قرار دارد
    if not config.startswith('vmess://'):
        return f"{config_no_fragment}#{new_remark}"

    # برای VMess
    try:
        # دیکود کردن payload اصلی vmess
        b64_part = config.split('://')[1]
        if '#' in b64_part:
            b64_part = b64_part.split('#')[0]
        b64_part += '=' * (-len(b64_part) % 4)
        decoded_part = base64.b64decode(b64_part).decode('utf-8')
        vmess_data = json.loads(decoded_part)
        
        # تغییر 'ps' (ریمارک/نام سرور) در JSON
        vmess_data['ps'] = new_remark
        
        # کد کردن مجدد و ساخت کانفیگ جدید
        new_b64_part = base64.b64encode(json.dumps(vmess_data).encode('utf-8')).decode('utf-8').strip('=')
        return f"vmess://{new_b64_part}"
        
    except Exception as e:
        print(f"Error modifying vmess config: {e}. Falling back to adding fragment.")
        # اگر خطا رخ داد، fallback به اضافه کردن fragment (که ممکن است کار نکند)
        return f"{config_no_fragment}#{new_remark}"

def get_server_host(config):
    """آدرس سرور (IP یا دامنه) را برای استفاده به عنوان ریمارک در حالت 'Unknown' استخراج می‌کند."""
    try:
        # برای vmess
        if config.startswith('vmess://'):
            b64_part = config.split('://')[1]
            if '#' in b64_part:
                b64_part = b64_part.split('#')[0]
            b64_part += '=' * (-len(b64_part) % 4)
            decoded_part = base64.b64decode(b64_part).decode('utf-8')
            vmess_data = json.loads(decoded_part)
            return vmess_data.get('add', 'vmess-server')
            
        # برای سایر پروتکل‌ها
        config_no_fragment = config.split('#', 1)[0]
        parsed_url = urlparse(config_no_fragment)
        
        # اگر هاست وجود داشت، آن را برمی‌گرداند، در غیر این صورت پروتکل + پورت را برمی‌گرداند
        host = parsed_url.hostname
        port = parsed_url.port
        
        if host:
            return host
        
        return f"{parsed_url.scheme}://{port or 'port-unknown'}"
        
    except Exception:
        return "Unknown-Server" # در صورت خطا، یک نام عمومی برمی‌گرداند


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
    
    print(f"\nFound {len(unique_configs)} unique configs. Now modifying remarks and sorting...")

    by_protocol = defaultdict(list)
    by_country = defaultdict(list)
    modified_unique_configs = [] # لیست جدید برای نگهداری کانفیگ‌های با ریمارک اصلاح شده

    for config in unique_configs:
        original_remark = get_remark_from_config(config)
        
        country_name, country_identifier = find_country(original_remark)
        
        new_remark = ""
        
        if country_identifier:
            # اگر کشور پیدا شد (اعم از اموجی یا نام کامل)، ریمارک جدید را فقط با آن تنظیم می‌کند
            new_remark = country_identifier 
            
            # بر اساس نام کشور (country_name) برای پوشه‌بندی در by_country استفاده می‌شود
            country_for_sorting = country_name 
            
        else:
            # اگر کشور پیدا نشد، ریمارک جدید را آدرس سرور (IP/Domain) قرار می‌دهد
            new_remark = get_server_host(config)
            country_for_sorting = "Unknown" # برای پوشه‌بندی

        # ایجاد کانفیگ جدید با ریمارک تمیز شده
        modified_config = modify_config_remark(config, new_remark)
        modified_unique_configs.append(modified_config)
        
        # ذخیره کانفیگ اصلاح شده برای دسته‌بندی
        proto = modified_config.split('://')[0]
        by_protocol[proto.upper()].append(modified_config)
        by_country[country_for_sorting].append(modified_config)
            
    # حذف و ایجاد مجدد پوشه‌ها
    if os.path.exists('sub'):
        shutil.rmtree('sub')
        
    os.makedirs('sub/protocol', exist_ok=True)
    os.makedirs('sub/country', exist_ok=True)
    os.makedirs('sub/split', exist_ok=True)

    # نوشتن همه کانفیگ‌های منحصر به فرد با ریمارک اصلاح شده در یک فایل
    with open('v2ray_configs.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(modified_unique_configs))
    
    # --- بخش: تقسیم فایل اصلی به فایل‌های کوچک‌تر ---
    chunk_size = 100
    for i in range(0, len(modified_unique_configs), chunk_size):
        chunk = modified_unique_configs[i:i + chunk_size]
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

    print("\n✅ Success! All configs have been cleaned, sorted, and saved.")

if __name__ == "__main__":
    main()
