"""
台灣高鐵車站資料
THSR Station Data
"""

# 車站代碼對應表 (網站使用的 value)
STATIONS = {
    "南港": "1",
    "台北": "2",
    "板橋": "3",
    "桃園": "4",
    "新竹": "5",
    "苗栗": "6",
    "台中": "7",
    "彰化": "8",
    "雲林": "9",
    "嘉義": "10",
    "台南": "11",
    "左營": "12",
}

# 反向對應：代碼 -> 站名
STATION_CODES = {v: k for k, v in STATIONS.items()}

# 車站列表（按順序）
STATION_LIST = [
    "南港", "台北", "板橋", "桃園", "新竹",
    "苗栗", "台中", "彰化", "雲林", "嘉義",
    "台南", "左營"
]


def get_station_code(station_name: str) -> str:
    """
    取得車站代碼

    Args:
        station_name: 車站名稱

    Returns:
        車站代碼

    Raises:
        ValueError: 找不到車站
    """
    if station_name not in STATIONS:
        raise ValueError(f"找不到車站: {station_name}，可用車站: {', '.join(STATION_LIST)}")
    return STATIONS[station_name]


def get_station_name(station_code: str) -> str:
    """
    取得車站名稱

    Args:
        station_code: 車站代碼

    Returns:
        車站名稱
    """
    return STATION_CODES.get(station_code, "未知車站")


def validate_stations(departure: str, arrival: str) -> bool:
    """
    驗證出發站和到達站

    Args:
        departure: 出發站
        arrival: 到達站

    Returns:
        是否有效
    """
    if departure not in STATIONS:
        raise ValueError(f"無效的出發站: {departure}")
    if arrival not in STATIONS:
        raise ValueError(f"無效的到達站: {arrival}")
    if departure == arrival:
        raise ValueError("出發站和到達站不能相同")
    return True
