from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
from bs4 import BeautifulSoup
import openpyxl
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
from selenium.webdriver.chrome.options import Options
import datetime
import jdatetime
import urllib.parse
import pandas as pd
import sys
import subprocess
from datetime import datetime, timedelta
from pymongo import MongoClient, UpdateOne  # ✅ اضافه شدن UpdateOne برای جلوگیری از تکرار

# --------------------- تنظیمات MongoDB ---------------------
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "costs"
COLLECTION_NAME = "campaigns"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# ایجاد ایندکس یکتا برای جلوگیری از تکرار در سطح دیتابیس
collection.create_index([("account_name", 1), ("campaign_name", 1), ("campaign_date", 1)], unique=True)
# -----------------------------------------------------------

# چک برای دسترسی ادمین
if not os.environ.get('USERPROFILE'):
    script = sys.argv[0]
    params = sys.argv[1:]
    subprocess.run(['powershell', 'Start-Process', 'python', '-ArgumentList', script] + params, shell=True)
else:
    print("🔄 Running script with admin privileges...")

# تنظیمات لاگ فایل
log_file_path = "C:/Users/digiton/Desktop/logs/magnet.txt"
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
log_file = open(log_file_path, "a", encoding="utf-8")
sys.stdout = log_file
sys.stderr = log_file

# تابع تبدیل تاریخ شمسی به میلادی
def convert_to_gregorian(date):
    try:
        year, month, day = map(int, str(date).split('/'))
        gregorian_date = jdatetime.date(year, month, day).togregorian()
        return gregorian_date.strftime('%Y-%m-%d')
    except Exception as e:
        print(f"Error converting date {date}: {e}")
        return None

# لیست اکانت‌ها
accounts = [
    {
        "username": "#",
        "password": "#",
        "download_path": r"C:\Users\digiton\Desktop\FinallWriteAdNetwork\Tapsell\MagnetDownloadPath\Account1",
        "account_name": "Account1"
    },
    {
        "username": "#",
        "password": "#",
        "download_path": r"C:\Users\digiton\Desktop\FinallWriteAdNetwork\Tapsell\MagnetDownloadPath\Account2",
        "account_name": "Account2"
    },
    {
        "username": "#",
        "password": "#",
        "download_path": r"C:\Users\digiton\Desktop\FinallWriteAdNetwork\Tapsell\MagnetDownloadPath\Account3",
        "account_name": "Account3"
    }
]

# مسیر ChromeDriver
CHROME_DRIVER_PATH = r"C:\Users\digiton\Desktop\chromeDriver\chromedriver-win64\chromedriver.exe"

# پردازش هر اکانت
for account in accounts:
    print(f"\n🔄 Processing account: {account['account_name']}")

    download_path = account['download_path']
    if not os.path.exists(download_path):
        os.makedirs(download_path)
        print(f"Created directory: {download_path}")

    # پاکسازی فایل‌های قدیمی در پوشه دانلود
    if os.path.exists(download_path):
        for file in os.listdir(download_path):
            file_path = os.path.join(download_path, file)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")

    # تنظیمات کروم برای دانلود خودکار
    chrome_options = Options()
    prefs = {"download.default_directory": download_path, "safebrowsing.enabled": True}
    chrome_options.add_experimental_option("prefs", prefs)

    service = Service(CHROME_DRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # ورود به سایت
        driver.get("https://app.magnet.ir/User/Login")
        time.sleep(3)

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "email"))).send_keys(account['username'])
        driver.find_element(By.ID, "loginPassword").send_keys(account['password'])
        driver.find_element(By.CSS_SELECTOR, ".btn.btn-primary").click()
        time.sleep(5)

        print(f"Login successful for {account['account_name']}!")

        # کلید انتقال به پنل گزارشات
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, "btn-action"))).click()
        time.sleep(5)

        # محاسبه تاریخ دیروز (شمسی) برای فیلتر گزارش
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_shamsi = jdatetime.date.fromgregorian(date=yesterday)
        yesterday_shamsi_str = yesterday_shamsi.strftime("%Y-%m-%d")
        yesterday_shamsi_encoded = urllib.parse.quote(yesterday_shamsi_str, safe='')

        # لود کردن صفحه گزارش با تاریخ مشخص
        dynamic_url = f"https://app.magnet.ir/Campaign/Report?secondPriority=date_&dateFrom={yesterday_shamsi_encoded}&dateTo={yesterday_shamsi_encoded}&dateEnum=CustomDate"
        driver.get(dynamic_url)
        time.sleep(5)

        # کلیک روی دکمه دانلود اکسل
        download_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "downloadButton")))
        driver.execute_script("arguments[0].click();", download_button)
        print(f"Download button clicked for {account['account_name']}.")
        time.sleep(10)

        # پیدا کردن فایل اکسل دانلود شده
        excel_file = None
        for file in os.listdir(download_path):
            if file.endswith((".xlsx", ".xls")):
                excel_file = os.path.join(download_path, file)
                break

        if excel_file:
            print(f"Found Excel file: {excel_file}")
            df = pd.read_excel(excel_file, skiprows=5)

            # انتخاب ستون‌های مورد نیاز و نام‌گذاری
            df = df.iloc[:, [1, 2, 3]]
            df.columns = ["campaign_name", "campaign_date", "cost"]

            # حذف ردیف‌های بدون هزینه و تبدیل تاریخ
            df = df[df["cost"] != 0]
            df["campaign_date"] = df["campaign_date"].apply(convert_to_gregorian)
            df["account_name"] = account['account_name']

            # --------------------- ذخیره‌سازی هوشمند (Upsert) ---------------------
            operations = []
            for _, row in df.iterrows():
                # کلید شناسایی یکتا: نام اکانت + نام کمپین + تاریخ
                filter_criteria = {
                    "account_name": row["account_name"],
                    "campaign_name": row["campaign_name"],
                    "campaign_date": row["campaign_date"]
                }
                
                # مقادیری که باید بروزرسانی شوند یا در صورت نبودن درج شوند
                update_data = {
                    "$set": {
                        "cost": row["cost"],
                        "updated_at": datetime.utcnow()
                    },
                    "$setOnInsert": {
                        "inserted_at": datetime.utcnow()
                    }
                }
                
                # ایجاد دستور بروزرسانی/درج
                operations.append(UpdateOne(filter_criteria, update_data, upsert=True))

            if operations:
                result = collection.bulk_write(operations)
                print(f"Database Stats for {account['account_name']}:")
                print(f" - Matched: {result.matched_count}")
                print(f" - Upserted: {result.upserted_count}")
                print(f" - Modified: {result.modified_count}")
            else:
                print(f"No data to process for {account['account_name']}.")
            # -----------------------------------------------------------------------

            # ذخیره بک‌آپ CSV
            output_csv_path = os.path.join(download_path, f"{account['account_name']}.csv")
            df.to_csv(output_csv_path, index=False, encoding="utf-8")
        else:
            print(f"No Excel file found for {account['account_name']}!")

    except Exception as e:
        print(f"Error processing {account['account_name']}: {e}")

    finally:
        driver.quit()

print("\n✅ All accounts processed and synced with MongoDB!")
print("-------------------------------------------------------------------------------------------------")

client.close()
log_file.close()