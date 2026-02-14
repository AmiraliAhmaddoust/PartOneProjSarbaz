from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
from bs4 import BeautifulSoup
import openpyxl
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta
from selenium.webdriver.chrome.options import Options
import os
import pandas as pd
from google.oauth2 import service_account
from pandas_gbq import to_gbq
import sys
import subprocess
from pymongo import MongoClient  # ✅ برای MongoDB

# --------------------- تنظیمات MongoDB ---------------------
MONGO_URI = "mongodb://localhost:27017/"   # اگر سرور ریموت داری، اینجا رو عوض کن
DB_NAME = "costs"
COLLECTION_NAME = "campaigns"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]
# -----------------------------------------------------------

if not os.environ.get('USERPROFILE'):
    script = sys.argv[0]
    params = sys.argv[1:]
    subprocess.run(['powershell', 'Start-Process', 'python', '-ArgumentList', script] + params, shell=True)
else:
    print("در حال اجرای اسکریپت با دسترسی ادمین...")

print("🔄 در حال اجرای کد اصلی...")

log_file = open(r"C:\Users\digiton\Desktop\logs\Yektanet.txt", "a", encoding="utf-8")
sys.stdout = log_file
sys.stderr = log_file

download_path = r"C:\Users\digiton\Desktop\FinallWriteAdNetwork\Tapsell\Yektanet"

# پاک کردن تمام فایل‌ها داخل فولدر دانلود
if os.path.exists(download_path):
    try:
        for file in os.listdir(download_path):
            file_path = os.path.join(download_path, file)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    print(f"Deleted file: {file_path}")
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")
        print("✅ همه فایل‌ها با موفقیت حذف شدند.")
    except Exception as e:
        print(f"Error accessing directory {download_path}: {e}")
else:
    print("❌ فولدر مورد نظر پیدا نشد.")

chrome_options = Options()
prefs = {"download.default_directory": download_path, "safebrowsing.enabled": True}
chrome_options.add_experimental_option("prefs", prefs)
CHROME_DRIVER_PATH = r"C:\Users\digiton\Desktop\chromeDriver\chromedriver-win64\chromedriver.exe"
service = Service(CHROME_DRIVER_PATH)

accounts = [
    {"email": "", "password": ""},
    {"email": "", "password": ""},
    {"email": "", "password": ""},
    {"email": "", "password": ""},
    {"email": "", "password": ""},
    {"email": "", "password": ""},
    {"email": "", "password": ""},
    {"email": "", "password": ""},
    {"email": "", "password": ""},
    {"email": "", "password": ""}
]

j = 0

