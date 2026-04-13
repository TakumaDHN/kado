"""
過去データ一括集計（バックフィル）スクリプト

デプロイ後に一度実行し、既存の device_history から
daily_operation_rate / daily_green_apple_count テーブルを埋める。

使い方:
  cd kado
  python scripts/backfill_aggregates.py            # 履歴のある全日を集計
  python scripts/backfill_aggregates.py --days 30  # 直近30日のみ
"""
import sys
import os
import argparse
import pytz
from datetime import datetime, timedelta, time as dtime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import func
from app.database import engine, SessionLocal, Base
from app.models import (
    DeviceHistory, DeviceRegistration,
    DailyOperationRate, DailyGreenAppleCount,
)

jst = pytz.timezone('Asia/Tokyo')
utc = pytz.UTC


# ── 計算ロジック（app/main.py の _calc_green_minutes / _calc_apples_for_day と同等）──

def calc_green_minutes(db, device_addr, window_start_utc, window_end_utc):
    histories = db.query(DeviceHistory).filter(
        DeviceHistory.device_addr == device_addr,
        DeviceHistory.timestamp >= window_start_utc,
        DeviceHistory.timestamp < window_end_utc
    ).order_by(DeviceHistory.timestamp).all()

    prev = db.query(DeviceHistory).filter(
        DeviceHistory.device_addr == device_addr,
        DeviceHistory.timestamp < window_start_utc
    ).order_by(DeviceHistory.timestamp.desc()).first()

    records = []
    if prev:
        records.append({'timestamp': window_start_utc, 'green': prev.green})
    elif histories:
        records.append({'timestamp': window_start_utc, 'green': False})

    for h in histories:
        records.append({'timestamp': h.timestamp, 'green': h.green})

    if not records:
        return 0.0

    green_minutes = 0.0
    for i, rec in enumerate(records):
        next_ts = records[i + 1]['timestamp'] if i < len(records) - 1 else window_end_utc
        duration = max(0, (next_ts - rec['timestamp']).total_seconds() / 60)
        if rec['green']:
            green_minutes += duration
    return green_minutes


def calc_apples_for_day(db, device_addrs, day_start_jst, day_end_jst):
    daily_apples = 0
    current_hour = day_start_jst

    while current_hour < day_end_jst:
        next_hour = current_hour + timedelta(hours=1)
        total_running = 0
        total_other = 0

        hour_start_utc = current_hour.astimezone(utc).replace(tzinfo=None)
        hour_end_utc = next_hour.astimezone(utc).replace(tzinfo=None)

        for addr in device_addrs:
            histories = db.query(DeviceHistory).filter(
                DeviceHistory.device_addr == addr,
                DeviceHistory.timestamp >= hour_start_utc,
                DeviceHistory.timestamp < hour_end_utc
            ).order_by(DeviceHistory.timestamp).all()

            prev = db.query(DeviceHistory).filter(
                DeviceHistory.device_addr == addr,
                DeviceHistory.timestamp < hour_start_utc
            ).order_by(DeviceHistory.timestamp.desc()).first()

            if not histories and not prev:
                total_other += (hour_end_utc - hour_start_utc).total_seconds() / 60
                continue

            if prev:
                start_status = {
                    'timestamp': hour_start_utc,
                    'green': prev.green, 'yellow': prev.yellow, 'red': prev.red
                }
            elif histories:
                start_status = {
                    'timestamp': hour_start_utc,
                    'green': histories[0].green, 'yellow': histories[0].yellow, 'red': histories[0].red
                }
            else:
                start_status = {
                    'timestamp': hour_start_utc,
                    'green': False, 'yellow': False, 'red': False
                }

            time_records = [start_status]
            for h in histories:
                time_records.append({
                    'timestamp': h.timestamp,
                    'green': h.green, 'yellow': h.yellow, 'red': h.red
                })

            for idx in range(len(time_records)):
                rec = time_records[idx]
                next_ts = time_records[idx + 1]['timestamp'] if idx < len(time_records) - 1 else hour_end_utc
                dur = max(0, (next_ts - rec['timestamp']).total_seconds() / 60)
                if rec['green']:
                    total_running += dur
                else:
                    total_other += dur

        total_min = total_running + total_other
        running_pct = round(total_running / total_min * 100, 1) if total_min > 0 else 0

        if running_pct >= 50:
            daily_apples += 5
        elif running_pct >= 40:
            daily_apples += 3
        elif running_pct >= 35:
            daily_apples += 2
        elif running_pct > 30:
            daily_apples += 1

        current_hour = next_hour

    return daily_apples


# ── メイン処理 ──

