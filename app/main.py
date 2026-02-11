"""
ライトタワー監視システム - FastAPIメインアプリケーション
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import json
import asyncio
import re
import pytz
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .database import engine, get_db, Base
from .models import DeviceStatus, DeviceHistory, DeviceRegistration
from .mqtt_client import MQTTClient
from .device_config import REGISTERED_DEVICES, get_device_name, get_device_info, get_all_devices_from_db, get_device_info_from_db
from .utils import validate_mac_address, get_status_from_lights

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPIアプリ作成
app = FastAPI(
    title="ライトタワー監視システム",
    description="ESP32ベースのライトタワーゲートウェイシステムのリアルタイム監視",
    version="1.0.0"
)

# 静的ファイルとテンプレート
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# WebSocket接続マネージャー
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket接続: {len(self.active_connections)}台のクライアント")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket切断: {len(self.active_connections)}台のクライアント")

    async def broadcast(self, message: dict):
        """全クライアントにメッセージを配信"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"メッセージ送信エラー: {e}")


manager = ConnectionManager()
mqtt_client = None
scheduler = None

# デバイスごとの処理ロック（重複防止用）
device_locks = {}


async def reset_all_devices_to_idle():
    """
    毎日6:00に全デバイスを休止状態（Not Working）にリセット
    次のMQTTデータ受信まで休止状態を維持
    """
    try:
        db = next(get_db())
        jst = pytz.timezone('Asia/Tokyo')
        utc = pytz.UTC
        current_time_jst = datetime.now(jst)

        # 今日の6:00 JSTを計算
        today_6am_jst = jst.localize(datetime.combine(current_time_jst.date(), datetime.min.time())).replace(hour=6)

        logger.info(f"=== 6:00 デバイス休止処理開始 ({current_time_jst.strftime('%Y-%m-%d %H:%M:%S JST')}) ===")

        # 全デバイスを取得
        all_devices = db.query(DeviceStatus).all()
        reset_count = 0

        for device in all_devices:
            # デバイス情報を取得
            device_info = get_device_info_from_db(db, device.device_addr)
            device_name = device_info.get("name", "Unknown") if device_info else "Unknown"

            # 現在の状態を保存
            old_status = device.status_text
            old_red = device.red
            old_yellow = device.yellow
            old_green = device.green

            # ライト状態が変わるかチェック
            status_changed = (old_red != False or old_yellow != False or old_green != False)

            # 休止状態にリセット
            device.status_code = "00"
            device.status_text = "Not Working"
            device.red = False
            device.yellow = False
            device.green = False
            device.last_update = datetime.utcnow()
            # is_activeはそのまま維持（オフラインにするわけではない）
            # batteryもそのまま維持

            # ライト状態が変わった場合のみ履歴に記録
            if status_changed:
                # 重複防止: 今日の6:00前後1分以内に同じ状態のデータが既に存在するかチェック
                today_6am_utc = today_6am_jst.astimezone(utc).replace(tzinfo=None)
                existing_reset = db.query(DeviceHistory).filter(
                    DeviceHistory.device_addr == device.device_addr,
                    DeviceHistory.timestamp >= today_6am_utc - timedelta(minutes=1),
                    DeviceHistory.timestamp < today_6am_utc + timedelta(minutes=1),
                    DeviceHistory.status_code == "00",
                    DeviceHistory.red == False,
                    DeviceHistory.yellow == False,
                    DeviceHistory.green == False
                ).first()

                if not existing_reset:
                    history_entry = DeviceHistory(
                        device_id=device.device_id,
                        device_addr=device.device_addr,
                        battery=device.battery,
                        red=False,
                        yellow=False,
                        green=False,
                        status_code="00",
                        status_text="Not Working",
                        timestamp=datetime.utcnow()
                    )
                    db.add(history_entry)
                    logger.info(f"  - {device_name} ({device.device_addr}): {old_status} → Not Working (履歴記録)")
                    reset_count += 1
                else:
                    logger.info(f"  - {device_name} ({device.device_addr}): 6:00リセットデータ既存（スキップ）")
            else:
                logger.info(f"  - {device_name} ({device.device_addr}): すでに Not Working (変更なし)")

            # WebSocketで各デバイスの更新を配信
            try:
                await manager.broadcast({
                    "type": "device_update",
                    "device_id": device.device_id,
                    "device_addr": device.device_addr,
                    "device_name": device_name,
                    "location": device_info.get("location", "") if device_info else "",
                    "battery": device.battery,
                    "red": False,
                    "yellow": False,
                    "green": False,
                    "status_code": "00",
                    "status_text": "Not Working",
                    "is_active": device.is_active,
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error(f"WebSocket配信エラー: {e}")

        db.commit()
        logger.info(f"=== 休止処理完了: {reset_count}台のデバイスをリセットしました ===")

    except Exception as e:
        logger.error(f"デバイス休止処理エラー: {e}")
        if db:
            db.rollback()
    finally:
        if db:
            db.close()


# データベース初期化
@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の処理"""
    global mqtt_client, scheduler

    # データベーステーブルを作成
    Base.metadata.create_all(bind=engine)
    logger.info("データベースを初期化しました")

    # 登録済みデバイスを初期化
    initialize_devices()

    # MQTTクライアントを開始
    loop = asyncio.get_event_loop()
    mqtt_client = MQTTClient(on_message_callback=handle_mqtt_message, event_loop=loop)
    mqtt_client.start()
    logger.info("MQTTクライアントを起動しました")

    # スケジューラーを起動（毎日6:00 JSTに全デバイスをリセット）
    scheduler = AsyncIOScheduler(timezone=pytz.timezone('Asia/Tokyo'))
    scheduler.add_job(
        reset_all_devices_to_idle,
        CronTrigger(hour=6, minute=0),  # 毎日6:00 JST
        id='reset_devices_daily',
        name='毎日6:00にデバイスを休止状態にリセット',
        replace_existing=True
    )
    scheduler.start()
    logger.info("スケジューラーを起動しました - 毎日6:00 JSTに全デバイスを休止状態にリセット")


def initialize_devices():
    """登録済みデバイスをデータベースに初期化"""
    db = next(get_db())
    try:
        # ステップ1: REGISTERED_DEVICESをDeviceRegistrationテーブルに移行（初回のみ）
        for mac_addr, info in REGISTERED_DEVICES.items():
            existing_reg = db.query(DeviceRegistration).filter(
                DeviceRegistration.device_addr == mac_addr
            ).first()

            if not existing_reg:
                # デバイス登録情報を作成
                new_registration = DeviceRegistration(
                    device_addr=mac_addr,
                    name=info["name"],
                    location=info["location"],
                    description=info["description"],
                    index=info["index"],
                    is_enabled=True
                )
                db.add(new_registration)
                logger.info(f"デバイス登録情報を追加: {info['name']} ({mac_addr})")

        db.commit()

        # ステップ2: DeviceStatusテーブルを初期化
        all_devices = get_all_devices_from_db(db)
        for mac_addr, info in all_devices.items():
            # 既存のデバイスを確認
            existing_status = db.query(DeviceStatus).filter(
                DeviceStatus.device_addr == mac_addr
            ).first()

            if not existing_status:
                # 新規デバイスを作成（オフライン状態で初期化）
                device_id = int(mac_addr[-4:], 16)
                new_device = DeviceStatus(
                    device_id=device_id,
                    device_addr=mac_addr,
                    gateway_id="JP0000000001",
                    battery=0.0,
                    red=False,
                    yellow=False,
                    green=False,
                    status_code="00",
                    status_text="Not Working",
                    is_active=False  # 初期状態はオフライン
                )
                db.add(new_device)
                logger.info(f"デバイスステータスを初期化: {info['name']} ({mac_addr})")

        db.commit()
        logger.info(f"全{len(all_devices)}台のデバイスを初期化しました")
    except Exception as e:
        logger.error(f"デバイス初期化エラー: {e}")
        db.rollback()
    finally:
        db.close()


@app.on_event("shutdown")
async def shutdown_event():
    """アプリケーション終了時の処理"""
    global mqtt_client, scheduler
    if mqtt_client:
        mqtt_client.stop()
        logger.info("MQTTクライアントを停止しました")
    if scheduler:
        scheduler.shutdown()
        logger.info("スケジューラーを停止しました")


async def handle_mqtt_message(data: dict):
    """
    MQTTメッセージ受信時の処理
    - データベースに保存
    - WebSocketクライアントに配信
    """
    device_addr = data.get("device_addr", "Unknown")

    # デバイスごとのロックを取得または作成
    if device_addr not in device_locks:
        device_locks[device_addr] = asyncio.Lock()

    # ロックを取得して、同じデバイスの処理が同時に実行されないようにする
    async with device_locks[device_addr]:
        db = None
        try:
            db = next(get_db())

            device_id = data.get("device_id")
            gateway_id = data.get("gateway_id", "Unknown")
            battery = data.get("battery", 0)
            red = data.get("red", False)
            yellow = data.get("yellow", False)
            green = data.get("green", False)
            status_code = data.get("status_code", "00")
            status_text = data.get("status_text", "Unknown")

            # その日の6:00のリセットデータが存在しない場合は追加
            jst = pytz.timezone('Asia/Tokyo')
            utc = pytz.UTC
            now_jst = datetime.now(jst)
            today_6am_jst = jst.localize(datetime.combine(now_jst.date(), datetime.min.time())).replace(hour=6)

            # 6:00より前の場合は前日の6:00を対象とする
            if now_jst.hour < 6:
                today_6am_jst = today_6am_jst - timedelta(days=1)

            today_6am_utc = today_6am_jst.astimezone(utc).replace(tzinfo=None)

            # その日の6:00のデータが存在するかチェック
            existing_6am = db.query(DeviceHistory).filter(
                DeviceHistory.device_addr == device_addr,
                DeviceHistory.timestamp == today_6am_utc
            ).first()

            # 6:00のデータがなければ追加
            if not existing_6am:
                reset_history = DeviceHistory(
                    device_id=device_id,
                    device_addr=device_addr,
                    battery=100.0,
                    red=False,
                    yellow=False,
                    green=False,
                    status_code="00",
                    status_text="Not Working",
                    timestamp=today_6am_utc
                )
                db.add(reset_history)
                db.commit()
                logger.info(f"[6:00リセット追加] デバイス {device_addr}: その日の最初の信号受信時に6:00の休止状態を記録")

            # 現在のステータスを更新または作成（MACアドレスで検索）
            status = db.query(DeviceStatus).filter(DeviceStatus.device_addr == device_addr).first()

            # ライト状態が変わったかどうかを判定
            status_changed = False

            if status:
                # 既存のステータスと比較（ライトの状態のみ）
                if status.red != red or status.yellow != yellow or status.green != green:
                    status_changed = True
                    logger.info(f"デバイス {device_addr}: ライト状態変更 "
                               f"(R:{status.red}->{red}, Y:{status.yellow}->{yellow}, G:{status.green}->{green})")

                # ステータスを更新
                status.device_id = device_id
                status.gateway_id = gateway_id
                status.battery = battery
                status.red = red
                status.yellow = yellow
                status.green = green
                status.status_code = status_code
                status.status_text = status_text
                status.last_update = datetime.utcnow()
                status.is_active = True  # データ受信したのでアクティブに
            else:
                # 新規デバイスの場合は履歴に記録
                status_changed = True
                status = DeviceStatus(
                    device_id=device_id,
                    device_addr=device_addr,
                    gateway_id=gateway_id,
                    battery=battery,
                    red=red,
                    yellow=yellow,
                    green=green,
                    status_code=status_code,
                    status_text=status_text
                )
                db.add(status)

            # DeviceStatusを先にコミット
            db.commit()

            # ライト状態が変わった場合のみ履歴に追加
            if status_changed:
                # 新しいトランザクションで重複チェックと追加を実行
                # 重複防止: 直近1秒以内に同じライト状態のレコードがないか確認
                one_second_ago = datetime.utcnow() - timedelta(seconds=1)
                recent_duplicate = db.query(DeviceHistory).filter(
                    DeviceHistory.device_addr == device_addr,
                    DeviceHistory.timestamp > one_second_ago,
                    DeviceHistory.red == red,
                    DeviceHistory.yellow == yellow,
                    DeviceHistory.green == green
                ).first()

                if recent_duplicate:
                    logger.warning(f"[重複スキップ] デバイス {device_addr}: 1秒以内に同じ状態が記録済み")
                else:
                    try:
                        history = DeviceHistory(
                            device_id=device_id,
                            device_addr=device_addr,
                            battery=battery,
                            red=red,
                            yellow=yellow,
                            green=green,
                            status_code=status_code,
                            status_text=status_text
                        )
                        db.add(history)
                        db.commit()
                        logger.info(f"[履歴追加] デバイス {device_addr} ({status_text}) R:{red} Y:{yellow} G:{green}")
                    except Exception as e:
                        logger.error(f"[履歴追加エラー] デバイス {device_addr}: {e}")
                        db.rollback()
            else:
                logger.debug(f"[変更なし] デバイス {device_addr} ({status_text}) - 履歴には記録しません")

            # WebSocketクライアントに配信（設備情報含む）
            device_info = get_device_info_from_db(db, device_addr)
            await manager.broadcast({
                "type": "device_update",
                "device_id": device_id,
                "device_addr": device_addr,
                "device_name": device_info["name"],
                "location": device_info["location"],
                "battery": battery,
                "red": red,
                "yellow": yellow,
                "green": green,
                "status_code": status_code,
                "status_text": status_text,
                "is_active": True,
                "timestamp": datetime.utcnow().isoformat()
            })

        except Exception as e:
            logger.error(f"メッセージ処理エラー: {e}")
            if db:
                db.rollback()
        finally:
            if db:
                db.close()


# ルート - ダッシュボード
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """ダッシュボード画面"""
    return templates.TemplateResponse("index.html", {"request": request})


# API - デバイス一覧
@app.get("/api/devices")
async def get_devices(db: Session = Depends(get_db)):
    """全デバイスの現在のステータスを取得（設備情報含む）"""
    devices = db.query(DeviceStatus).all()

    result = []
    for d in devices:
        device_info = get_device_info_from_db(db, d.device_addr)
        result.append({
            "device_id": d.device_id,
            "device_addr": d.device_addr,
            "device_name": device_info["name"],
            "location": device_info["location"],
            "description": device_info["description"],
            "index": device_info["index"],
            "gateway_id": d.gateway_id,
            "battery": d.battery,
            "red": d.red,
            "yellow": d.yellow,
            "green": d.green,
            "status_code": d.status_code,
            "status_text": d.status_text,
            "last_update": d.last_update.isoformat() if d.last_update else None,
            "is_active": d.is_active
        })

    # indexでソート（設備1号機→7号機の順）
    result.sort(key=lambda x: x["index"])
    return result


# API - デバイス履歴
@app.get("/api/devices/{device_id}/history")
async def get_device_history(
    device_id: int,
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """指定デバイスの履歴を取得"""
    since = datetime.utcnow() - timedelta(hours=hours)
    history = db.query(DeviceHistory).filter(
        DeviceHistory.device_id == device_id,
        DeviceHistory.timestamp >= since
    ).order_by(DeviceHistory.timestamp.desc()).all()

    return [h.to_dict() for h in history]


# WebSocketエンドポイント
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket接続エンドポイント - リアルタイムデータ配信"""
    await manager.connect(websocket)
    try:
        while True:
            # クライアントからのメッセージを待機（接続維持のため）
            data = await websocket.receive_text()
            # Pingメッセージに応答
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ヘルスチェック
@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {
        "status": "ok",
        "mqtt_connected": mqtt_client.connected if mqtt_client else False,
        "websocket_clients": len(manager.active_connections),
        "timestamp": datetime.utcnow().isoformat()
    }


# ========== デバイス管理API ==========

@app.get("/api/devices/config")
async def get_device_config(db: Session = Depends(get_db)):
    """デバイス管理用一覧取得"""
    devices = db.query(DeviceRegistration).order_by(DeviceRegistration.index).all()

    result = []
    for device in devices:
        result.append({
            "device_addr": device.device_addr,
            "name": device.name,
            "location": device.location,
            "description": device.description,
            "index": device.index,
            "is_enabled": device.is_enabled,
            "created_at": device.created_at.isoformat() if device.created_at else None,
            "updated_at": device.updated_at.isoformat() if device.updated_at else None
        })

    return result


@app.post("/api/devices/register")
async def register_device(
    device_addr: str,
    name: str,
    location: str = "",
    description: str = "",
    index: int = 999,
    db: Session = Depends(get_db)
):
    """デバイスを新規登録"""
    # MACアドレスバリデーション
    if not validate_mac_address(device_addr):
        raise HTTPException(
            status_code=400,
            detail="無効なMACアドレスです。12桁の16進数で入力してください（例: ECDA3BBE61E8）"
        )

    # 大文字に統一
    device_addr = device_addr.upper()

    # 重複チェック
    existing = db.query(DeviceRegistration).filter(
        DeviceRegistration.device_addr == device_addr
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="このMACアドレスは既に登録されています")

    try:
        # デバイス登録情報を作成
        new_device = DeviceRegistration(
            device_addr=device_addr,
            name=name,
            location=location,
            description=description,
            index=index,
            is_enabled=True
        )
        db.add(new_device)

        # DeviceStatusも初期化
        device_id = int(device_addr[-4:], 16)
        new_status = DeviceStatus(
            device_id=device_id,
            device_addr=device_addr,
            gateway_id="JP0000000001",
            battery=0.0,
            red=False,
            yellow=False,
            green=False,
            status_code="00",
            status_text="Not Working",
            is_active=False
        )
        db.add(new_status)

        db.commit()
        logger.info(f"新規デバイス登録: {name} ({device_addr})")

        return {
            "status": "success",
            "message": f"デバイス {name} を登録しました"
        }

    except Exception as e:
        db.rollback()
        logger.error(f"デバイス登録エラー: {e}")
        raise HTTPException(status_code=500, detail=f"登録エラー: {str(e)}")


@app.put("/api/devices/{device_addr}")
async def update_device(
    device_addr: str,
    name: str,
    location: str = "",
    description: str = "",
    index: int = 999,
    db: Session = Depends(get_db)
):
    """デバイス情報を編集"""
    device_addr = device_addr.upper()

    device = db.query(DeviceRegistration).filter(
        DeviceRegistration.device_addr == device_addr
    ).first()

    if not device:
        raise HTTPException(status_code=404, detail="デバイスが見つかりません")

    try:
        device.name = name
        device.location = location
        device.description = description
        device.index = index
        device.updated_at = datetime.utcnow()

        db.commit()
        logger.info(f"デバイス更新: {name} ({device_addr})")

        return {
            "status": "success",
            "message": f"デバイス {name} を更新しました"
        }

    except Exception as e:
        db.rollback()
        logger.error(f"デバイス更新エラー: {e}")
        raise HTTPException(status_code=500, detail=f"更新エラー: {str(e)}")


@app.delete("/api/devices/{device_addr}")
async def delete_device(
    device_addr: str,
    db: Session = Depends(get_db)
):
    """デバイスを削除（論理削除）"""
    device_addr = device_addr.upper()

    device = db.query(DeviceRegistration).filter(
        DeviceRegistration.device_addr == device_addr
    ).first()

    if not device:
        raise HTTPException(status_code=404, detail="デバイスが見つかりません")

    try:
        # 論理削除
        device.is_enabled = False
        device.updated_at = datetime.utcnow()

        # DeviceStatusも非アクティブに
        status = db.query(DeviceStatus).filter(
            DeviceStatus.device_addr == device_addr
        ).first()
        if status:
            status.is_active = False

        db.commit()
        logger.info(f"デバイス削除: {device.name} ({device_addr})")

        return {
            "status": "success",
            "message": f"デバイス {device.name} を削除しました"
        }

    except Exception as e:
        db.rollback()
        logger.error(f"デバイス削除エラー: {e}")
        raise HTTPException(status_code=500, detail=f"削除エラー: {str(e)}")


# ========== 稼働状況タイムライン API ==========

@app.get("/api/devices/{device_addr}/timeline")
async def get_device_timeline(
    device_addr: str,
    date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """デバイスの稼働状況タイムライン取得（日勤/夜勤別）"""
    device_addr = device_addr.upper()

    # タイムゾーン設定
    jst = pytz.timezone('Asia/Tokyo')
    utc = pytz.UTC

    # 日付パース（省略時は今日、ただし6:00より前なら前日）
    if date:
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(status_code=400, detail="日付形式が不正です（YYYY-MM-DD）")
    else:
        now_jst = datetime.now(jst)
        target_date = now_jst.date()
        # 現在時刻が6:00より前なら、前日の日付を使用
        if now_jst.hour < 6:
            target_date = target_date - timedelta(days=1)

    # 日勤: 6:00-18:00（JST）
    day_start_jst = jst.localize(datetime.combine(target_date, datetime.min.time()).replace(hour=6))
    day_end_jst = jst.localize(datetime.combine(target_date, datetime.min.time()).replace(hour=18))

    # 夜勤: 18:00-翌6:00（JST）
    night_start_jst = day_end_jst
    night_end_jst = jst.localize(
        datetime.combine(target_date + timedelta(days=1), datetime.min.time()).replace(hour=6)
    )

    # UTC変換
    day_start_utc = day_start_jst.astimezone(utc).replace(tzinfo=None)
    day_end_utc = day_end_jst.astimezone(utc).replace(tzinfo=None)
    night_start_utc = night_start_jst.astimezone(utc).replace(tzinfo=None)
    night_end_utc = night_end_jst.astimezone(utc).replace(tzinfo=None)

    # 日勤データ取得
    day_history = db.query(DeviceHistory).filter(
        DeviceHistory.device_addr == device_addr,
        DeviceHistory.timestamp >= day_start_utc,
        DeviceHistory.timestamp < day_end_utc
    ).order_by(DeviceHistory.timestamp).all()

    # 夜勤データ取得
    night_history = db.query(DeviceHistory).filter(
        DeviceHistory.device_addr == device_addr,
        DeviceHistory.timestamp >= night_start_utc,
        DeviceHistory.timestamp < night_end_utc
    ).order_by(DeviceHistory.timestamp).all()

    # セグメント化関数
    def create_segments(history_data, start_time, end_time):
        # 現在時刻（JST）を取得
        now_jst = datetime.now(jst).replace(tzinfo=None)

        # end_timeが未来の場合、現在時刻までに制限
        actual_end_time = min(end_time, now_jst)

        segments = []
        if not history_data:
            # データがない場合は全体をグレーに
            return [{
                "status": "none",
                "color": "gray",
                "start": start_time.isoformat(),
                "end": actual_end_time.isoformat(),
                "duration_minutes": int((actual_end_time - start_time).total_seconds() / 60)
            }]

        current_status = None
        current_color = None
        segment_start = start_time

        for record in history_data:
            status, color = get_status_from_lights(record.red, record.yellow, record.green)
            record_time = utc.localize(record.timestamp).astimezone(jst).replace(tzinfo=None)

            # ステータス変化を検出
            if current_status is None:
                # 最初のレコード
                current_status = status
                current_color = color
            elif status != current_status:
                # ステータス変化 - 前のセグメントを保存
                segments.append({
                    "status": current_status,
                    "color": current_color,
                    "start": segment_start.isoformat(),
                    "end": record_time.isoformat(),
                    "duration_minutes": int((record_time - segment_start).total_seconds() / 60)
                })
                segment_start = record_time
                current_status = status
                current_color = color

        # 最後のセグメント（現在時刻まで）
        if current_status is not None:
            segments.append({
                "status": current_status,
                "color": current_color,
                "start": segment_start.isoformat(),
                "end": actual_end_time.isoformat(),
                "duration_minutes": int((actual_end_time - segment_start).total_seconds() / 60)
            })

        # 現在時刻以降（未来）を白で表示
        if actual_end_time < end_time:
            segments.append({
                "status": "future",
                "color": "white",
                "start": actual_end_time.isoformat(),
                "end": end_time.isoformat(),
                "duration_minutes": int((end_time - actual_end_time).total_seconds() / 60)
            })

        return segments

    day_segments = create_segments(day_history, day_start_jst.replace(tzinfo=None), day_end_jst.replace(tzinfo=None))
    night_segments = create_segments(night_history, night_start_jst.replace(tzinfo=None), night_end_jst.replace(tzinfo=None))

    return {
        "device_addr": device_addr,
        "date": target_date.isoformat(),
        "day_shift": {
            "start": day_start_jst.isoformat(),
            "end": day_end_jst.isoformat(),
            "segments": day_segments
        },
        "night_shift": {
            "start": night_start_jst.isoformat(),
            "end": night_end_jst.isoformat(),
            "segments": night_segments
        }
    }


# ========== 稼働率計算 API ==========

@app.get("/api/devices/{device_addr}/operation-rate")
async def get_operation_rate(
    device_addr: str,
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db)
):
    """期間指定での稼働率計算（緑ライトのみ稼働としてカウント）"""
    device_addr = device_addr.upper()

    # タイムゾーン設定
    jst = pytz.timezone('Asia/Tokyo')
    utc = pytz.UTC

    # 日付パース
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日付形式が不正です（YYYY-MM-DD）")

    if start_dt > end_dt:
        raise HTTPException(status_code=400, detail="開始日は終了日より前である必要があります")

    # JSTで0時～翌0時までの範囲を設定
    start_jst = jst.localize(datetime.combine(start_dt, datetime.min.time()))
    end_jst = jst.localize(datetime.combine(end_dt + timedelta(days=1), datetime.min.time()))

    # UTC変換
    start_utc = start_jst.astimezone(utc).replace(tzinfo=None)
    end_utc = end_jst.astimezone(utc).replace(tzinfo=None)

    # 期間内のデータ取得
    history = db.query(DeviceHistory).filter(
        DeviceHistory.device_addr == device_addr,
        DeviceHistory.timestamp >= start_utc,
        DeviceHistory.timestamp < end_utc
    ).order_by(DeviceHistory.timestamp).all()

    # 各ステータスの継続時間を計算
    operation_minutes = 0  # 稼働（緑ライトのみ）
    stop_yellow_minutes = 0  # 停止（黄）
    stop_red_minutes = 0  # 停止（赤）
    none_minutes = 0  # 未稼働

    if not history:
        # データがない場合は全て未稼働
        total_minutes = int((end_utc - start_utc).total_seconds() / 60)
        return {
            "device_addr": device_addr,
            "start_date": start_date,
            "end_date": end_date,
            "operation_rate": 0.0,
            "operation_minutes": 0,
            "stop_yellow_minutes": 0,
            "stop_red_minutes": 0,
            "none_minutes": total_minutes,
            "total_minutes": total_minutes
        }

    # 前のレコードを保持して時間差分を計算
    prev_record = None
    prev_status = None

    for record in history:
        if prev_record is not None:
            # 前のレコードから現在のレコードまでの時間差
            time_diff = (record.timestamp - prev_record.timestamp).total_seconds() / 60

            # 前のレコードのステータスで時間を集計
            if prev_status == "running":
                operation_minutes += time_diff
            elif prev_status == "stop_yellow":
                stop_yellow_minutes += time_diff
            elif prev_status == "stop_red":
                stop_red_minutes += time_diff
            else:
                none_minutes += time_diff

        # 現在のステータスを判定
        prev_status, _ = get_status_from_lights(record.red, record.yellow, record.green)
        prev_record = record

    # 最後のレコードから期間終了までの時間
    if prev_record is not None:
        time_diff = (end_utc - prev_record.timestamp).total_seconds() / 60
        if prev_status == "running":
            operation_minutes += time_diff
        elif prev_status == "stop_yellow":
            stop_yellow_minutes += time_diff
        elif prev_status == "stop_red":
            stop_red_minutes += time_diff
        else:
            none_minutes += time_diff

    # 総時間
    total_minutes = int((end_utc - start_utc).total_seconds() / 60)

    # 稼働率計算（緑ライトのみ）
    operation_rate = (operation_minutes / total_minutes * 100) if total_minutes > 0 else 0.0

    return {
        "device_addr": device_addr,
        "start_date": start_date,
        "end_date": end_date,
        "operation_rate": round(operation_rate, 1),
        "operation_minutes": int(operation_minutes),
        "stop_yellow_minutes": int(stop_yellow_minutes),
        "stop_red_minutes": int(stop_red_minutes),
        "none_minutes": int(none_minutes),
        "total_minutes": total_minutes
    }


# ========== 現在の稼働率（6:00から現在まで）API ==========

@app.get("/api/devices/{device_addr}/current-operation-rate")
async def get_current_operation_rate(
    device_addr: str,
    db: Session = Depends(get_db)
):
    """6:00 JSTから現在時刻までの稼働率を計算（緑ライトのみ稼働としてカウント）"""
    device_addr = device_addr.upper()

    # タイムゾーン設定
    jst = pytz.timezone('Asia/Tokyo')
    utc = pytz.UTC

    # 現在時刻（JST）
    now_jst = datetime.now(jst)

    # 今日の6:00 JST
    start_jst = jst.localize(datetime.combine(now_jst.date(), datetime.min.time())).replace(hour=6)

    # もし現在時刻が6:00より前なら、昨日の6:00から計算
    if now_jst.hour < 6:
        start_jst = start_jst - timedelta(days=1)

    # UTC変換
    start_utc = start_jst.astimezone(utc).replace(tzinfo=None)
    end_utc = now_jst.astimezone(utc).replace(tzinfo=None)

    # 期間内のデータ取得
    history = db.query(DeviceHistory).filter(
        DeviceHistory.device_addr == device_addr,
        DeviceHistory.timestamp >= start_utc,
        DeviceHistory.timestamp <= end_utc
    ).order_by(DeviceHistory.timestamp).all()

    # 各ステータスの継続時間を計算
    operation_minutes = 0  # 稼働（緑ライトのみ）
    stop_yellow_minutes = 0  # 停止（黄）
    stop_red_minutes = 0  # 停止（赤）
    none_minutes = 0  # 未稼働

    # 総時間（分）
    total_minutes = (end_utc - start_utc).total_seconds() / 60

    if not history:
        # データがない場合は全て未稼働
        return {
            "device_addr": device_addr,
            "start_time": start_jst.strftime('%Y-%m-%d %H:%M:%S'),
            "end_time": now_jst.strftime('%Y-%m-%d %H:%M:%S'),
            "operation_rate": 0.0,
            "operation_minutes": 0,
            "stop_yellow_minutes": 0,
            "stop_red_minutes": 0,
            "none_minutes": int(total_minutes),
            "total_minutes": int(total_minutes)
        }

    # 前のレコードを保持して時間差分を計算
    prev_record = None
    prev_status = None

    for record in history:
        if prev_record is not None:
            # 前のレコードから現在のレコードまでの時間差
            time_diff = (record.timestamp - prev_record.timestamp).total_seconds() / 60

            # 前のレコードのステータスで時間を集計
            if prev_status == "running":
                operation_minutes += time_diff
            elif prev_status == "stop_yellow":
                stop_yellow_minutes += time_diff
            elif prev_status == "stop_red":
                stop_red_minutes += time_diff
            else:
                none_minutes += time_diff

        # 現在のステータスを判定
        prev_status, _ = get_status_from_lights(record.red, record.yellow, record.green)
        prev_record = record

    # 最後のレコードから現在時刻までの時間
    if prev_record is not None:
        time_diff = (end_utc - prev_record.timestamp).total_seconds() / 60
        if prev_status == "running":
            operation_minutes += time_diff
        elif prev_status == "stop_yellow":
            stop_yellow_minutes += time_diff
        elif prev_status == "stop_red":
            stop_red_minutes += time_diff
        else:
            none_minutes += time_diff

    # 稼働率計算（緑ライトのみ）
    operation_rate = (operation_minutes / total_minutes * 100) if total_minutes > 0 else 0.0

    return {
        "device_addr": device_addr,
        "start_time": start_jst.strftime('%Y-%m-%d %H:%M:%S'),
        "end_time": now_jst.strftime('%Y-%m-%d %H:%M:%S'),
        "operation_rate": round(operation_rate, 1),
        "operation_minutes": int(operation_minutes),
        "stop_yellow_minutes": int(stop_yellow_minutes),
        "stop_red_minutes": int(stop_red_minutes),
        "none_minutes": int(none_minutes),
        "total_minutes": int(total_minutes)
    }


# ========== データ受信ログAPI ==========

@app.get("/api/devices/{device_addr}/data-logs")
async def get_device_data_logs(
    device_addr: str,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """デバイスのデータ受信ログを取得"""
    device_addr = device_addr.upper()

    # 最新のログを取得
    logs = db.query(DeviceHistory).filter(
        DeviceHistory.device_addr == device_addr
    ).order_by(DeviceHistory.timestamp.desc()).limit(limit).all()

    # タイムゾーン設定
    jst = pytz.timezone('Asia/Tokyo')
    utc = pytz.UTC

    result = []
    for log in logs:
        # UTC -> JST変換
        utc_time = utc.localize(log.timestamp)
        jst_time = utc_time.astimezone(jst)

        result.append({
            "timestamp": jst_time.strftime('%Y-%m-%d %H:%M:%S'),
            "status_code": log.status_code,
            "status_text": log.status_text,
            "battery": log.battery,
            "red": log.red,
            "yellow": log.yellow,
            "green": log.green,
            "device_id": log.device_id
        })

    return {
        "device_addr": device_addr,
        "total_logs": len(result),
        "logs": result
    }


# ========== 全体稼働率API ==========

@app.get("/api/overall/current-status")
async def get_overall_current_status(db: Session = Depends(get_db)):
    """全デバイスの現在のステータス時間割合を取得（円グラフ用）"""
    jst = pytz.timezone('Asia/Tokyo')
    utc = pytz.UTC

    # 登録されているデバイス一覧を取得
    registrations = db.query(DeviceRegistration).all()
    device_addrs = [reg.device_addr for reg in registrations]

    if not device_addrs:
        return {
            "running": 0,
            "stop_yellow": 0,
            "stop_red": 0,
            "idle": 0,
            "total_devices": 0
        }

    # 6:00～現在までの時間範囲（現在時刻が6:00より前なら前日の6:00から）
    now_jst = datetime.now(jst)
    today_date = now_jst.date()

    # 今日の6:00を計算
    start_time = jst.localize(datetime.combine(today_date, datetime.min.time()) + timedelta(hours=6))

    # 現在時刻が6:00より前なら、前日の6:00を基準にする
    if now_jst.hour < 6:
        start_time = start_time - timedelta(days=1)

    end_time = now_jst

    # 各ステータスの合計時間（分）
    total_running_minutes = 0
    total_stop_yellow_minutes = 0
    total_stop_red_minutes = 0
    total_idle_minutes = 0

    # 各デバイスの稼働時間を計算
    for device_addr in device_addrs:
        # この期間の履歴を取得
        histories = db.query(DeviceHistory).filter(
            DeviceHistory.device_addr == device_addr,
            DeviceHistory.timestamp >= start_time.astimezone(utc).replace(tzinfo=None),
            DeviceHistory.timestamp < end_time.astimezone(utc).replace(tzinfo=None)
        ).order_by(DeviceHistory.timestamp).all()

        if not histories:
            continue

        # 各履歴間の時間を計算
        for j in range(len(histories)):
            current = histories[j]

            if j < len(histories) - 1:
                next_record = histories[j + 1]
                duration_minutes = (next_record.timestamp - current.timestamp).total_seconds() / 60
            else:
                # 最後のレコードは現在時刻まで
                end_point = end_time.astimezone(utc).replace(tzinfo=None)
                duration_minutes = (end_point - current.timestamp).total_seconds() / 60

            # 負の値を防ぐ
            duration_minutes = max(0, duration_minutes)

            # ステータスごとに集計
            if current.green:
                total_running_minutes += duration_minutes
            elif current.yellow:
                total_stop_yellow_minutes += duration_minutes
            elif current.red:
                total_stop_red_minutes += duration_minutes
            else:
                total_idle_minutes += duration_minutes

    # 合計時間
    total_minutes = total_running_minutes + total_stop_yellow_minutes + total_stop_red_minutes + total_idle_minutes

    # 割合を計算（%）
    if total_minutes > 0:
        running_percent = round(total_running_minutes / total_minutes * 100, 1)
        stop_yellow_percent = round(total_stop_yellow_minutes / total_minutes * 100, 1)
        stop_red_percent = round(total_stop_red_minutes / total_minutes * 100, 1)
        idle_percent = round(total_idle_minutes / total_minutes * 100, 1)
    else:
        running_percent = stop_yellow_percent = stop_red_percent = idle_percent = 0

    return {
        "running": running_percent,
        "stop_yellow": stop_yellow_percent,
        "stop_red": stop_red_percent,
        "idle": idle_percent,
        "total_devices": len(device_addrs),
        "total_hours": round(total_minutes / 60, 1)
    }


@app.get("/api/overall/hourly-status")
async def get_overall_hourly_status(
    date: str = Query(default=None, description="YYYY-MM-DD形式の日付（省略時は今日）"),
    db: Session = Depends(get_db)
):
    """1時間ごとの全体ステータス割合を取得（積上げ棒グラフ用）"""
    jst = pytz.timezone('Asia/Tokyo')
    utc = pytz.UTC

    # 日付処理
    if date:
        target_date = datetime.strptime(date, '%Y-%m-%d').date()
    else:
        now_jst = datetime.now(jst)
        target_date = now_jst.date()
        # 現在時刻が6:00より前なら、前日の日付を使用
        if now_jst.hour < 6:
            target_date = target_date - timedelta(days=1)

    # 6:00～翌6:00の時間範囲を設定
    start_time = jst.localize(datetime.combine(target_date, datetime.min.time()) + timedelta(hours=6))
    end_time = start_time + timedelta(hours=24)

    # 登録されているデバイス一覧を取得
    registrations = db.query(DeviceRegistration).all()
    device_addrs = [reg.device_addr for reg in registrations]

    if not device_addrs:
        return {"hours": [], "data": []}

    total_devices = len(device_addrs)

    # 1時間ごとのデータを作成
    hourly_data = []
    total_green_apples = 0  # GreenApple合計
    current_hour = start_time

    while current_hour < end_time and current_hour <= datetime.now(jst):
        next_hour = current_hour + timedelta(hours=1)

        # この時間帯の各ステータスの合計時間（分）
        total_running_minutes = 0
        total_stop_yellow_minutes = 0
        total_stop_red_minutes = 0
        total_idle_minutes = 0

        for device_addr in device_addrs:
            # この時間帯の履歴を取得
            histories = db.query(DeviceHistory).filter(
                DeviceHistory.device_addr == device_addr,
                DeviceHistory.timestamp >= current_hour.astimezone(utc).replace(tzinfo=None),
                DeviceHistory.timestamp < next_hour.astimezone(utc).replace(tzinfo=None)
            ).order_by(DeviceHistory.timestamp).all()

            # 直前の状態も取得（時間帯開始時点の状態を知るため）
            prev_history = db.query(DeviceHistory).filter(
                DeviceHistory.device_addr == device_addr,
                DeviceHistory.timestamp < current_hour.astimezone(utc).replace(tzinfo=None)
            ).order_by(DeviceHistory.timestamp.desc()).first()

            # 時間帯の終了時刻（現在時刻を超えない）
            period_end = min(next_hour, datetime.now(jst)).astimezone(utc).replace(tzinfo=None)

            if not histories and not prev_history:
                # データがない場合は休止中とする
                duration_minutes = (period_end - current_hour.astimezone(utc).replace(tzinfo=None)).total_seconds() / 60
                total_idle_minutes += duration_minutes
                continue

            # 時間帯開始時点の状態を決定
            if histories:
                all_records = histories[:]
            else:
                all_records = []

            # 時間帯開始時点の状態を追加
            if prev_history:
                # 直前の状態を時間帯開始時点に設定
                start_status = {
                    'timestamp': current_hour.astimezone(utc).replace(tzinfo=None),
                    'green': prev_history.green,
                    'yellow': prev_history.yellow,
                    'red': prev_history.red
                }
            elif all_records:
                # 履歴の最初のレコードを時間帯開始時点に設定
                start_status = {
                    'timestamp': current_hour.astimezone(utc).replace(tzinfo=None),
                    'green': all_records[0].green,
                    'yellow': all_records[0].yellow,
                    'red': all_records[0].red
                }
            else:
                # データがない場合
                start_status = {
                    'timestamp': current_hour.astimezone(utc).replace(tzinfo=None),
                    'green': False,
                    'yellow': False,
                    'red': False
                }

            # 時間計算用のレコードリスト
            time_records = [start_status]
            for h in all_records:
                time_records.append({
                    'timestamp': h.timestamp,
                    'green': h.green,
                    'yellow': h.yellow,
                    'red': h.red
                })

            # 各レコード間の時間を計算
            for i in range(len(time_records)):
                current_record = time_records[i]

                if i < len(time_records) - 1:
                    next_timestamp = time_records[i + 1]['timestamp']
                else:
                    next_timestamp = period_end

                duration_minutes = (next_timestamp - current_record['timestamp']).total_seconds() / 60
                duration_minutes = max(0, duration_minutes)

                # ステータスごとに集計
                if current_record['green']:
                    total_running_minutes += duration_minutes
                elif current_record['yellow']:
                    total_stop_yellow_minutes += duration_minutes
                elif current_record['red']:
                    total_stop_red_minutes += duration_minutes
                else:
                    total_idle_minutes += duration_minutes

        # 合計時間
        total_minutes = total_running_minutes + total_stop_yellow_minutes + total_stop_red_minutes + total_idle_minutes

        # 割合を計算
        if total_minutes > 0:
            running_percent = round(total_running_minutes / total_minutes * 100, 1)
            stop_yellow_percent = round(total_stop_yellow_minutes / total_minutes * 100, 1)
            stop_red_percent = round(total_stop_red_minutes / total_minutes * 100, 1)
            idle_percent = round(total_idle_minutes / total_minutes * 100, 1)
        else:
            running_percent = stop_yellow_percent = stop_red_percent = idle_percent = 0

        # GreenApple獲得数を計算
        green_apples = 0
        if running_percent >= 50:
            green_apples = 5
        elif running_percent >= 40:
            green_apples = 3
        elif running_percent >= 35:
            green_apples = 2
        elif running_percent > 30:
            green_apples = 1

        total_green_apples += green_apples

        hourly_data.append({
            "hour": current_hour.strftime('%H:%M'),
            "running": running_percent,
            "stop_yellow": stop_yellow_percent,
            "stop_red": stop_red_percent,
            "idle": idle_percent,
            "green_apples": green_apples
        })

        current_hour = next_hour

    return {
        "date": target_date.strftime('%Y-%m-%d'),
        "total_devices": total_devices,
        "total_green_apples": total_green_apples,
        "data": hourly_data
    }


@app.get("/api/overall/daily-operation-rate")
async def get_overall_daily_operation_rate(
    year: int = Query(default=None, description="年（省略時は今年）"),
    month: int = Query(default=None, description="月（省略時は今月）"),
    days: int = Query(default=None, description="取得する日数（year/month指定時は無視）"),
    start_date: str = Query(default=None, description="開始日（YYYY-MM-DD形式）"),
    end_date: str = Query(default=None, description="終了日（YYYY-MM-DD形式）"),
    db: Session = Depends(get_db)
):
    """日ごとの全体稼働率を取得（折れ線グラフ用）"""
    jst = pytz.timezone('Asia/Tokyo')
    utc = pytz.UTC

    # 登録されているデバイス一覧を取得
    registrations = db.query(DeviceRegistration).all()
    device_addrs = [reg.device_addr for reg in registrations]

    if not device_addrs:
        return {"dates": [], "rates": []}

    total_devices = len(device_addrs)
    daily_rates = []

    # 対象期間を決定
    if start_date is not None and end_date is not None:
        # 日付範囲指定の場合
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
            if start_dt > end_dt:
                raise HTTPException(status_code=400, detail="開始日は終了日より前である必要があります")
            # 開始日から終了日までの日付リストを作成
            date_list = []
            current_date = start_dt
            while current_date <= end_dt:
                date_list.append(current_date)
                current_date += timedelta(days=1)
        except ValueError:
            raise HTTPException(status_code=400, detail="日付形式が不正です（YYYY-MM-DD）")
    elif year is not None and month is not None:
        # 年月指定の場合：その月の1日～末日
        import calendar
        days_in_month = calendar.monthrange(year, month)[1]
        date_list = [datetime(year, month, day).date() for day in range(1, days_in_month + 1)]
    else:
        # 日数指定の場合（従来の動作）
        if days is None:
            days = 7
        date_list = [(datetime.now(jst) - timedelta(days=i)).date() for i in range(days - 1, -1, -1)]

    # 各日のデータを取得
    for target_date in date_list:

        # 6:00～翌6:00の時間範囲
        start_time = jst.localize(datetime.combine(target_date, datetime.min.time()) + timedelta(hours=6))
        end_time = start_time + timedelta(hours=24)

        # この日の全デバイスの稼働率を計算
        total_running_minutes = 0
        total_possible_minutes = 0

        for device_addr in device_addrs:
            # この日の履歴を取得
            histories = db.query(DeviceHistory).filter(
                DeviceHistory.device_addr == device_addr,
                DeviceHistory.timestamp >= start_time.astimezone(utc).replace(tzinfo=None),
                DeviceHistory.timestamp < end_time.astimezone(utc).replace(tzinfo=None)
            ).order_by(DeviceHistory.timestamp).all()

            if not histories:
                continue

            # 各履歴間の時間を計算
            for j in range(len(histories)):
                current = histories[j]

                if j < len(histories) - 1:
                    next_record = histories[j + 1]
                    duration_minutes = (next_record.timestamp - current.timestamp).total_seconds() / 60
                else:
                    # 最後のレコードは現在時刻または終了時刻まで
                    if end_time <= datetime.now(jst):
                        end_point = end_time.astimezone(utc).replace(tzinfo=None)
                    else:
                        end_point = datetime.now(utc).replace(tzinfo=None)
                    duration_minutes = (end_point - current.timestamp).total_seconds() / 60

                # 負の値を防ぐ
                duration_minutes = max(0, duration_minutes)

                total_possible_minutes += duration_minutes

                if current.green:
                    total_running_minutes += duration_minutes

        # 稼働率を計算
        if total_possible_minutes > 0:
            operation_rate = round(total_running_minutes / total_possible_minutes * 100, 1)
        else:
            operation_rate = 0

        daily_rates.append({
            "date": target_date.strftime('%m/%d'),
            "rate": operation_rate
        })

    return {
        "total_devices": total_devices,
        "data": daily_rates
    }


@app.get("/api/overall/daily-green-apples")
async def get_daily_green_apples(
    year: int = Query(default=None, description="年（省略時は今年）"),
    month: int = Query(default=None, description="月（省略時は今月）"),
    start_date: str = Query(default=None, description="開始日（YYYY-MM-DD形式）"),
    end_date: str = Query(default=None, description="終了日（YYYY-MM-DD形式）"),
    db: Session = Depends(get_db)
):
    """GreenApple獲得数を取得（棒グラフ用）"""
    jst = pytz.timezone('Asia/Tokyo')
    utc = pytz.UTC

    # 登録されているデバイス一覧を取得
    registrations = db.query(DeviceRegistration).all()
    device_addrs = [reg.device_addr for reg in registrations]

    if not device_addrs:
        return {"data": []}

    # 対象期間を決定
    if start_date is not None and end_date is not None:
        # 日付範囲指定の場合
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
            if start_dt > end_dt:
                raise HTTPException(status_code=400, detail="開始日は終了日より前である必要があります")
            # 開始日から終了日までの日付リストを作成
            date_list = []
            current_date = start_dt
            while current_date <= end_dt:
                date_list.append(current_date)
                current_date += timedelta(days=1)
        except ValueError:
            raise HTTPException(status_code=400, detail="日付形式が不正です（YYYY-MM-DD）")
    else:
        # 年月指定の場合（従来の動作）
        now_jst = datetime.now(jst)
        if year is None:
            year = now_jst.year
        if month is None:
            month = now_jst.month

        # その月の日数を取得
        import calendar
        days_in_month = calendar.monthrange(year, month)[1]
        date_list = [datetime(year, month, day).date() for day in range(1, days_in_month + 1)]

    daily_apples = []

    # 各日のデータを取得
    for target_date in date_list:

        # 6:00～翌6:00の時間範囲
        start_time = jst.localize(datetime.combine(target_date, datetime.min.time()) + timedelta(hours=6))
        end_time = start_time + timedelta(hours=24)

        # この日の時間別GreenApple獲得数を計算
        daily_green_apples = 0
        current_hour = start_time

        while current_hour < end_time and current_hour <= datetime.now(jst):
            next_hour = current_hour + timedelta(hours=1)

            # この時間帯の各ステータスの合計時間（分）
            total_running_minutes = 0
            total_stop_yellow_minutes = 0
            total_stop_red_minutes = 0
            total_idle_minutes = 0

            for device_addr in device_addrs:
                # この時間帯の履歴を取得
                histories = db.query(DeviceHistory).filter(
                    DeviceHistory.device_addr == device_addr,
                    DeviceHistory.timestamp >= current_hour.astimezone(utc).replace(tzinfo=None),
                    DeviceHistory.timestamp < next_hour.astimezone(utc).replace(tzinfo=None)
                ).order_by(DeviceHistory.timestamp).all()

                # 直前の状態も取得
                prev_history = db.query(DeviceHistory).filter(
                    DeviceHistory.device_addr == device_addr,
                    DeviceHistory.timestamp < current_hour.astimezone(utc).replace(tzinfo=None)
                ).order_by(DeviceHistory.timestamp.desc()).first()

                # 時間帯の終了時刻
                period_end = min(next_hour, datetime.now(jst)).astimezone(utc).replace(tzinfo=None)

                if not histories and not prev_history:
                    duration_minutes = (period_end - current_hour.astimezone(utc).replace(tzinfo=None)).total_seconds() / 60
                    total_idle_minutes += duration_minutes
                    continue

                # 時間帯開始時点の状態を決定
                if histories:
                    all_records = histories[:]
                else:
                    all_records = []

                if prev_history:
                    start_status = {
                        'timestamp': current_hour.astimezone(utc).replace(tzinfo=None),
                        'green': prev_history.green,
                        'yellow': prev_history.yellow,
                        'red': prev_history.red
                    }
                elif all_records:
                    start_status = {
                        'timestamp': current_hour.astimezone(utc).replace(tzinfo=None),
                        'green': all_records[0].green,
                        'yellow': all_records[0].yellow,
                        'red': all_records[0].red
                    }
                else:
                    start_status = {
                        'timestamp': current_hour.astimezone(utc).replace(tzinfo=None),
                        'green': False,
                        'yellow': False,
                        'red': False
                    }

                # 時間計算用のレコードリスト
                time_records = [start_status]
                for h in all_records:
                    time_records.append({
                        'timestamp': h.timestamp,
                        'green': h.green,
                        'yellow': h.yellow,
                        'red': h.red
                    })

                # 各レコード間の時間を計算
                for idx in range(len(time_records)):
                    current_record = time_records[idx]

                    if idx < len(time_records) - 1:
                        next_timestamp = time_records[idx + 1]['timestamp']
                    else:
                        next_timestamp = period_end

                    duration_minutes = (next_timestamp - current_record['timestamp']).total_seconds() / 60
                    duration_minutes = max(0, duration_minutes)

                    if current_record['green']:
                        total_running_minutes += duration_minutes
                    elif current_record['yellow']:
                        total_stop_yellow_minutes += duration_minutes
                    elif current_record['red']:
                        total_stop_red_minutes += duration_minutes
                    else:
                        total_idle_minutes += duration_minutes

            # 合計時間
            total_minutes = total_running_minutes + total_stop_yellow_minutes + total_stop_red_minutes + total_idle_minutes

            # 稼働率を計算
            if total_minutes > 0:
                running_percent = round(total_running_minutes / total_minutes * 100, 1)
            else:
                running_percent = 0

            # GreenApple獲得数を計算
            green_apples = 0
            if running_percent >= 50:
                green_apples = 5
            elif running_percent >= 40:
                green_apples = 3
            elif running_percent >= 35:
                green_apples = 2
            elif running_percent > 30:
                green_apples = 1

            daily_green_apples += green_apples
            current_hour = next_hour

        daily_apples.append({
            "date": target_date.strftime('%m/%d'),
            "full_date": target_date.strftime('%Y-%m-%d'),
            "apples": daily_green_apples
        })

    return {
        "data": daily_apples
    }


@app.get("/api/overall/hourly-green-apples")
async def get_hourly_green_apples(
    date: str = Query(..., description="YYYY-MM-DD形式の日付"),
    db: Session = Depends(get_db)
):
    """特定の日の時間帯別GreenApple獲得数を取得"""
    jst = pytz.timezone('Asia/Tokyo')
    utc = pytz.UTC

    # 登録されているデバイス一覧を取得
    registrations = db.query(DeviceRegistration).all()
    device_addrs = [reg.device_addr for reg in registrations]

    if not device_addrs:
        return {"data": []}

    # 日付処理
    target_date = datetime.strptime(date, '%Y-%m-%d').date()

    # 6:00～翌6:00の時間範囲
    start_time = jst.localize(datetime.combine(target_date, datetime.min.time()) + timedelta(hours=6))
    end_time = start_time + timedelta(hours=24)

    hourly_apples = []
    current_hour = start_time

    while current_hour < end_time and current_hour <= datetime.now(jst):
        next_hour = current_hour + timedelta(hours=1)

        # この時間帯の各ステータスの合計時間（分）
        total_running_minutes = 0
        total_stop_yellow_minutes = 0
        total_stop_red_minutes = 0
        total_idle_minutes = 0

        for device_addr in device_addrs:
            # この時間帯の履歴を取得
            histories = db.query(DeviceHistory).filter(
                DeviceHistory.device_addr == device_addr,
                DeviceHistory.timestamp >= current_hour.astimezone(utc).replace(tzinfo=None),
                DeviceHistory.timestamp < next_hour.astimezone(utc).replace(tzinfo=None)
            ).order_by(DeviceHistory.timestamp).all()

            # 直前の状態も取得
            prev_history = db.query(DeviceHistory).filter(
                DeviceHistory.device_addr == device_addr,
                DeviceHistory.timestamp < current_hour.astimezone(utc).replace(tzinfo=None)
            ).order_by(DeviceHistory.timestamp.desc()).first()

            # 時間帯の終了時刻
            period_end = min(next_hour, datetime.now(jst)).astimezone(utc).replace(tzinfo=None)

            if not histories and not prev_history:
                duration_minutes = (period_end - current_hour.astimezone(utc).replace(tzinfo=None)).total_seconds() / 60
                total_idle_minutes += duration_minutes
                continue

            # 時間帯開始時点の状態を決定
            if histories:
                all_records = histories[:]
            else:
                all_records = []

            if prev_history:
                start_status = {
                    'timestamp': current_hour.astimezone(utc).replace(tzinfo=None),
                    'green': prev_history.green,
                    'yellow': prev_history.yellow,
                    'red': prev_history.red
                }
            elif all_records:
                start_status = {
                    'timestamp': current_hour.astimezone(utc).replace(tzinfo=None),
                    'green': all_records[0].green,
                    'yellow': all_records[0].yellow,
                    'red': all_records[0].red
                }
            else:
                start_status = {
                    'timestamp': current_hour.astimezone(utc).replace(tzinfo=None),
                    'green': False,
                    'yellow': False,
                    'red': False
                }

            # 時間計算用のレコードリスト
            time_records = [start_status]
            for h in all_records:
                time_records.append({
                    'timestamp': h.timestamp,
                    'green': h.green,
                    'yellow': h.yellow,
                    'red': h.red
                })

            # 各レコード間の時間を計算
            for idx in range(len(time_records)):
                current_record = time_records[idx]

                if idx < len(time_records) - 1:
                    next_timestamp = time_records[idx + 1]['timestamp']
                else:
                    next_timestamp = period_end

                duration_minutes = (next_timestamp - current_record['timestamp']).total_seconds() / 60
                duration_minutes = max(0, duration_minutes)

                if current_record['green']:
                    total_running_minutes += duration_minutes
                elif current_record['yellow']:
                    total_stop_yellow_minutes += duration_minutes
                elif current_record['red']:
                    total_stop_red_minutes += duration_minutes
                else:
                    total_idle_minutes += duration_minutes

        # 合計時間
        total_minutes = total_running_minutes + total_stop_yellow_minutes + total_stop_red_minutes + total_idle_minutes

        # 稼働率を計算
        if total_minutes > 0:
            running_percent = round(total_running_minutes / total_minutes * 100, 1)
        else:
            running_percent = 0

        # GreenApple獲得数を計算
        green_apples = 0
        if running_percent >= 50:
            green_apples = 5
        elif running_percent >= 40:
            green_apples = 3
        elif running_percent >= 35:
            green_apples = 2
        elif running_percent > 30:
            green_apples = 1

        hourly_apples.append({
            "hour": current_hour.strftime('%H:00'),
            "running_percent": running_percent,
            "apples": green_apples
        })

        current_hour = next_hour

    return {
        "date": date,
        "data": hourly_apples
    }


@app.get("/api/devices/{device_addr}/hourly-operation-rate")
async def get_device_hourly_operation_rate(
    device_addr: str,
    date: str = Query(..., description="YYYY-MM-DD形式の日付"),
    db: Session = Depends(get_db)
):
    """設備の時間帯別稼働率を取得（積上げ棒グラフ用）"""
    device_addr = device_addr.upper()

    jst = pytz.timezone('Asia/Tokyo')
    utc = pytz.UTC

    # 日付処理
    try:
        target_date = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日付形式が不正です（YYYY-MM-DD）")

    # 6:00～翌6:00の時間範囲を設定
    start_time = jst.localize(datetime.combine(target_date, datetime.min.time()) + timedelta(hours=6))
    end_time = start_time + timedelta(hours=24)

    hourly_data = []
    current_hour = start_time

    while current_hour < end_time and current_hour <= datetime.now(jst):
        next_hour = current_hour + timedelta(hours=1)

        # この時間帯の稼働データを取得
        total_running_minutes = 0
        total_stop_yellow_minutes = 0
        total_stop_red_minutes = 0
        total_idle_minutes = 0

        # この時間帯の履歴を取得
        histories = db.query(DeviceHistory).filter(
            DeviceHistory.device_addr == device_addr,
            DeviceHistory.timestamp >= current_hour.astimezone(utc).replace(tzinfo=None),
            DeviceHistory.timestamp < next_hour.astimezone(utc).replace(tzinfo=None)
        ).order_by(DeviceHistory.timestamp).all()

        # 直前の状態も取得
        prev_history = db.query(DeviceHistory).filter(
            DeviceHistory.device_addr == device_addr,
            DeviceHistory.timestamp < current_hour.astimezone(utc).replace(tzinfo=None)
        ).order_by(DeviceHistory.timestamp.desc()).first()

        # 時間帯の終了時刻
        period_end = min(next_hour, datetime.now(jst)).astimezone(utc).replace(tzinfo=None)

        if not histories and not prev_history:
            duration_minutes = (period_end - current_hour.astimezone(utc).replace(tzinfo=None)).total_seconds() / 60
            total_idle_minutes += duration_minutes
        else:
            # 時間帯開始時点の状態を決定
            if histories:
                all_records = histories[:]
            else:
                all_records = []

            if prev_history:
                start_status = {
                    'timestamp': current_hour.astimezone(utc).replace(tzinfo=None),
                    'green': prev_history.green,
                    'yellow': prev_history.yellow,
                    'red': prev_history.red
                }
            elif all_records:
                start_status = {
                    'timestamp': current_hour.astimezone(utc).replace(tzinfo=None),
                    'green': all_records[0].green,
                    'yellow': all_records[0].yellow,
                    'red': all_records[0].red
                }
            else:
                start_status = {
                    'timestamp': current_hour.astimezone(utc).replace(tzinfo=None),
                    'green': False,
                    'yellow': False,
                    'red': False
                }

            # 時間計算用のレコードリスト
            time_records = [start_status]
            for h in all_records:
                time_records.append({
                    'timestamp': h.timestamp,
                    'green': h.green,
                    'yellow': h.yellow,
                    'red': h.red
                })

            # 各レコード間の時間を計算
            for idx in range(len(time_records)):
                current_record = time_records[idx]

                if idx < len(time_records) - 1:
                    next_timestamp = time_records[idx + 1]['timestamp']
                else:
                    next_timestamp = period_end

                duration_minutes = (next_timestamp - current_record['timestamp']).total_seconds() / 60
                duration_minutes = max(0, duration_minutes)

                if current_record['green']:
                    total_running_minutes += duration_minutes
                elif current_record['yellow']:
                    total_stop_yellow_minutes += duration_minutes
                elif current_record['red']:
                    total_stop_red_minutes += duration_minutes
                else:
                    total_idle_minutes += duration_minutes

        # 合計時間
        total_minutes = total_running_minutes + total_stop_yellow_minutes + total_stop_red_minutes + total_idle_minutes

        # 割合を計算
        if total_minutes > 0:
            running_percent = round(total_running_minutes / total_minutes * 100, 1)
            stop_yellow_percent = round(total_stop_yellow_minutes / total_minutes * 100, 1)
            stop_red_percent = round(total_stop_red_minutes / total_minutes * 100, 1)
            idle_percent = round(total_idle_minutes / total_minutes * 100, 1)
        else:
            running_percent = stop_yellow_percent = stop_red_percent = idle_percent = 0

        hourly_data.append({
            "hour": current_hour.strftime('%H:00'),
            "running": running_percent,
            "stop_yellow": stop_yellow_percent,
            "stop_red": stop_red_percent,
            "idle": idle_percent
        })

        current_hour = next_hour

    return {
        "device_addr": device_addr,
        "date": date,
        "data": hourly_data
    }