for account in accounts:
    driver = webdriver.Chrome(service=service, options=chrome_options)
    j = j + 1

    # باز کردن صفحه لاگین
    driver.get("https://accounts.yektanet.com/login/?plt=yektanet&type=adv&redirect=https%3A%2F%2Fpanel.yektanet.com%2F")
    time.sleep(3)  # ⏳ انتظار برای بارگذاری صفحه

    # ورود به حساب
    driver.find_element(By.ID, "login_input").send_keys(account["email"])
    driver.find_element(By.ID, "password_input").send_keys(account["password"])
    driver.find_element(By.CSS_SELECTOR, ".auth-btn.btn.btn-primary.font-5").click()
    time.sleep(10)  # ⏳ صبر برای پردازش لاگین

    print(f"✅ Login successful! in this account :  {account['email']}")

    # محاسبه تاریخ دیروز برای گزارش
    yesterday = datetime.now() - timedelta(days=1)
    yesterday_str = yesterday.strftime("%Y-%m-%d")  # فرمت: 2025-09-29

    # هدایت به صفحه گزارشات بر اساس اکانت
    if(j==1):
     driver.get(     "https://panel.yektanet.com/u/Sr6Mpub7/report/campaigns"
                     "?campaign=all&tag=f4376635-1bc1-4e7b-b022-dd8599499003"
                     f"&s={yesterday_str}T00%3A00%3A00"
                     f"&e={yesterday_str}T23%3A59%3A59"
                     )
    elif(j==2):
     driver.get(    "https://panel.yektanet.com/u/kCDfmcCw/report/campaigns"
                     "?campaign=all&tag=06f2cb16-9a65-4b0b-ad2b-c771e8e04403"
                     f"&s={yesterday_str}T00%3A00%3A00"
                     f"&e={yesterday_str}T23%3A59%3A59"
                     )
    elif(j==3):
     driver.get(    "https://panel.yektanet.com/u/MpgFZDHN/report/campaigns"
                     "?campaign=all&tag=75271209-3e49-49e4-895f-e4adf7d45ffe"
                     f"&s={yesterday_str}T00%3A00%3A00"
                     f"&e={yesterday_str}T23%3A59%3A59"
                     )
    elif(j==4):
     driver.get(    "https://panel.yektanet.com/u/St5O3y6a/report/campaigns"
                    "?campaign=all&tag=5cfdd5c5-4ed9-49a0-9a9e-2ff653509ec7"
                    f"&s={yesterday_str}T00%3A00%3A00"
                    f"&e={yesterday_str}T23%3A59%3A59"
                    )
    elif(j==5):
     driver.get(    "https://panel.yektanet.com/u/Jmn6b4EA/report/campaigns?campaign=all&tag=6f1b4de6-6687-438f-805c-2aa329216fc6"
                   f"&s={yesterday_str}T00%3A00%3A00"
                   f"&e={yesterday_str}T23%3A59%3A59"
                   )
    elif(j==6):
     driver.get(    "https://panel.yektanet.com/u/iDEJhCGH/report/campaigns?campaign=all&tag=7a18adfa-6c33-4716-b528-4dc8158cc67e"
                   f"&s={yesterday_str}T00%3A00%3A00"
                   f"&e={yesterday_str}T23%3A59%3A59"
                   )
    elif(j==7):
     driver.get(    "https://panel.yektanet.com/u/ZQlBjkvL/report/campaigns?campaign=all&tag=549af257-d479-42ee-b946-8c7d82077d57"
                   f"&s={yesterday_str}T00%3A00%3A00"
                   f"&e={yesterday_str}T23%3A59%3A59"
                   )
    elif(j==8):
     driver.get(    "https://panel.yektanet.com/u/2Q0wEMyq/report/campaigns?campaign=all&tag=4a495837-59ba-4b53-b0fb-2d75753925d5"
                   f"&s={yesterday_str}T00%3A00%3A00"
                   f"&e={yesterday_str}T23%3A59%3A59"
                   )
    elif(j==9):
     driver.get(    "https://panel.yektanet.com/u/xcygYFhx/report/campaigns?campaign=all&tag=28918d79-866b-4d7b-aee8-a29641d62717"
                   f"&s={yesterday_str}T00%3A00%3A00"
                   f"&e={yesterday_str}T23%3A59%3A59"
                   )
    elif(j==10):
     driver.get(    "https://panel.yektanet.com/u/Sr6Mpub7/report/campaigns?campaign=all&tag=f4376635-1bc1-4e7b-b022-dd8599499003"
                   f"&s={yesterday_str}T00%3A00%3A00"
                   f"&e={yesterday_str}T23%3A59%3A59"
                   )
    time.sleep(15)

    try:
        driver.execute_script("document.body.style.zoom='10%'")
        time.sleep(2)
        link = driver.find_element(By.ID, "table-campaign-title")
        link.click()
        time.sleep(10)
        
        # منتظر ماندن برای ظاهر شدن دکمه دانلود
        download_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'btn-outline-primary') and .//i[contains(@class, 'icon-download')]]"))
        )
        
        # کلیک با جاوا اسکریپت برای اطمینان
        driver.execute_script("arguments[0].click();", download_button)
        
        print(f"✅ فایل برای اکانت {account['email']} دانلود شد.")
        time.sleep(10) # زمان برای تکمیل دانلود
    except Exception:
        print("❌ دکمه دانلود پیدا نشد.")

    driver.quit()