def backfill(max_days=None):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 履歴データの最古タイムスタンプを取得
        oldest = db.query(func.min(DeviceHistory.timestamp)).scalar()
        if not oldest:
            print("device_history にデータがありません。処理をスキップします。")
            return

        # UTC naive → JST aware
        oldest_jst = utc.localize(oldest).astimezone(jst)
        now_jst = datetime.now(jst)

        # 営業日の起点（6:00区切り）
        oldest_business = oldest_jst.date()
        today_business = now_jst.date() if now_jst.hour >= 6 else (now_jst - timedelta(days=1)).date()

        if max_days:
            earliest = today_business - timedelta(days=max_days)
            if oldest_business < earliest:
                oldest_business = earliest

        registrations = db.query(DeviceRegistration).filter(
            DeviceRegistration.is_enabled == True
        ).all()

        if not registrations:
            print("DeviceRegistration にデータがありません。")
            return

        all_addrs = [r.device_addr for r in registrations]

        # 設置場所グループ
        location_groups = {}
        for r in registrations:
            loc = r.location or ""
            if loc not in location_groups:
                location_groups[loc] = []
            location_groups[loc].append(r.device_addr)

        # 対象日をリストアップ（当日は除外＝リアルタイム計算に任せる）
        target_date = oldest_business
        dates = []
        while target_date < today_business:
            dates.append(target_date)
            target_date += timedelta(days=1)

        print(f"対象期間: {dates[0]} 〜 {dates[-1]} ({len(dates)}日間)")
        print(f"デバイス数: {len(all_addrs)}台")
        print(f"設置場所: {list(location_groups.keys())}")
        print()

        for i, d in enumerate(dates):
            # 時間ウィンドウ（JST → naive UTC）
            regular_start = jst.localize(datetime.combine(d, dtime(8, 0)))
            regular_end_utc = regular_start.astimezone(utc).replace(tzinfo=None) + timedelta(hours=18)
            overtime_end_utc = regular_start.astimezone(utc).replace(tzinfo=None) + timedelta(hours=21)
            regular_start_utc = regular_start.astimezone(utc).replace(tzinfo=None)

            day_start = jst.localize(datetime.combine(d, dtime(6, 0)))
            day_end = day_start + timedelta(hours=24)

            # ── 稼働率 ──
            for reg in registrations:
                run_r = calc_green_minutes(db, reg.device_addr, regular_start_utc, regular_end_utc)
                run_o = calc_green_minutes(db, reg.device_addr, regular_start_utc, overtime_end_utc)

                existing = db.query(DailyOperationRate).filter(
                    DailyOperationRate.device_addr == reg.device_addr,
                    DailyOperationRate.target_date == d
                ).first()

                if existing:
                    existing.running_minutes_regular = run_r
                    existing.running_minutes_overtime = run_o
                else:
                    db.add(DailyOperationRate(
                        device_addr=reg.device_addr,
                        target_date=d,
                        running_minutes_regular=run_r,
                        window_minutes_regular=1080.0,
                        running_minutes_overtime=run_o,
                        window_minutes_overtime=1260.0,
                    ))

            # ── GREEN APPLE ──
            # 全体
            total_apples = calc_apples_for_day(db, all_addrs, day_start, day_end)
            _upsert_apple(db, d, "", total_apples)

            # 設置場所別
            for loc, addrs in location_groups.items():
                loc_apples = calc_apples_for_day(db, addrs, day_start, day_end)
                _upsert_apple(db, d, loc, loc_apples)

            db.commit()

            # 進捗表示
            rate_r = 0
            rate_o = 0
            if all_addrs:
                rows = db.query(DailyOperationRate).filter(
                    DailyOperationRate.target_date == d
                ).all()
                if rows:
                    sum_r = sum(r.running_minutes_regular for r in rows)
                    sum_o = sum(r.running_minutes_overtime for r in rows)
                    rate_r = round(sum_r / (1080.0 * len(rows)) * 100, 1)
                    rate_o = round(sum_o / (1260.0 * len(rows)) * 100, 1)

            print(f"  [{i+1}/{len(dates)}] {d}  稼働率: 定時内={rate_r}% 含残業={rate_o}%  APPLE: {total_apples}個")

        print()
        print(f"完了! {len(dates)}日分の集計データを生成しました。")

    except Exception as e:
        db.rollback()
        print(f"エラー: {e}")
        raise
    finally:
        db.close()


def _upsert_apple(db, target_date, location, apple_count):
    existing = db.query(DailyGreenAppleCount).filter(
        DailyGreenAppleCount.target_date == target_date,
        DailyGreenAppleCount.location == location
    ).first()
    if existing:
        existing.apple_count = apple_count
    else:
        db.add(DailyGreenAppleCount(
            target_date=target_date,
            location=location,
            apple_count=apple_count,
        ))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="過去データ一括集計（バックフィル）")
    parser.add_argument("--days", type=int, default=None,
                        help="直近N日のみ集計（省略時は履歴のある全日）")
    args = parser.parse_args()

    print("=" * 55)
    print("  日次集計データ バックフィル")
    print("=" * 55)
    backfill(max_days=args.days)
