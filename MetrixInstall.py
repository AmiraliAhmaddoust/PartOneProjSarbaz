import requests
import time
import pandas as pd
import jdatetime
from datetime import datetime, timedelta
import os
import glob
import sys
from pymongo import MongoClient  # 👈 برای اتصال به MongoDB

# ------------------ تنظیمات ------------------

# بهتره یوزرنیم/پسورد رو از متغیر محیطی بخونی (یا مستقیم بنویسی)
USERNAME = os.getenv('METRIX_USERNAME', '')   # نام کاربری متریکس
PASSWORD = os.getenv('METRIX_PASSWORD', '')   # رمز عبور متریکس

DIMENSIONS = ['network', 'campaign', 'adGroup', 'creative', 'subId', 'installSource', 'reinstalled']  # فیلدهای خروجی
END_DATE = int(time.time() * 1000)
START_DATE = END_DATE - (24 * 60 * 60 * 1000)

OUTPUT_FOLDER = r'C:\Users\digiton\Desktop\FinallWriteAdNetwork\metrixInstall\output'  # پوشه خروجی برای ذخیره فایل‌ها

# تنظیمات MongoDB
MONGO_URI = "mongodb://localhost:27017"  # 👈 آدرس MongoDB (در صورت نیاز عوض کن)
MONGO_DB_NAME = "metrix_installations"   # 👈 اسم دیتابیس

print(f"start = {START_DATE}")
print(f"end = {END_DATE}")

# لیست پکیج‌نیم‌ها
PACKAGE_NAMES = [


]

log_file = open(r"C:\Users\digiton\Desktop\logs\MetrixInstallLog.txt", "a", encoding="utf-8")
sys.stdout = log_file
sys.stderr = log_file

# ------------------ ایجاد پوشه خروجی ------------------

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)
    print(f"✅ پوشه {OUTPUT_FOLDER} ایجاد شد.")

# ------------------ حذف فایل‌های CSV قدیمی ------------------

def clear_csv_files(folder):
    csv_files = glob.glob(os.path.join(folder, "*.csv"))
    for file in csv_files:
        try:
            os.remove(file)
            print(f"🗑️ فایل {file} حذف شد.")
        except Exception as e:
            print(f"❌ خطا در حذف فایل {file}: {e}")

# ------------------ اتصال به MongoDB ------------------

def get_mongo_collection(collection_name):
    """
    گرفتن کالکشن MongoDB بر اساس نام.
    هر فایل نهایی یک کالکشن جدا خواهد داشت.
    """
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB_NAME]
    return db[collection_name]

def save_df_to_mongo(df, collection_name):
    """
    ذخیره دیتافریم در MongoDB.
    هر بار که این تابع صدا زده بشه، رکوردهای جدید به کالکشن اضافه می‌شن.
    """
    try:
        collection = get_mongo_collection(collection_name)
        records = df.to_dict(orient='records')
        if not records:
            print(f"⚠️ دیتافریم خالی است، چیزی در MongoDB ذخیره نشد. کالکشن: {collection_name}")
            return
        result = collection.insert_many(records)
        print(f"✅ {len(result.inserted_ids)} رکورد در کالکشن '{collection_name}' درج شد.")
    except Exception as e:
        print(f"❌ خطا در ذخیره دیتا در MongoDB برای کالکشن {collection_name}: {e}")

# ------------------ ۱. دریافت توکن ------------------

def get_token(username, password):
    url = "https://web.metrix.ir/oauth/token"
    headers = {
        "authorization": "Basic bWV0cml4X2Rhc2hib2FyZDpZSTc1TU1FMlJS"
    }
    data = {
        "grant_type": "password",
        "username": username,
        "password": password
    }
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response.json()['access_token']
    except Exception as e:
        print(f"❌ خطا در دریافت توکن: {e}")
        raise

# ------------------ ۲. ارسال درخواست export نصب‌ها ------------------

