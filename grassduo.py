import asyncio
import aiofiles
import random
import ssl
import json
import time
import uuid
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
import csv
import os
import sys

# 从CSV文件中读取代理列表
async def read_proxies_from_csv(file_path, proxy_type):
    proxies = []
    try:
        async with aiofiles.open(file_path, 'r') as csvfile:
            async for row in csvfile:
                proxy = row.strip()
                if proxy_type == "http":
                    proxies.append(f"http://{proxy}")
                elif proxy_type == "socks5":
                    proxies.append(f"socks5://{proxy}")
                else:
                    logger.error("Invalid proxy type. Supported types are 'http' and 'socks5'.")
    except Exception as e:
        logger.error(f"Error reading proxies from CSV: {e}")
    return proxies

# 与WebSocket代理建立连接并保持通信
async def connect_to_wss(proxy, user_id, reconnect_interval):
    while True:
        try:
            device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, proxy))
            logger.info(device_id)
            # 谷歌浏览器模拟状态列表
            chrome_versions = [
                "Chrome/58.0.3029.110",
                "Chrome/65.0.3325.181",
                "Chrome/70.0.3538.77",
                "Chrome/85.0.4183.121",
                "Chrome/91.0.4472.124"
            ]
            # 随机选择一个谷歌浏览器模拟状态
            user_agent = random.choice(chrome_versions)
            custom_headers = {
                "User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) {user_agent} Safari/537.3"
            }
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            uri = "wss://proxy.wynd.network:4650/"
            server_hostname = "proxy.wynd.network"
            proxy_instance = Proxy.from_url(proxy)
            async with proxy_connect(uri, proxy=proxy_instance, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:
                async def send_ping():
                    while True:
                        send_message = json.dumps(
                            {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}})
                        logger.debug(send_message)
                        await websocket.send(send_message)
                        await asyncio.sleep(20)

                await asyncio.sleep(1)
                asyncio.create_task(send_ping())

                while True:
                    response = await websocket.recv()
                    message = json.loads(response)
                    logger.info(message)
                    if message.get("action") == "AUTH":
                        auth_response = {
                            "id": message["id"],
                            "origin_action": "AUTH",
                            "result": {
                                "browser_id": device_id,
                                "user_id": user_id,
                                "user_agent": custom_headers['User-Agent'],
                                "timestamp": int(time.time()),
                                "device_type": "extension",
                                "version": "2.5.0"
                            }
                        }
                        logger.debug(auth_response)
                        await websocket.send(json.dumps(auth_response))

                    elif message.get("action") == "PONG":
                        pong_response = {"id": message["id"], "origin_action": "PONG"}
                        logger.debug(pong_response)
                        await websocket.send(json.dumps(pong_response))
        except Exception as e:
            logger.error(e)
            logger.error(f"Failed to connect to proxy: {proxy}")
        finally:
            await asyncio.sleep(reconnect_interval)

# 主函数，负责读取CSV文件中的代理并发起连接
async def main():
    if len(sys.argv) != 5:
        print("Usage: python3 grassduo.py <proxy_type> <file_path> <reconnect_interval> <user_id>")
        sys.exit(1)

    proxy_type = sys.argv[1].lower()
    file_path = sys.argv[2]
    reconnect_interval = int(sys.argv[3])
    user_id = sys.argv[4]

    proxies = await read_proxies_from_csv(file_path, proxy_type)
    if proxies:
        tasks = [connect_to_wss(proxy, user_id, reconnect_interval) for proxy in proxies]
        await asyncio.gather(*tasks)
    else:
        logger.error("No proxies found in the CSV file.")

# 运行主函数
if __name__ == "__main__":
    asyncio.run(main())
