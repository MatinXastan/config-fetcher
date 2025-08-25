import os
import requests
import base64
import socket
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

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

def extract_ip_port(config_uri):
    """آدرس IP و پورت را از یک URI کانفیگ استخراج می‌کند."""
    try:
        # برای vless/trojan: vless://uuid@ip:port...
        match = re.search(r'vless://.*?@(.*?):(\d+)', config_uri)
        if match:
            return match.group(1), int(match.group(2))
        
        # برای vmess (که base64 انکود شده)
        if config_uri.startswith('vmess://'):
            try:
                decoded_part = base64.b64decode(config_uri[8:]).decode('utf-8')
                add_match = re.search(r'"add":"(.*?)"', decoded_part)
                port_match = re.search(r'"port":"(\d+)"', decoded_part)
                if add_match and port_match:
                    return add_match.group(1), int(port_match.group(1))
            except Exception:
                return None, None
    except Exception:
        return None, None
    return None, None

def check_server_connectivity(server_ip, port, timeout=2):
    """بررسی می‌کند که آیا می‌توان به یک IP و پورت خاص متصل شد یا نه."""
    try:
        # یک سوکت TCP ایجاد می‌کند
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            # تلاش برای اتصال
            s.connect((server_ip, port))
        return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

def test_config(config):
    """یک کانفیگ را تست می‌کند و در صورت فعال بودن، آن را برمی‌گرداند."""
    ip, port = extract_ip_port(config)
    if ip and port:
        if check_server_connectivity(ip, port):
            print(f"  [SUCCESS] {ip}:{port} is reachable.")
            return config
    return None

def main():
    """تابع اصلی برنامه."""
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
    valid_protocols = ('vless://', 'vmess://') # تست برای این دو پروتکل ساده‌تر است
    initial_valid_configs = [c for c in all_configs if c and c.strip().startswith(valid_protocols)]
    unique_configs = list(dict.fromkeys(initial_valid_configs))
    
    print(f"\nFound {len(unique_configs)} unique configs. Now testing connectivity...")
    
    active_configs = []
    # استفاده از چند ترد برای سرعت بخشیدن به تست همزمان کانفیگ‌ها
    with ThreadPoolExecutor(max_workers=50) as executor:
        future_to_config = {executor.submit(test_config, config): config for config in unique_configs}
        for future in as_completed(future_to_config):
            result = future.result()
            if result:
                active_configs.append(result)

    if active_configs:
        output_filename = 'v2ray_configs.txt'
        with open(output_filename, 'w', encoding='utf-8') as f:
            for config in active_configs:
                f.write(config + '\n')
        
        print(f"\n✅ Success! Found {len(active_configs)} active configs.")
        print(f"Output saved to '{output_filename}'.")
    else:
        print("\n⚠️ No active configs found after testing.")

if __name__ == "__main__":
    main()
```

### **مرحله دوم: فایل ورک‌فلو (`main.yml`)**

فایل ورک‌فلو شما **هیچ تغییری نیاز ندارد** و همان نسخه اصلاح شده قبلی باقی می‌ماند. چون تمام منطق تست به کد پایتون منتقل شده، اکشن فقط کافی است همان اسکریپت را اجرا کند.

برای یادآوری، این همان فایل `main.yml` است که باید داشته باشید:


```yaml
name: Fetch and Commit V2Ray Configs

on:
  schedule:
    - cron: '0 */6 * * *'
  workflow_dispatch:

jobs:
  build-and-commit:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests

      - name: Run Python script to fetch and test configs
        env:
          CONFIG_URLS: ${{ secrets.CONFIG_URLS }}
        run: python main.py

      - name: Commit and push if changed
        run: |
          git config --global user.name 'github-actions[bot]'
          git config --global user.email 'github-actions[bot]@users.noreply.github.com'
          git add v2ray_configs.txt
          if ! git diff --staged --quiet; then
            git commit -m "Update active configs [$(date)]"
            git push
            echo "✅ New active configs committed and pushed."
          else
            echo "ℹ️ No changes to commit."
          fi
