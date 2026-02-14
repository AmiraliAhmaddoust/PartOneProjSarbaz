import requests
import time
import pandas as pd
import jdatetime
import os
import sys
from datetime import datetime, timedelta
import gspread
from google.oauth2 import service_account
from pandas_gbq import to_gbq
from pymongo import MongoClient  # 👈 اضافه برای MongoDB

# اطلاعات ورود (جایگزین کن با مقادیر خودت)
METRIX_USERNAME = ''
METRIX_PASSWORD = ''

# مسیر دایرکتوری خروجی
OUTPUT_DIR = r"C:\Users\digiton\Desktop\FinallWriteAdNetwork\Metrixrev\output"
PROCESSED_OUTPUT_DIR = r"C:\Users\digiton\Desktop\FinallWriteAdNetwork\Metrixrev\processed_output"

log_file = open(r"C:\Users\digiton\Desktop\logs\MetrixRevLog.txt", "a", encoding="utf-8")
sys.stdout = log_file
sys.stderr = log_file

# ------------------ تنظیمات MongoDB ------------------
MONGO_URI = "mongodb://localhost:27017"       # اگر روی سرور دیگری هست، این آدرس را عوض کن
MONGO_DB_NAME = "metrix_revenue"             # اسم دیتابیس

mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client[MONGO_DB_NAME]

def save_df_to_mongo(df, collection_name):
    """
    ذخیره دیتافریم در MongoDB.
    هر بار که صدا زده شود، رکوردهای جدید به کالکشن اضافه می‌شود (append).
    """
    try:
        records = df.to_dict(orient='records')
        if not records:
            print(f"⚠️ دیتافریم خالی است، چیزی در MongoDB ذخیره نشد. کالکشن: {collection_name}")
            return
        collection = mongo_db[collection_name]
        result = collection.insert_many(records)
        print(f"✅ {len(result.inserted_ids)} رکورد در کالکشن '{collection_name}' درج شد.")
    except Exception as e:
        print(f"❌ خطا در ذخیره دیتا در MongoDB برای کالکشن {collection_name}: {e}")

# ------------------ آماده‌سازی پوشه‌ها ------------------

# ایجاد دایرکتوری خروجی در صورت عدم وجود
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# ایجاد دایرکتوری خروجی پردازش‌شده در صورت عدم وجود
if not os.path.exists(PROCESSED_OUTPUT_DIR):
    os.makedirs(PROCESSED_OUTPUT_DIR)

# حذف فایل‌های CSV قبلی در دایرکتوری خروجی
for file in os.listdir(OUTPUT_DIR):
    if file.endswith(".csv"):
        file_path = os.path.join(OUTPUT_DIR, file)
        os.remove(file_path)
        print(f"Deleted previous CSV file: {file_path}")

# لیست بازی‌ها با پکیج‌نیم و اسلاگ مربوطه
GAMES = [
    {"package_name": "", "slug": ""},
    {"package_name": "", "slug": ""},
    {"package_name": "", "slug": ""},
    {"package_name": "", "slug": ""},
    {"package_name": "", "slug": ""},
    {"package_name": "", "slug": ""},
    {"package_name": "", "slug": ""},
    {"package_name": "", "slug": ""},
    {"package_name": "", "slug": ""},
    {"package_name": "", "slug": ""},
    {"package_name": "", "slug": ""},
    {"package_name": "", "slug": ""},
    {"package_name": "", "slug": ""},
    {"package_name": "", "slug": ""},
    {"package_name": "", "slug": ""},
    {"package_name": "", "slug": ""},
    {"package_name": "", "slug": ""},
    {"package_name": "", "slug": ""}
]

# مرحله 1: گرفتن access token
def get_access_token():
    url = "https://web.metrix.ir/oauth/token"
    headers = {
        "authorization": "Basic bWV0cml4X2Rhc2hib2FyZDpZSTc1TU1FMlJS"
    }
    data = {
        "grant_type": "password",
        "username": METRIX_USERNAME,
        "password": METRIX_PASSWORD
    }

    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()
    token = response.json()["access_token"]
    return token

