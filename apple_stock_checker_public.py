import requests
import time
import logging
from datetime import datetime, timedelta
import os

# ============== 配置区域 ==============
SERVER_CHAN_KEY = "这里填Server酱的Key"
SERVER_CHAN_URL = f"https://sctapi.ftqq.com/{SERVER_CHAN_KEY}.send"

# 多少秒算网络请求超时
REQUEST_TIMEOUT = 15

# 如果一直没货 多久发一次心跳推送证明程序还在运行
HEARTBEAT_INTERVAL_HOURS = 2

# 同一次循环内 两个商店查询之间隔多少秒
STORE_QUERY_INTERVAL = 2

# 查询一轮后 隔多少秒开始下一轮
LOOP_INTERVAL = 10

# 连续报错多少轮就发推送提醒
ERROR_NOTIFY_THRESHOLD = 3

# 推送有货消息后 隔多少分钟才能再发下一次有货推送
STOCK_NOTIFY_INTERVAL_MINUTES = 5

# 为True时 系统时间凌晨1点到5点之间不查询
DO_NOT_DISTURB = True

# 日志配置
LOG_FILE = "monitor.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# Apple 门店映射 这些都是香港的门店
STORES = {
    "R428": "Apple ifc mall",
    "R409": "Apple Causeway Bay",
    "R499": "Apple Canton Road",
    "R485": "Apple Festival Walk",
    "R673": "Apple apm Hong Kong",
    "R610": "Apple New Town Plaza"
}

# MG6L4ZA/A 是 港版 iPhone 17 Pro 256G 蓝色的型号
BASE_URL = "https://www.apple.com/hk/shop/fulfillment-messages"
PARAMS_TEMPLATE = {"pl": "true", "parts.0": "MG6L4ZA/A"}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/129.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json"
}


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def countdown(seconds, reason):
    """倒计时显示"""
    for remaining in range(seconds, 0, -1):
        print(f"\r⏳ 等待中 (原因: {reason}) 剩余: {remaining}s", end="", flush=True)
        time.sleep(1)
    print("\r", end="", flush=True)


def push_notification(title, desp=""):
    """推送通知并写入日志"""
    try:
        resp = requests.post(SERVER_CHAN_URL, data={"title": title, "desp": desp}, timeout=15)
        if resp.status_code == 200:
            msg = f"推送成功：{title}"
            print(f"📢 {msg}")
            logging.info(f"{msg} | 内容: {desp}")
        else:
            msg = f"推送失败: {resp.text}"
            print(f"⚠️ {msg}")
            logging.error(msg)
    except Exception as e:
        msg = f"推送出错: {e}"
        print(f"⚠️ {msg}")
        logging.error(msg)


def check_store(store_code, store_name):
    """查询 Apple Store 的库存并打印耗时"""
    params = PARAMS_TEMPLATE.copy()
    params["store"] = store_code
    start = time.perf_counter()

    try:
        response = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        duration_ms = (time.perf_counter() - start) * 1000

        store_info = data["body"]["content"]["pickupMessage"]["stores"][0]
        pickup_display = store_info["partsAvailability"]["MG6L4ZA/A"]["pickupDisplay"]

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if pickup_display == "available":
            print(f"{now} 🟢 {store_code} {store_name} - 有货 | 耗时 {duration_ms:.2f} ms")
            return True, now, None
        else:
            print(f"{now} 🔴 {store_code} {store_name} - 无货 | 耗时 {duration_ms:.2f} ms")
            return False, None, None

    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        error_msg = f"查询 {store_code} {store_name} 出错: {e} | 耗时 {duration_ms:.2f} ms"
        print(f"⚠️ {error_msg}")
        return False, None, error_msg


def format_stock_summary(last_stock_times):
    lines = ["📌 各门店上次有货时间："]
    for code, name in STORES.items():
        if last_stock_times[code]:
            lines.append(f"- {code} {name}：{last_stock_times[code]}")
        else:
            lines.append(f"- {code} {name}：暂无记录")
    return "\n".join(lines)


def main():
    print("🚀 Apple iPhone 库存监控启动 🔍📱")
    logging.info("程序启动")

    push_notification("🚀 Apple 库存监控已启动", "程序已开始运行")

    round_num = 1
    last_stock_times = {code: None for code in STORES}
    last_heartbeat = datetime.now()
    last_stock_notify = None

    error_streak = 0
    last_error_detail = ""

    while True:
        start_time = time.perf_counter()
        print(f"\n🕒 第 {round_num} 轮查询开始...")

        now_hour = datetime.now().hour
        loop_messages = []

        if DO_NOT_DISTURB and (1 <= now_hour < 5):
            msg = "🌙 免打扰时间段，本轮不执行查询"
            print(msg)
            loop_messages.append("免打扰")
        else:
            had_error = False
            for code, name in STORES.items():
                available, stock_time, error_msg = check_store(code, name)
                if error_msg:
                    had_error = True
                    last_error_detail = error_msg
                    loop_messages.append(f"{code}: ERR")
                elif available:
                    loop_messages.append(f"{code}: 有货")
                    last_stock_times[code] = stock_time
                    now = datetime.now()
                    if (not last_stock_notify 
                        or (now - last_stock_notify > timedelta(minutes=STOCK_NOTIFY_INTERVAL_MINUTES))):
                        push_notification(
                            "🟢 iPhone 有货提醒",
                            f"⏰ 时间：{stock_time}\n🏬 门店：{code} {name}\n📱 快去下单！"
                        )
                        last_stock_notify = now
                        last_heartbeat = now
                else:
                    loop_messages.append(f"{code}: 无货")

                if code != list(STORES.keys())[-1]:
                    countdown(STORE_QUERY_INTERVAL, "查询下一个门店CD")

            if had_error:
                error_streak += 1
            else:
                error_streak = 0

        elapsed = time.perf_counter() - start_time
        clear_screen()
        print("=" * 60)
        print(f"⏱️ 本轮执行用时：{elapsed:.2f} 秒")
        print("\n" + format_stock_summary(last_stock_times))
        print("=" * 60)

        # 每轮写一行日志
        logging.info(f"第 {round_num} 轮结束 | 状态: {', '.join(loop_messages)}")

        if error_streak >= ERROR_NOTIFY_THRESHOLD:
            push_notification("⚠️ 连续报错提醒", f"已连续 {error_streak} 次报错。\n最新错误：{last_error_detail}")
            logging.error(f"连续报错 {error_streak} 次 | 最新错误：{last_error_detail}")
            error_streak = 0

        now = datetime.now()
        if now - last_heartbeat > timedelta(hours=HEARTBEAT_INTERVAL_HOURS):
            push_notification(
                "🫀 心跳通知",
                f"⏰ 时间：{now.strftime('%Y-%m-%d %H:%M:%S')}\n✅ 程序仍在运行。\n\n{format_stock_summary(last_stock_times)}"
            )
            last_heartbeat = now

        round_num += 1
        countdown(LOOP_INTERVAL, "两次查询之间CD")


if __name__ == "__main__":
    main()