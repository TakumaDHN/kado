"""
デバイス設定 - 登録済みセンサーデバイスの情報
"""

# JP_LightTowerUpdate_LAN_1.4.0.ino の clientESP[7] に対応
REGISTERED_DEVICES = {
    "ECDA3BBE61E8": {
        "name": "設備1号機",
        "location": "製造ライン A",
        "description": "メイン生産機",
        "index": 0
    },
    "B08184044C94": {
        "name": "設備2号機",
        "location": "製造ライン A",
        "description": "サブ生産機",
        "index": 1
    },
    "188B0E936AF8": {
        "name": "設備3号機",
        "location": "製造ライン B",
        "description": "検査機",
        "index": 2
    },
    "188B0E93DAD8": {
        "name": "設備4号機",
        "location": "製造ライン B",
        "description": "梱包機",
        "index": 3
    },
    "188B0E91ABD4": {
        "name": "設備5号機",
        "location": "製造ライン C",
        "description": "加工機",
        "index": 4
    },
    "188B0E915D9C": {
        "name": "設備6号機",
        "location": "製造ライン C",
        "description": "組立機",
        "index": 5
    },
    "188B0E93B5D4": {
        "name": "設備7号機",
        "location": "製造ライン C",
        "description": "出荷検査機",
        "index": 6
    }
}

def get_device_name(mac_addr: str) -> str:
    """MACアドレスからデバイス名を取得"""
    device = REGISTERED_DEVICES.get(mac_addr)
    return device["name"] if device else mac_addr

def get_device_info(mac_addr: str) -> dict:
    """MACアドレスからデバイス情報を取得"""
    return REGISTERED_DEVICES.get(mac_addr, {
        "name": mac_addr,
        "location": "不明",
        "description": "未登録デバイス",
        "index": 999
    })

def get_all_devices() -> dict:
    """全登録デバイスを取得"""
    return REGISTERED_DEVICES


def get_all_devices_from_db(db):
    """DBから全デバイス情報を取得"""
    from .models import DeviceRegistration

    devices = db.query(DeviceRegistration).filter(
        DeviceRegistration.is_enabled == True
    ).order_by(DeviceRegistration.index).all()

    result = {}
    for device in devices:
        result[device.device_addr] = {
            "name": device.name,
            "location": device.location,
            "description": device.description,
            "index": device.index
        }
    return result


def get_device_info_from_db(db, mac_addr: str) -> dict:
    """DBから個別デバイス情報を取得"""
    from .models import DeviceRegistration

    device = db.query(DeviceRegistration).filter(
        DeviceRegistration.device_addr == mac_addr,
        DeviceRegistration.is_enabled == True
    ).first()

    if device:
        return {
            "name": device.name,
            "location": device.location,
            "description": device.description,
            "index": device.index
        }

    # フォールバック: ハードコードされた設定を確認
    return REGISTERED_DEVICES.get(mac_addr, {
        "name": mac_addr,
        "location": "不明",
        "description": "未登録デバイス",
        "index": 999
    })
