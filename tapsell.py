import requests
import json
from datetime import datetime, timedelta
import time
import pandas as pd
import sys
import subprocess
import os
from pymongo import MongoClient  # برای MongoDB

# --------------------- تنظیمات MongoDB ---------------------
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "costs"
COLLECTION_NAME = "campaigns"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]
# -----------------------------------------------------------

# اتصال log
log_file = open("C:/Users/digiton/Desktop/logs/Tapsell.txt", "a", encoding="utf-8")
sys.stdout = log_file
sys.stderr = log_file

# حذف CSV های قدیمی
output_dir = r"C:\Users\digiton\Desktop\FinallWriteAdNetwork\Tapsell"
if os.path.exists(output_dir):
    for file in os.listdir(output_dir):
        if file.endswith(".csv"):
            try:
                os.remove(os.path.join(output_dir, file))
                print(f"Deleted CSV file: {file}")
            except:
                pass
    print("✅ All CSV files deleted.")
else:
    print("❌ Output directory not found.")

# مسیر API
login_url = "https://sso-api.tapsell.ir/user/api/login"
campaign_list_url = "https://webapi-v2.tapsell.ir/web/tabligh-dahande/campaign/"

# لیست اکانت‌ها
accounts = [
    {"username": "#", "password": "#"},
    {"username": "#", "password": "#"},
    {"username": "#", "password": "#"},
    {"username": "#", "password": "#"}
    #برای حفظ دیتاهای اکانتهای شرکت و بخاطر 
    # NDA
    #  امضا شده اسم و رمز اکانتها با # جایگزین شد 
]




login_headers = {"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"}

# محاسبه بازه زمانی
end_date = datetime.now()
start_date = end_date - timedelta(hours=24)
start_timestamp = int(start_date.timestamp() * 1000)
end_timestamp = int(end_date.timestamp() * 1000)
yesterday = end_date - timedelta(days=1)

print(f"بازه: {start_date} تا {end_date}")

all_accounts_campaigns = []

# --------------------- پردازش هر اکانت ---------------------
for account in accounts:
    username = account["username"]
    password = account["password"]

    print(f"\n=== login: {username} ===")

    login_data = {"username": username, "password": password}
    response = requests.post(login_url, headers=login_headers, data=login_data)

    if response.status_code != 200:
        print(f"Login error: {username}")
        continue

    token = response.json().get("access_token")
    if not token:
        print(f"Token not found: {username}")
        continue

    campaign_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    page_index = 0
    page_size = 100
    has_more = True
    account_campaigns = []

    while has_more:
        payload = {
            "startDate": start_timestamp,
            "endDate": end_timestamp,
            "interval": "daily",
            "pageIndex": page_index,
            "pageSize": page_size,
            "sortReversed": True,
            "sortField": "creationDate",
        }

        response = requests.post(campaign_list_url, headers=campaign_headers, data=json.dumps(payload))
        if response.status_code != 200:
            break

        data = response.json()
        campaigns = data.get("ctas", [])

        if not campaigns:
            break

        # --------------------- فیلتر دقیق cost ---------------------
        for c in campaigns:
            raw_cost = c.get("totalAdvertiserCost", 0)

            try:
                cost = float(raw_cost)
            except:
                cost = 0

            if cost > 0:   # فقط هزینه غیر صفر و عددی
                account_campaigns.append({
                    "campaign_name": c.get("title"),
                    "campaign_date": yesterday.strftime("%Y-%m-%d"),
                    "cost": cost,
                    "account_name": username,
                    "source": "tapsell"
                })
        # ------------------------------------------

        total_items = data.get("totalCount", 0)
        page_index += 1

        if page_index * page_size >= total_items:
            break

        time.sleep(1)

    all_accounts_campaigns.extend(account_campaigns)
    print(f"{len(account_campaigns)} campaign collected for {username}")

# --------------------- تبدیل به DataFrame ---------------------
df = pd.DataFrame(all_accounts_campaigns)

if df.empty:
    print("❗ No data to insert.")
else:
    df["cost"] = pd.to_numeric(df["cost"], errors="coerce")
    df = df[(df["cost"].notna()) & (df["cost"] > 0)]

    # افزودن زمان ذخیره
    records = df.to_dict("records")
    for r in records:
        r["inserted_at"] = datetime.utcnow()

    # --------------------- درج در MongoDB ---------------------
    result = collection.insert_many(records)
    print(f"\n✅ Inserted {len(result.inserted_ids)} Tapsell records into MongoDB.")

    # ذخیره CSV
    output_file = r"C:\Users\digiton\Desktop\FinallWriteAdNetwork\Tapsell\tapsell_campaigns_filtered_nonzero.csv"
    df_csv = df.copy()
    df_csv.to_csv(output_file, index=False, encoding="utf-8")
    print(f"CSV saved: {output_file}")
print("-------------- DONE --------------")

# بستن کانکشن‌ها
client.close()


log_file.close()

