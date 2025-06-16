import os
import pandas as pd
import uuid
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from pytz import timezone

from app.database import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

report_status = {}

def trigger_report_generation():
    report_id = str(uuid.uuid4())
    report_status[report_id] = "Running"
    logger.info(f"[{report_id}] Report generation started.")

    try:
        logger.info(f"[{report_id}] Fetching data from MongoDB...")
        status_df = pd.DataFrame(list(db.store_status.find()))
        bh_df = pd.DataFrame(list(db.business_hours.find()))
        tz_df = pd.DataFrame(list(db.store_timezones.find()))
        logger.info(f"[{report_id}] Data fetched. {len(status_df)} status rows.")

        for df in [status_df, bh_df, tz_df]:
            df['store_id'] = df['store_id'].apply(
                lambda x: x.hex() if isinstance(x, (bytes, bytearray)) else str(x)
            )

        status_df['timestamp_utc'] = pd.to_datetime(status_df['timestamp_utc'], utc=True)
        now_utc = status_df['timestamp_utc'].max()
        logger.info(f"[{report_id}] Latest timestamp in data: {now_utc}")

        business_hours = defaultdict(lambda: {i: [("00:00", "23:59")] for i in range(7)})
        for _, row in bh_df.iterrows():
            business_hours[row['store_id']][row['dayOfWeek']] = [
                (row['start_time_local'], row['end_time_local'])
            ]

        tz_map = defaultdict(lambda: "America/Chicago")
        for _, row in tz_df.iterrows():
            tz_map[row['store_id']] = row['timezone_str']

        result_rows = []

        store_ids = status_df['store_id'].unique()[:10]

        for store_id in store_ids:
            start_time = datetime.now()
            logger.info(f"[{report_id}] Processing store: {store_id}")

            try:
                store_data = status_df[status_df['store_id'] == store_id].copy()
                store_data = store_data.sort_values('timestamp_utc')

                tz = timezone(tz_map[store_id])
                store_data['timestamp_local'] = store_data['timestamp_utc'].dt.tz_convert(tz)

                store_data['status_bin'] = store_data['status'].apply(lambda x: 1 if x == 'active' else 0)

                store_data.set_index('timestamp_local', inplace=True)
                store_data = store_data.resample('1min').ffill().reset_index()

                store_data['dayOfWeek'] = store_data['timestamp_local'].dt.dayofweek
                store_data['time'] = store_data['timestamp_local'].dt.strftime('%H:%M')

                def is_within_business_hours(row):
                    hours = business_hours[store_id][row['dayOfWeek']]
                    return any(start <= row['time'] <= end for start, end in hours)

                store_data = store_data[store_data.apply(is_within_business_hours, axis=1)]

                one_hour_ago = now_utc - timedelta(hours=1)
                one_day_ago = now_utc - timedelta(days=1)
                one_week_ago = now_utc - timedelta(days=7)

                def calc_metrics(df, from_time):
                    filtered = df[df['timestamp_local'] >= from_time]
                    up_minutes = filtered['status_bin'].sum()
                    total_minutes = len(filtered)
                    down_minutes = total_minutes - up_minutes
                    return up_minutes, down_minutes

                one_hour_up, one_hour_down = calc_metrics(store_data, one_hour_ago)
                one_day_up, one_day_down = calc_metrics(store_data, one_day_ago)
                one_week_up, one_week_down = calc_metrics(store_data, one_week_ago)

                result_rows.append({
                    "store_id": store_id,
                    "uptime_last_hour(in minutes)": one_hour_up,
                    "uptime_last_day(in hours)": round(one_day_up / 60, 2),
                    "update_last_week(in hours)": round(one_week_up / 60, 2),
                    "downtime_last_hour(in minutes)": one_hour_down,
                    "downtime_last_day(in hours)": round(one_day_down / 60, 2),
                    "downtime_last_week(in hours)": round(one_week_down / 60, 2),
                })

                elapsed = (datetime.now() - start_time).total_seconds()
                logger.info(f"[{report_id}] Finished store: {store_id} in {elapsed:.2f}s")

            except Exception:
                logger.exception(f"[{report_id}] Error processing store {store_id}")
                continue

        logger.info(f"[{report_id}] Finished processing all stores.")

        result_df = pd.DataFrame(result_rows)
        filename = f"report_{report_id}.csv"
        filepath = os.path.join("reports", filename)
        os.makedirs("reports", exist_ok=True)
        result_df.to_csv(filepath, index=False)
        logger.info(f"[{report_id}] Report written to {filepath}")

        db.reports.insert_one({
            "report_id": report_id,
            "status": "Complete",
            "filename": filename,
            "generated_at": datetime.utcnow()
        })

        report_status[report_id] = "Complete"
        logger.info(f"[{report_id}] Report generation complete.")

    except Exception:
        logger.exception(f"[{report_id}] Error generating report")
        report_status[report_id] = "Failed"

    return report_id
