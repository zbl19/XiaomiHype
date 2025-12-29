import sys
print(f"Python版本: {sys.version}")
print(f"Python路径: {sys.executable}")

try:
    from bleak import BleakScanner, BleakClient
    print("成功导入bleak库")
except ImportError as e:
    print(f"导入bleak库失败: {e}")
    import os
    print(f"当前工作目录: {os.getcwd()}")
    print("系统PATH:")
    for path in sys.path:
        print(f"  {path}")