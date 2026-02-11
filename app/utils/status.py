"""Status determination utilities"""


def get_status_from_lights(red: bool, yellow: bool, green: bool) -> tuple:
    """ライトの状態からステータスと色を判定"""
    if green:
        return "running", "green"
    elif yellow:
        return "stop_yellow", "yellow"
    elif red:
        return "stop_red", "red"
    else:
        return "none", "gray"