# مرحله 2: درخواست export ایونت
def request_export(token, package_name, start_date, end_date, event_slugs, dimensions):
    url = f"https://web.metrix.ir/v2/apps/{package_name}/export/events?lang=en"
    headers = {
        "authorization": f"bearer {token}",
        "accept": "application/json",
        "content-type": "application/json"
    }
    payload = {
        "startDate": str(start_date),
        "endDate": str(end_date),
        "eventSlug": event_slugs,
        "dimensions": dimensions,
        "conditions": {},
        "dateFilterType": "TIMESTAMP"
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    task_id = response.json()["taskId"]
    return task_id

# مرحله 3: چک کردن وضعیت
def check_status(token, package_name, task_id):
    url = f"https://web.metrix.ir/v2/apps/{package_name}/export/status/{task_id}"
    headers = {
        "authorization": f"bearer {token}",
        "accept": "application/json"
    }

    while True:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        result = response.json()

        status = result.get("status")
        print(f"Task Status for {package_name}: {status}")
        if status == "PROCESSED":
            return result["url"]
        elif status == "ERROR":
            raise Exception(f"Export task failed for {package_name}.")
        
        time.sleep(10)  # هر ۱۰ ثانیه دوباره چک کن

# مرحله 4: دانلود فایل نهایی
def download_file(url, filename):
    response = requests.get(url)
    response.raise_for_status()
    file_path = os.path.join(OUTPUT_DIR, filename)
    with open(file_path, 'wb') as f:
        f.write(response.content)
    print(f"File downloaded: {file_path}")

# تبدیل تاریخ شمسی به میلادی
def shamsi_to_miladi(shamsi_date_str):
    try:
        date_only = shamsi_date_str.split(" ")[0]
        shamsi_date = jdatetime.datetime.strptime(date_only, '%Y-%m-%d')
        miladi_date = shamsi_date.togregorian()
        return miladi_date.strftime('%Y%m%d')
    except Exception as e:
        print(f"Error converting date {shamsi_date_str}: {e}")
        return None

# پردازش فایل‌های CSV خام (اضافه کردن تاریخ میلادی)
def process_csv_files(file_urls, package_name):
    for i, url in enumerate(file_urls):
        file_name = f"{package_name.replace('.', '_')}_events_{i}.csv"
        file_path = os.path.join(OUTPUT_DIR, file_name)
        print(f"📊 پردازش فایل {file_name}...")

        df = pd.read_csv(file_path)
        df.columns = df.columns.str.replace(' ', '_', regex=False)

        if 'First_Install_Time' in df.columns:
            df['miladi_first_install_time'] = df['First_Install_Time'].apply(shamsi_to_miladi)
        else:
            print(f"ستون 'First Install Time' در فایل {file_name} یافت نشد.")
            df['miladi_first_install_time'] = None

        if 'Time' in df.columns:
            df['miladi_time'] = df['Time'].apply(shamsi_to_miladi)
        else:
            print(f"ستون 'Time' در فایل {file_name} یافت نشد.")
            df['miladi_time'] = None

        new_file_name = f"processed_{package_name.replace('.', '_')}_events_{i}.csv"
        new_file_path = os.path.join(OUTPUT_DIR, new_file_name)
        df.to_csv(new_file_path, index=False, encoding='utf-8')
        print(f"✅ فایل پردازش‌شده ذخیره شد: {new_file_path}")
        os.remove(file_path)
        print(f"✅ فایل قدیمی حذف شد {file_path}")

# ساخت فایل نهایی و آماده برای نوشتن در MongoDB
def process_file(file_path, output_path):
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    elif file_path.endswith('.xlsx'):
        df = pd.read_excel(file_path)
    else:
        raise ValueError("فایل باید CSV یا Excel باشد")
    
    required_columns = [
        'Network', 'Campaign', 'Ad_Group', 'Creative', 'Sub_Id',
        'First_Install_Time', 'Time', 'Revenue_Amount',
        'miladi_first_install_time', 'miladi_time', 'Install_Source'
    ]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"ستون‌های زیر در فایل وجود ندارند: {missing_columns}")
    
    df[required_columns] = df[required_columns].fillna('').astype(str)
    
    df['Unique_Combination'] = df[required_columns].agg('-'.join, axis=1)
    
    final_columns = required_columns + ['Unique_Combination']
    df_final = df[final_columns]
    df_final.columns = df_final.columns.str.replace(' ', '_', regex=False)
    
    if output_path.endswith('.csv'):
        df_final.to_csv(output_path, index=False)
    else:
        df_final.to_excel(output_path, index=False)
    
    print(f'فایل پردازش شده ذخیره شد در: {output_path}')
    
    return df_final

