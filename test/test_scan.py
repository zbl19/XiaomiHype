import asyncio
from bleak import BleakScanner

async def test_scan():
    print("开始扫描蓝牙设备...")
    try:
        # 测试基本扫描功能，设置10秒超时
        devices = await BleakScanner.discover(timeout=10)
        print(f"扫描完成，找到 {len(devices)} 个设备:")
        for device in devices:
            device_name = device.name or "未知设备"
            print(f"  {device_name} ({device.address})")
        return devices
    except Exception as e:
        print(f"扫描失败: {e}")
        return []

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        devices = loop.run_until_complete(test_scan())
        print(f"测试结果: 找到 {len(devices)} 个设备")
    except Exception as e:
        print(f"测试出错: {e}")
    finally:
        loop.close()
