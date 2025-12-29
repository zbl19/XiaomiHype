import sys
import asyncio
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from bleak import BleakScanner

class ScanThread(QThread):
    scan_finished = pyqtSignal(list)
    scan_failed = pyqtSignal(str)
    
    def run(self):
        print("ScanThread开始运行")
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            print("创建事件循环完成")
            
            devices = loop.run_until_complete(self._scan_devices())
            print(f"扫描完成，找到 {len(devices)} 个设备")
            self.scan_finished.emit(devices)
        except Exception as e:
            print(f"扫描线程异常: {e}")
            self.scan_failed.emit(str(e))
        finally:
            loop.close()
            print("事件循环已关闭")
    
    async def _scan_devices(self):
        print("开始异步扫描...")
        devices = await asyncio.wait_for(BleakScanner.discover(), timeout=10)
        return list(devices)

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("线程扫描测试")
        self.setFixedSize(400, 200)
        self.setup_ui()
        
        self.scan_thread = None
        self.is_scanning = False
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.scan_button = QPushButton("开始扫描")
        self.scan_button.clicked.connect(self._on_scan_clicked)
        layout.addWidget(self.scan_button)
        
        self.status_label = QLabel("准备就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
    
    def _on_scan_clicked(self):
        if self.is_scanning:
            return
        
        print("点击扫描按钮")
        self.is_scanning = True
        self.scan_button.setEnabled(False)
        self.scan_button.setText("扫描中...")
        self.status_label.setText("开始扫描...")
        
        # 启动扫描线程
        self.scan_thread = ScanThread()
        self.scan_thread.scan_finished.connect(self._on_scan_finished)
        self.scan_thread.scan_failed.connect(self._on_scan_failed)
        self.scan_thread.finished.connect(lambda: setattr(self, "scan_thread", None))
        self.scan_thread.start()
    
    def _on_scan_finished(self, devices):
        print(f"扫描完成回调，设备数: {len(devices)}")
        self.status_label.setText(f"扫描完成，找到 {len(devices)} 个设备")
        self.is_scanning = False
        self.scan_button.setEnabled(True)
        self.scan_button.setText("开始扫描")
        
        # 打印设备信息
        for device in devices:
            device_name = device.name or "未知设备"
            print(f"  {device_name} ({device.address})")
    
    def _on_scan_failed(self, error_msg):
        print(f"扫描失败回调: {error_msg}")
        self.status_label.setText(f"扫描失败: {error_msg}")
        self.is_scanning = False
        self.scan_button.setEnabled(True)
        self.scan_button.setText("开始扫描")

if __name__ == "__main__":
    print("启动应用程序")
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_())