def request_installation_export(token, package_name):
    url = f"https://web.metrix.ir/v2/apps/{package_name}/export/sessions?lang=en"
    headers = {
        "authorization": f"bearer {token}",
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json"
    }
    payload = {
        "startDate": START_DATE,
        "endDate": END_DATE,
        "requestType": "INSTALL_RAW_DATA",
        "dimensions": DIMENSIONS,
        "conditions": {}
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["taskId"]
    except Exception as e:
        print(f"❌ خطا در ارسال درخواست برای {package_name}: {e}")
        raise

# ------------------ ۳. بررسی وضعیت ------------------

def check_status(token, task_id, package_name):
    url = f"https://web.metrix.ir/v2/apps/{package_name}/export/status/{task_id}"
    headers = {
        "authorization": f"bearer {token}",
        "accept": "application/json, text/plain, */*"
    }

    while True:
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            result = response.json()
            status = result.get('status')

            print(f"Task status for {package_name}: {status}")
            if status == 'PROCESSED':
                url = result.get('url')
                if isinstance(url, list):
                    return url
                return [url]
            elif status == 'ERROR':
                raise Exception(f"Export task failed for {package_name}.")
            time.sleep(10)
        except Exception as e:
            print(f"❌ خطا در بررسی وضعیت برای {package_name}: {e}")
            raise

# ------------------ ۴. تبدیل تاریخ شمسی به میلادی ------------------

def shamsi_to_miladi(shamsi_date_str):
    try:
        if pd.isna(shamsi_date_str) or not isinstance(shamsi_date_str, str):
            print(f"❌ مقدار نامعتبر برای تاریخ: {shamsi_date_str}")
            return None

        date_only = shamsi_date_str.split(" ")[0]
        shamsi_date = jdatetime.datetime.strptime(date_only, '%Y-%m-%d')
        miladi_date = shamsi_date.togregorian()
        return miladi_date.strftime('%Y%m%d')
    except Exception as e:
        print(f"❌ خطا در تبدیل تاریخ {shamsi_date_str}: {e}")
        return None

# ------------------ ۵. پردازش فایل‌های CSV خام متریکس ------------------

def process_csv_files(urls, package_name):
    if not isinstance(urls, list):
        urls = [urls]
    
    for i, url in enumerate(urls):
        file_name = os.path.join(OUTPUT_FOLDER, f"installation_export_{package_name}.csv")
        print(f"📊 پردازش فایل {file_name}...")

        try:
            if not isinstance(url, str):
                print(f"❌ URL نامعتبر برای {package_name}: {url}")
                continue

            download = requests.get(url)
            download.raise_for_status()
            with open(file_name, 'wb') as f:
                f.write(download.content)
            print(f"✅ ذخیره شد: {file_name}")

            df = pd.read_csv(file_name)
            if df.empty:
                print(f"❌ فایل {file_name} خالی است.")
                continue

            print(f"ستون‌های فایل CSV: {list(df.columns)}")
            df.columns = df.columns.str.replace(' ', '_', regex=False)
            print(f"ستون‌های بعد از تغییر نام: {list(df.columns)}")

            if 'First_Install_Time' not in df.columns or 'Time' not in df.columns:
                print(f"❌ ستون‌های مورد انتظار ('First_Install_Time', 'Time') در فایل {file_name} یافت نشد.")
                continue

            print(f"نمونه تاریخ‌ها در ستون First_Install_Time: {df['First_Install_Time'].head().tolist()}")
            print(f"نمونه تاریخ‌ها در ستون Time: {df['Time'].head().tolist()}")

            invalid_rows = df[df['First_Install_Time'].isna() | df['Time'].isna()]
            if not invalid_rows.empty:
                
                print(f"⚠️ {len(invalid_rows)} ردیف با تاریخ نامعتبر در پکیج {package_name} وجود دارد (نادیده گرفته شد).")
            
            df = df[~(df['First_Install_Time'].isna() | df['Time'].isna())]

            df['miladi_first_install_time'] = df['First_Install_Time'].apply(shamsi_to_miladi)
            df['miladi_time'] = df['Time'].apply(shamsi_to_miladi)

            new_file_name = os.path.join(OUTPUT_FOLDER, f"processed_{package_name}.csv")
            df.to_csv(new_file_name, index=False, encoding='utf-8')
            print(f"✅ فایل پردازش‌شده ذخیره شد: {new_file_name}")
            os.remove(file_name)
            print(f"🗑️ فایل قدیمی حذف شد: {file_name}")
        except Exception as e:
            print(f"❌ خطا در پردازش فایل {file_name}: {e}")
            continue

# ------------------ ۶. پردازش فایل‌های نهایی (تجمیع و شمارش) ------------------

def process_file(file_path, output_path):
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    elif file_path.endswith('.xlsx'):
        df = pd.read_excel(file_path)
    else:
        raise ValueError("فایل باید CSV یا Excel باشد")
    
    unique_key = ['Network', 'Campaign', 'Ad_Group', 'Creative', 'Sub_Id', 'Reinstalled', 'Install_Source']
    df['Unique_Combination'] = df[unique_key].astype(str).agg('-'.join, axis=1)
    
    counts = df['Unique_Combination'].value_counts().reset_index()
    counts.columns = ['Unique_Combination', 'Total_Install']
    
    df = df.drop_duplicates(subset=unique_key).merge(counts, on='Unique_Combination', how='left')
    
    df = df[unique_key + ['Total_Install']]
    df.columns = df.columns.str.replace(' ', '_', regex=False)
    yesterday = (datetime.today() - timedelta(days=1)).strftime('%Y%m%d')
    df['Date'] = yesterday
    
    if output_path.endswith('.csv'):
        df.to_csv(output_path, index=False)
    else:
        df.to_excel(output_path, index=False)
    
    print(f'فایل پردازش شده ذخیره شد در: {output_path}')
    return df

# ------------------ ۷. حذف فایل‌های قدیمی در پوشه خروجی نهایی ------------------

def clear_csv_files1(folder):
    csv_files = glob.glob(os.path.join(folder, "*.csv"))
    for file in csv_files:
        try:
            os.remove(file)
            print(f"🗑️ فایل {file} حذف شد.")
        except Exception as e:
            print(f"❌ خطا در حذف فایل {file}: {e}")

# ------------------ اجرای اصلی ------------------

if __name__ == "__main__":
    print(f"🗑️ حذف فایل‌های CSV قدیمی در پوشه {OUTPUT_FOLDER}...")
    clear_csv_files(OUTPUT_FOLDER)

    print("🔑 در حال دریافت توکن...")
    access_token = get_token(USERNAME, PASSWORD)

    for package_name in PACKAGE_NAMES:
        print(f"\n📦 پردازش پکیج: {package_name}")
        try:
            print("📤 ارسال درخواست نصب‌ها...")
            task_id = request_installation_export(access_token, package_name)
            print(f"🆔 Task ID: {task_id}")

            print("⏳ بررسی وضعیت آماده‌سازی فایل...")
            urls = check_status(access_token, task_id, package_name)

            print("✅ فایل آماده شد! لینک‌های دانلود:")
            for url in urls:
                print(url)

            process_csv_files(urls, package_name)
        except Exception as e:
            print(f"❌ خطا در پردازش پکیج {package_name}: {e}")
            continue

    now = datetime.now()
    yesterday = now - timedelta(days=1)
    formatted_yesterday = yesterday.strftime("%Y/%m/%d")

    folder_path = r"C:\Users\digiton\Desktop\FinallWriteAdNetwork\metrixInstall\output"
    output_path = r"C:\Users\digiton\Desktop\FinallWriteAdNetwork\metrixInstall\output\processed"

    print(f"🗑️ حذف فایل‌های CSV قدیمی در پوشه {output_path}...")
    clear_csv_files1(output_path)

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # جابه‌جا و rename کردن فایل‌های processed_
    for filename in os.listdir(folder_path):
        if filename.endswith(".csv"):
            if "matdgf4" in filename:
                new_name = "Golmorad.csv"
            else:
                new_name = filename.replace("processed_", "")

            old_file = os.path.join(folder_path, filename)
            new_file = os.path.join(output_path, new_name)

            if os.path.exists(new_file) and old_file != new_file:
                print(f"فایل {new_name} از قبل وجود دارد. تغییر نام انجام نشد برای {filename}.")
                continue
            try:
                os.rename(old_file, new_file)
                print(f"نام فایل از {filename} به {new_name} تغییر کرد.")
            except FileExistsError:
                print(f"خطا: فایل {new_name} از قبل وجود دارد. تغییر نام انجام نشد برای {filename}.")

    # پردازش نهایی و ذخیره در MongoDB
    for filename in os.listdir(output_path):
        if filename.endswith(".csv"):
            file_path = os.path.join(output_path, filename)
            output_file = os.path.join(output_path, f"final_{filename}")
            try:
                df_final = process_file(file_path, output_file)

                # تعیین نام کالکشن بر اساس اسم فایل
                base_name = os.path.splitext(os.path.basename(output_file))[0]  # مثلا final_Golmorad
                if base_name.startswith("final_"):
                    collection_name = base_name[len("final_"):]  # Golmorad
                else:
                    collection_name = base_name

                print(f"📥 ذخیره دیتای فایل {output_file} در MongoDB کالکشن: {collection_name}")
                save_df_to_mongo(df_final, collection_name)

            except Exception as e:
                print(f"❌ خطا در پردازش فایل {file_path}: {e}")
                continue

    print("تغییر نام و پردازش فایل‌ها با موفقیت انجام شد!")
    print("تاریخ یک روز قبل:", formatted_yesterday)
    print("-------------------------------------------------------------------------------------------------")
    print("-------------------------------------------------------------------------------------------------")
