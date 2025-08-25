import os
import requests
import base64
from datetime import datetime

def fetch_and_decode_content(url):
    """
    محتوای یک URL را دریافت کرده و اگر با Base64 کد شده باشد، آن را دیکود می‌کند.
    """
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
    """
    تابع اصلی برنامه که تمام مراحل را مدیریت می‌کند.
    """
    # خواندن لیست URL ها از GitHub Secrets
    urls_str = os.environ.get('CONFIG_URLS')
    if not urls_str:
        print("CONFIG_URLS secret not found or is empty. Please check repository secrets.")
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
                print(f"-> Found {len(configs)} lines from this URL.")

    # --- بخش بهبود یافته برای فیلتر کردن ---
    all_configs = list(filter(None, all_configs)) 
    valid_protocols = ('vless://', 'vmess://', 'ss://', 'trojan://', 'tuic://')
    valid_configs = [c for c in all_configs if c.strip().startswith(valid_protocols)]
    unique_configs = list(dict.fromkeys(valid_configs))
    # --- پایان بخش بهبود یافته ---
    
    if unique_configs:
        output_filename = 'v2ray_configs.txt'
        with open(output_filename, 'w', encoding='utf-8') as f:
            for config in unique_configs:
                f.write(config + '\n')
        
        print(f"\n✅ Success! Found {len(unique_configs)} unique and valid configs.")
        print(f"Output saved to '{output_filename}'.")
    else:
        print("\n⚠️ No valid configs found to save.")

if __name__ == "__main__":
    main()