print("🎉 تمام اطلاعات پردازش و ذخیره شد (دانلود گزارش‌ها).")

# پردازش فایل‌های اکسل دانلود شده
folder_path = r'C:\Users\digiton\Desktop\FinallWriteAdNetwork\Tapsell\Yektanet'
excel_files = [f for f in os.listdir(folder_path) if f.endswith((".xlsx", ".xls"))]

counter = 0
dfs = []  # ✅ برای نگه‌داشتن همه‌ی دیتافریم‌ها جهت اینسرت یک‌جا در MongoDB

for file in excel_files:
    file_path = os.path.join(folder_path, file)
    df = pd.read_excel(file_path, header=None)

    # استخراج تاریخ میلادی از سلول ردیف 0، ستون 2
    date_miladi = str(df.iloc[0, 2]).rsplit(" - ", 1)[0]
    date_object = datetime.strptime(date_miladi, "%A %d %B %Y")
    formatted_date = date_object.strftime("%Y-%m-%d")

    # تمیز کردن و ساخت جدول نهایی
    df = df.iloc[4:].reset_index(drop=True)
    
    # فقط سه ستون اول را نگه داریم: نام کمپین، نوع، هزینه
    df = df.iloc[:, :3]
    df.columns = ["campaign_name", "campaign_type", "cost"]
    
    # اضافه کردن تاریخ به عنوان ستون جدا
    df["campaign_date"] = formatted_date
    
    # فقط ستون‌های موردنیاز برای مونگو
    df = df[["campaign_name", "campaign_date", "cost"]]


    dfs.append(df)  # ✅ نگه‌داشتن برای MongoDB

    # ساخت CSV جداگانه برای هر فایل
    counter += 1
    output_csv_path = os.path.join(folder_path, f"{counter}_updated.csv")
    df.to_csv(output_csv_path, index=False, encoding="utf-8")
    print(f"فایل جدید ذخیره شد: {output_csv_path}")

# ✅ اینسرت همه‌ی داده‌های Yektanet در MongoDB
try:
    if dfs:
        combined_df = pd.concat(dfs, ignore_index=True)

        # 🔥 فقط ردیف‌هایی که cost عددی و بزرگ‌تر از صفر دارند
        combined_df["cost"] = pd.to_numeric(combined_df["cost"], errors="coerce")
        combined_df = combined_df[(combined_df["cost"].notna()) & (combined_df["cost"] > 0)]

        if combined_df.empty:
            print("❗ بعد از فیلتر کردن، هیچ ردیفی با cost معتبر (>0) باقی نماند.")
        else:
            records = combined_df.to_dict("records")

            # افزودن فیلدهای اضافی برای مانگو
            for r in records:
                r["inserted_at"] = datetime.utcnow()
                r["source"] = "yektanet"  # ✅ تا بعداً راحت تفکیک کنی

            result = collection.insert_many(records)
            print(f"✅ {len(result.inserted_ids)} رکورد از Yektanet در MongoDB (costs.campaigns) ذخیره شد.")
    else:
        print("❗ هیچ فایل اکسل معتبری برای پردازش پیدا نشد.")
except Exception as e:
    print("خطا در اینسرت داده‌ها در MongoDB:", str(e))

now = datetime.now()
yesterday = now - timedelta(days=1)
formatted_yesterday = yesterday.strftime("%Y/%m/%d")
print("تاریخ یک روز قبل:", formatted_yesterday)
print("-------------------------------------------------------------------------------------------------")
print("-------------------------------------------------------------------------------------------------")

# بستن کانکشن‌ها
client.close()
log_file.close()
