import os
import requests
import base64
from datetime import datetime

def fetch_and_decode_content(url):
    """
    محتوای یک URL را دریافت کرده و اگر با Base64 کد شده باشد، آن را دیکود می‌کند.
    """
    try:
        # درخواست GET به URL با یک مهلت زمانی ۱۰ ثانیه‌ای
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # اگر خطایی (مثل 404 یا 500) رخ دهد، برنامه متوقف می‌شود

        content = response.text
        
        # تلاش برای دیکود کردن محتوا از Base64
        # اکثر لینک‌های اشتراک کانفیگ به صورت Base64 هستند
        try:
            # حذف فاصله‌ها و خطوط جدید اضافی از ابتدا و انتهای محتوا
            decoded_content = base64.b64decode(content.strip()).decode('utf-8')
            # محتوای دیکود شده را بر اساس خطوط جدید به لیستی از کانفیگ‌ها تبدیل می‌کند
            return decoded_content.strip().split('\n')
        except Exception:
            # اگر محتوا Base64 نبود، همان را به صورت خط به خط برمی‌گردانیم
            return content.strip().split('\n')
            
    except requests.exceptions.RequestException as e:
        print(f"خطا در دریافت اطلاعات از {url}: {e}")
        return [] # در صورت بروز خطا، یک لیست خالی برمی‌گرداند

def main():
    """
    تابع اصلی برنامه که تمام مراحل را مدیریت می‌کند.
    """
    # خواندن لیست URL ها از GitHub Secrets که به عنوان متغیر محیطی (environment variable) به اسکریپت داده شده
    urls_str = os.environ.get('CONFIG_URLS')
    if not urls_str:
        print("متغیر CONFIG_URLS پیدا نشد یا خالی است. لطفا سکرت‌های ریپازیتوری را بررسی کنید.")
        return

    urls = urls_str.strip().split('\n')
    all_configs = []

    print(f"شروع پردازش {len(urls)} لینک...")

    for url in urls:
        if url.strip(): # اطمینان از اینکه لینک خالی یا فقط حاوی فاصله نیست
            print(f"در حال استخراج از: {url.strip()}")
            configs = fetch_and_decode_content(url.strip())
            if configs:
                # اضافه کردن کانفیگ‌های جدید به لیست کلی
                all_configs.extend(configs)
                print(f"-> تعداد {len(configs)} کانفیگ از این لینک پیدا شد.")

    # برای حذف کانفیگ‌های تکراری و حفظ ترتیب آن‌ها، از دیکشنری استفاده می‌کنیم
    unique_configs = list(dict.fromkeys(filter(None, all_configs))) # filter(None, ...) کانفیگ‌های خالی را حذف می‌کند
    
    if unique_configs:
        # نام فایل خروجی
        output_filename = 'v2ray_configs.txt'
        # ذخیره تمام کانفیگ‌های منحصر به فرد در فایل خروجی
        with open(output_filename, 'w', encoding='utf-8') as f:
            for config in unique_configs:
                f.write(config + '\n')
        
        print("\n✅ عملیات با موفقیت انجام شد.")
        print(f"تعداد کل کانفیگ‌های منحصر به فرد: {len(unique_configs)}")
        print(f"فایل خروجی در '{output_filename}' ذخیره شد.")
    else:
        print("\n⚠️ هیچ کانفیگی برای ذخیره کردن پیدا نشد.")

if __name__ == "__main__":
    main()
