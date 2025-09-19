import requests
import time
from datetime import datetime, timedelta
import os

# 配置 Server酱
SERVER_CHAN_KEY = "Paste Your ServerChan SendKey Here"
SERVER_CHAN_URL = f"https://sctapi.ftqq.com/{SERVER_CHAN_KEY}.send"

# Apple 门店
STORES = {
    "R428": "Apple ifc mall",
    "R409": "Apple Causeway Bay",
    "R499": "Apple Canton Road",
    "R485": "Apple Festival Walk",
    "R673": "Apple apm Hong Kong",
    "R610": "Apple New Town Plaza"
}

# 香港地区查询地址
BASE_URL = "https://www.apple.com/hk/shop/fulfillment-messages"
PARAMS_TEMPLATE = {
    "pl": "true",
    "parts.0": "MG6L4ZA/A" # iPhone 17 256GB iPhone 17 256GB 霧藍色
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/129.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json"
}


def clear_screen():
    """清屏"""
    os.system('cls' if os.name == 'nt' else 'clear')


def push_notification(title, desp=""):
    """通过 Server酱推送消息"""
    try:
        resp = requests.post(SERVER_CHAN_URL, data={"title": title, "desp": desp}, timeout=10)
        if resp.status_code == 200:
            print(f"📢 已推送通知：{title}")
        else:
            print(f"⚠️ 推送失败: {resp.text}")
    except Exception as e:
        print(f"⚠️ 推送出错: {e}")


def check_store(store_code, store_name):
    """查询某个 Apple Store 的 pickup 状态"""
    params = PARAMS_TEMPLATE.copy()
    params["store"] = store_code

    try:
        response = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        store_info = data["body"]["content"]["pickupMessage"]["stores"][0]
        pickup_display = store_info["partsAvailability"]["MG6L4ZA/A"]["pickupDisplay"]

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if pickup_display == "available":
            print(f"{now} 🟢 {store_code} {store_name} - 有货")
            return True, now
        else:
            print(f"{now} 🔴 {store_code} {store_name} - 无货")
            return False, None

    except Exception as e:
        print(f"⚠️ 查询 {store_code} {store_name} 出错: {e}")
        return False, None


def main():
    print("🚀 Apple iPhone 门店库存监控程序启动！开始监控门店库存情况 🔍📱")
    print("=" * 60)

    # 程序启动通知
    push_notification("🚀 Apple 库存监控已启动", "🔍 已开始实时监控各门店库存，请保持关注 📱")

    round_num = 1
    last_stock_times = {code: None for code in STORES}  # 每家店上次有货时间
    last_heartbeat = datetime.now()  # 上次心跳推送时间

    while True:
        start_time = time.perf_counter()
        print(f"\n🕒 第 {round_num} 轮查询开始...")
        has_stock = False

        for code, name in STORES.items():
            available, stock_time = check_store(code, name)
            if available:
                has_stock = True
                last_stock_times[code] = stock_time
                # 🔔 有货时立即推送
                push_notification(
                    "🟢 iPhone 有货提醒",
                    f"⏰ 时间：{stock_time}\n🏬 门店：{code} {name}\n📱 快去下单！"
                )
            time.sleep(1)

        elapsed = time.perf_counter() - start_time
        clear_screen()

        # 查询总结
        print("=" * 60)
        if has_stock:
            print(f"✅ 第 {round_num} 轮查询结束：有门店有货！")
        else:
            print(f"❌ 第 {round_num} 轮查询结束：所有门店暂无库存。")
        print(f"⏱️ 本轮总用时：{elapsed:.2f} 秒")

        print("\n📌 各门店上次有货时间：")
        for code, name in STORES.items():
            if last_stock_times[code]:
                print(f"   {code} {name} - {last_stock_times[code]}")
            else:
                print(f"   {code} {name} - 暂无记录")
        print("=" * 60)

        # 推送心跳通知（每 3 小时）
        now = datetime.now()
        if now - last_heartbeat > timedelta(hours=3):
            push_notification(
                "🫀 心跳通知",
                f"⏰ 时间：{now.strftime('%Y-%m-%d %H:%M:%S')}\n✅ 程序仍在正常运行中。"
            )
            last_heartbeat = now

        round_num += 1
        time.sleep(10)


if __name__ == "__main__":
    main()