# ------------------ اجرای برنامه ------------------

if __name__ == "__main__":
    token = get_access_token()
    print("Access token دریافت شد.")

    now = datetime.now()
    midnight_today = datetime(now.year, now.month, now.day)
    end = int(midnight_today.timestamp() * 1000)
    midnight_yesterday = midnight_today - timedelta(days=1)
    start = int(midnight_yesterday.timestamp() * 1000)

    print(f"start = {start}")
    print(f"end = {end}")

    dimensions = ["network", "campaign", "adGroup", "creative", "subId", "installSource", "reinstalled", "revenue"]

    for game in GAMES:
        package_name = game["package_name"]
        slug = game["slug"]
        print(f"\n🔄 پردازش بازی: {package_name} با اسلاگ: {slug}")

        try:
            task_id = request_export(token, package_name, start, end, [slug], dimensions)
            print(f"Task ID دریافت شد برای {package_name}: {task_id}")

            file_urls = check_status(token, package_name, task_id)
            if not isinstance(file_urls, list):
                file_urls = [file_urls]
            print(f"URLs برای {package_name}: {file_urls}")

            for i, url in enumerate(file_urls):
                file_name = f"{package_name.replace('.', '_')}_events_{i}.csv"
                download_file(url, file_name)

            print(f"📈 شروع پردازش فایل‌های CSV برای {package_name}...")
            process_csv_files(file_urls, package_name)

        except Exception as e:
            print(f"❌ خطا در پردازش بازی {package_name}: {e}")
            continue

    print("✅ پردازش تمام بازی‌ها به پایان رسید.")

    # مرحله نهایی: تبدیل processed_*.csv به final_*.csv و ذخیره در MongoDB
    for filename in os.listdir(OUTPUT_DIR):
        if filename.startswith("processed_") and filename.endswith(".csv"):
            input_path = os.path.join(OUTPUT_DIR, filename)
            final_filename = f"final_{filename[len('processed_'):]}"  
            output_path = os.path.join(PROCESSED_OUTPUT_DIR, final_filename)
            
            try:
                df_final = process_file(input_path, output_path)

                
                middle_part = filename[len("processed_"):]  
                collection_name = middle_part.split("_events_")[0] 

                print(f"📥 ذخیره دیتای فایل {final_filename} در MongoDB کالکشن: {collection_name}")
                save_df_to_mongo(df_final, collection_name)

            except Exception as e:
                print(f"❌ خطا در ساخت فایل نهایی یا ذخیره در MongoDB برای {filename}: {e}")
                continue

    now = datetime.now()
    yesterday = now - timedelta(days=1)
    formatted_yesterday = yesterday.strftime("%Y/%m/%d")
    print("تاریخ یک روز قبل:", formatted_yesterday)    
    print("-------------------------------------------------------------------------------------------------")
    print("-------------------------------------------------------------------------------------------------")
