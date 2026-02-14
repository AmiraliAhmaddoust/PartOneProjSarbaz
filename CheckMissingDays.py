from pymongo import MongoClient
from datetime import datetime, timedelta

# -------------- تنظیمات --------------
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "metrix_revenue"

# بازه تاریخی که می‌خوای چک کنی (به میلادی، فرمت YYYY-MM-DD)
START_DATE_STR = "2025-11-08"
END_DATE_STR   = "2025-11-30"

# -------------- توابع کمکی --------------


def date_range(start_date: datetime, end_date: datetime):
    """تولید همه‌ی روزها بین دو تاریخ (شامل دو سر بازه)."""
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def main():
    # اتصال به مونگو
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    # تبدیل رشته‌های تاریخ به datetime
    start_date = datetime.strptime(START_DATE_STR, "%Y-%m-%d").date()
    end_date = datetime.strptime(END_DATE_STR, "%Y-%m-%d").date()

    # تبدیل بازه به فرمت YYYYMMDD برای مقایسه با miladi_time
    start_ymd = start_date.strftime("%Y%m%d")
    end_ymd = end_date.strftime("%Y%m%d")

    print(f"چک کردن بازه: {START_DATE_STR} تا {END_DATE_STR} (miladi_time بین {start_ymd} و {end_ymd})")
    print("------------------------------------------------------------")

    # گرفتن لیست همه کالکشن‌های دیتابیس متریکس رونیو
    collections = db.list_collection_names()

    # خروجی نهایی: لیست دیکشنری برای ساخت جدول اگر خواستی
    summary_rows = []

    for coll_name in collections:
        coll = db[coll_name]
        print(f"\n📂 کالکشن: {coll_name}")

        # همه miladi_time های موجود در این بازه، به صورت set برای دسترسی سریع
        existing_dates_ymd = set()

        # فقط داکیومنت‌هایی که miladi_time توی بازه هست
        cursor = coll.find(
            {
                "miladi_time": {
                    "$gte": start_ymd,
                    "$lte": end_ymd
                }
            },
            {"miladi_time": 1}  # فقط همین فیلد را برمی‌گردانیم
        )

        for doc in cursor:
            mt = doc.get("miladi_time")
            if mt:
                existing_dates_ymd.add(str(mt))

        missing_days = []

        # پیمایش تمام روزهای بازه و چک کردن نبودنشان
        for d in date_range(start_date, end_date):
            d_ymd = d.strftime("%Y%m%d")
            if d_ymd not in existing_dates_ymd:
                # اگر این روز در اون کالکشن هیچ eventی ندارد
                missing_days.append({
                    "collection": coll_name,
                    "date_iso": d.isoformat(),   # 2025-11-15
                    "miladi_time": d_ymd         # 20251115
                })

        if not missing_days:
            print("✅ برای این کالکشن، در این بازه همه‌ی روزها حداقل یک event دارند.")
        else:
            print("❌ روزهایی که هیچ event ندارند:")
            for md in missing_days:
                print(f"   - {md['date_iso']} (miladi_time={md['miladi_time']})")

        # اضافه کردن به summary کلی
        summary_rows.extend(missing_days)

    # اگر خواستی این summary_rows را تبدیل به CSV یا DataFrame کنی:
    try:
        import pandas as pd
        if summary_rows:
            df = pd.DataFrame(summary_rows)
            df.to_csv("missing_days_summary.csv", index=False, encoding="utf-8-sig")
            print("\n📁 فایل 'missing_days_summary.csv' ساخته شد (خلاصه روزهای خالی برای همه کالکشن‌ها).")
        else:
            print("\n✅ هیچ روز خالی‌ای در هیچ کالکشنی برای این بازه یافت نشد.")
    except ImportError:
        print("\n(pandas نصب نیست؛ اگر خواستی خروجی CSV بگیری `pip install pandas` بزن.)")

    client.close()


if __name__ == "__main__":
    main()
