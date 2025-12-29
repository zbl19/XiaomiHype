import sys
import asyncio
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QComboBox, QPushButton,
    QVBoxLayout, QHBoxLayout, QSlider, QCheckBox, QDialog, QMessageBox, QGroupBox
)
from PyQt5.QtCore import QPoint
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QPalette, QColor
from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

# HRS服务和特征值UUID
HRS_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
HEART_RATE_CHAR_UUID = "00002a37-0000-1000-8000-00805f9b34fb"
HRS_SERVICE_SHORT_UUID = 0x180D
HEART_RATE_MEASUREMENT_CHAR_SHORT_UUID = 0x2A37

# 默认设备MAC地址（可配置）
DEFAULT_DEVICE_MAC = ""

class ScanThread(QThread):
    """扫描蓝牙设备的线程"""
    scan_finished = pyqtSignal(list)
    scan_failed = pyqtSignal(str)
    advertisement_received = pyqtSignal(BLEDevice, AdvertisementData)
    
    def run(self):
        """运行扫描任务"""
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 扫描蓝牙设备并接收广告数据
            loop.run_until_complete(self._scan_devices())
        except Exception as e:
            self.scan_failed.emit(str(e))
        finally:
            loop.close()
    
    async def _scan_devices(self):
        """异步扫描所有蓝牙设备并处理广告数据"""
        
        # 用于存储扫描到的设备
        discovered_devices = {}
        
        def callback(device, advertisement_data):
            """广告数据回调函数"""
            # 存储设备
            discovered_devices[device.address] = device
            self.advertisement_received.emit(device, advertisement_data)
        
        # 使用BleakScanner接收广告数据，设置超时时间为10秒
        scanner = BleakScanner(callback)
        
        try:
            # 开始扫描
            await scanner.start()
            # 减少扫描时间到5秒，提高连接速度
            await asyncio.sleep(5.0)
        except Exception as e:
            print(f"扫描过程中发生错误: {str(e)}")
            self.scan_failed.emit(str(e))
        finally:
            await scanner.stop()
        
        # 获取扫描到的所有设备
        devices = list(discovered_devices.values())
        self.scan_finished.emit(devices)


class FloatWindow(QWidget):
    """简约数字样式的悬浮窗"""
    
    def __init__(self):
        super().__init__()
        
        # 悬浮窗设置
        self.is_topmost = True
        self.is_fixed = False
        self.window_size = 150
        self.current_heart_rate = 0
        
        # 初始化界面
        self.setup_ui()
        
    def setup_ui(self):
        """设置悬浮窗界面"""
        # 设置窗口属性
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 设置窗口大小
        self.resize(self.window_size, self.window_size)
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建心率显示标签
        self.heart_rate_label = QLabel(self)
        self.heart_rate_label.setAlignment(Qt.AlignCenter)
        self.heart_rate_label.setStyleSheet(
            f"font-size: {self.window_size // 2}px; "
            f"font-weight: bold; "
            f"color: red;"
        )
        self.heart_rate_label.setText("0")
        
        layout.addWidget(self.heart_rate_label)
        
        # 鼠标事件变量
        self.dragging = False
        self.drag_start_position = QPoint()
        
    def update_heart_rate(self, heart_rate):
        """更新心率显示"""
        self.current_heart_rate = heart_rate
        self.heart_rate_label.setText(str(heart_rate))
    
    def set_topmost(self, is_topmost):
        """设置窗口是否置顶"""
        self.is_topmost = is_topmost
        flags = self.windowFlags()
        if is_topmost:
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
        self.show()
    
    def set_fixed(self, is_fixed):
        """设置窗口是否固定"""
        self.is_fixed = is_fixed
    
    def set_size(self, size):
        """设置窗口大小"""
        self.window_size = size
        self.resize(size, size)
        self.heart_rate_label.setStyleSheet(
            f"font-size: {size // 2}px; "
            f"font-weight: bold; "
            f"color: red;"
        )
        # 确保窗口正确显示更新后的大小
        if self.isVisible():
            self.hide()
            self.show()
    
    # 鼠标事件处理
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if not self.is_fixed and event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_start_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if not self.is_fixed and self.dragging and event.buttons() & Qt.LeftButton:
            new_position = event.globalPos() - self.drag_start_position
            self.move(new_position)
            event.accept()
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            self.dragging = False
            event.accept()
        super().mouseReleaseEvent(event)


# 为HeartRateMonitor类添加缺失的方法
class HeartRateMonitor(QMainWindow):
    """主窗口类"""
    heart_rate_update = pyqtSignal(int)
    connection_status = pyqtSignal(str, bool)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("心率监测控制面板")
        # self.setFixedSize(500, 200)
        
        # 变量初始化
        self.devices = []
        self.selected_device = None
        self.client = None
        self.current_heart_rate = 0
        self.is_scanning = False
        self.is_connected = False
        self.loop = None
        self.connect_task = None
        self.monitor_task = None
        
        # 扫描线程
        self.scan_thread = None
        
        # 悬浮窗
        self.float_window = None
        self.float_window_visible = False
        
        # 用于存储支持HRS的设备
        self.hrs_devices = {}  # key: device address, value: device
        
        # 设置界面
        self.setup_ui()
        
        # 创建并启动事件循环
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # 使用QTimer定期处理事件循环
        self.event_loop_timer = QTimer()
        self.event_loop_timer.timeout.connect(self._process_event_loop)
        self.event_loop_timer.start(100)  # 每100毫秒处理一次事件循环
        
        # 连接信号
        self.heart_rate_update.connect(self._on_heart_rate_updated)
        self.connection_status.connect(self._on_connection_status_changed)
    
    def setup_ui(self):
        """设置主界面布局"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 第一行：蓝牙设备选择和扫描按钮
        row1_layout = QHBoxLayout()
        device_label = QLabel("蓝牙设备:")
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(200)
        self.scan_button = QPushButton("扫描")
        self.scan_button.setStyleSheet("background-color: blue; color: white;")
        self.scan_button.clicked.connect(self._on_scan_clicked)
        
        row1_layout.addWidget(device_label)
        row1_layout.addWidget(self.device_combo)
        row1_layout.addStretch()
        row1_layout.addWidget(self.scan_button)
        main_layout.addLayout(row1_layout)
        
        # 第二行：连接控制按钮
        row2_layout = QHBoxLayout()
        self.connect_button = QPushButton("连接设备")
        self.connect_button.setStyleSheet("background-color: green; color: white;")
        self.connect_button.clicked.connect(self._on_connect_clicked)
        
        self.disconnect_button = QPushButton("断开连接")
        self.disconnect_button.setStyleSheet("""
            QPushButton {
                background-color: #FF4444; 
                color: white;
                border: none;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #FF6666;
            }
            QPushButton:pressed {
                background-color: #CC0000;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #888888;
            }
        """)
        self.disconnect_button.clicked.connect(self._on_disconnect_clicked)
        self.disconnect_button.setEnabled(False)
        
        row2_layout.addWidget(self.connect_button)
        row2_layout.addWidget(self.disconnect_button)
        main_layout.addLayout(row2_layout)
        
        # 第三行：连接状态显示
        row3_layout = QHBoxLayout()
        status_label = QLabel("连接状态:")
        self.status_value = QLabel("未连接")
        self.status_value.setStyleSheet("color: pink;")
        
        row3_layout.addWidget(status_label)
        row3_layout.addWidget(self.status_value)
        row3_layout.addStretch()
        main_layout.addLayout(row3_layout)
        
        # 第四行：悬浮窗设置区域
        float_group = QGroupBox("悬浮窗设置")
        float_layout = QVBoxLayout(float_group)
        
        # 样式选择
        style_layout = QHBoxLayout()
        style_label = QLabel("显示样式:")
        self.style_combo = QComboBox()
        self.style_combo.addItem("简约数字")
        self.style_combo.addItem("表盘样式")
        self.style_combo.addItem("动态图形")
        style_layout.addWidget(style_label)
        style_layout.addWidget(self.style_combo)
        float_layout.addLayout(style_layout)
        
        # 悬浮窗大小滑块
        size_layout = QHBoxLayout()
        size_label = QLabel("悬浮窗大小:")
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setMinimum(100)
        self.size_slider.setMaximum(200)
        self.size_slider.setValue(150)
        self.size_value = QLabel("150")
        self.size_slider.valueChanged.connect(self._on_size_changed)
        self.size_slider.valueChanged.connect(self._on_size_slider_changed)
        size_layout.addWidget(size_label)
        size_layout.addWidget(self.size_slider)
        size_layout.addWidget(self.size_value)
        float_layout.addLayout(size_layout)
        
        # 复选框和按钮
        controls_layout = QHBoxLayout()
        self.topmost_checkbox = QCheckBox("窗口置顶")
        self.topmost_checkbox.setChecked(True)
        self.topmost_checkbox.toggled.connect(self._on_topmost_changed)
        
        self.fixed_checkbox = QCheckBox("固定位置")
        self.fixed_checkbox.setChecked(False)
        self.fixed_checkbox.toggled.connect(self._on_fixed_changed)
        
        self.float_window_toggle_button = QPushButton("显示悬浮窗")
        self.float_window_toggle_button.clicked.connect(self._toggle_float_window)
        
        controls_layout.addWidget(self.topmost_checkbox)
        controls_layout.addWidget(self.fixed_checkbox)
        controls_layout.addWidget(self.float_window_toggle_button)
        float_layout.addLayout(controls_layout)
        
        main_layout.addWidget(float_group)
    
    def _on_scan_clicked(self):
        """扫描按钮点击事件"""
        if self.is_scanning:
            return
        
        self.is_scanning = True
        self.scan_button.setEnabled(False)
        self.scan_button.setText("扫描中...")
        
        # 清空设备列表
        self.devices = []
        self.device_combo.clear()
        self.hrs_devices = {}
        
        # 启动扫描线程
        self.scan_thread = ScanThread()
        self.scan_thread.scan_finished.connect(self._on_scan_finished)
        self.scan_thread.scan_failed.connect(self._on_scan_failed)
        self.scan_thread.finished.connect(self._on_scan_thread_finished)
        self.scan_thread.advertisement_received.connect(self._on_advertisement_received)
        self.scan_thread.start()
    
    def _on_scan_finished(self, devices):
        """扫描完成回调"""
        # 结合扫描到的设备和从广告数据中检测到的HRS设备
        all_devices = list(self.hrs_devices.values())
        
        # 确保所有扫描到的设备都包含在内
        for device in devices:
            if device.address not in self.hrs_devices:
                all_devices.append(device)
        
        self.devices = all_devices
        self.device_combo.clear()
        
        for device in all_devices:
            device_name = device.name or "未知设备"
            is_hrs = device.address in self.hrs_devices
            hrs_tag = " [HRS]" if is_hrs else ""
            self.device_combo.addItem(f"{device_name} ({device.address}){hrs_tag}")
        
        self.is_scanning = False
        self.scan_button.setEnabled(True)
        self.scan_button.setText("扫描")
    
    def _process_event_loop(self):
        """定期处理事件循环"""
        if self.loop and not self.loop.is_closed():
            # 运行事件循环一小段时间来处理异步任务
            try:
                if not self.loop.is_running():
                    # 如果事件循环没有运行，运行一小段时间
                    self.loop.run_until_complete(asyncio.sleep(0.01))
            except RuntimeError:
                # 忽略可能的运行时错误
                pass

    def _on_scan_thread_finished(self):
        """扫描线程完成回调"""
        self.scan_thread = None

    def _on_advertisement_received(self, device, advertisement_data):
        """广告数据接收回调"""
        # 检查设备是否支持HRS服务
        if self._is_hrs_device(advertisement_data):
            # 存储支持HRS的设备
            if device.address not in self.hrs_devices:
                self.hrs_devices[device.address] = device
            
            # 尝试解析心率数据
            heart_rate = self._parse_heart_rate_from_advertisement(advertisement_data)
            if heart_rate is not None:
                # 发送心率更新信号
                self.heart_rate_update.emit(heart_rate)
    
    def _is_hrs_device(self, advertisement_data):
        """检查设备是否支持HRS服务"""
        # 检查服务UUID列表中是否包含HRS服务
        if HRS_SERVICE_UUID.lower() in advertisement_data.service_uuids:
            return True
        
        # 检查16位UUID是否包含HRS服务
        if hasattr(advertisement_data, 'service_data'):
            for uuid in advertisement_data.service_data:
                if uuid.startswith("0x180d") or uuid == str(HRS_SERVICE_SHORT_UUID):
                    return True
        
        return False
    
    def _parse_heart_rate_from_advertisement(self, advertisement_data):
        """从广告数据中解析心率值"""
        if not hasattr(advertisement_data, 'service_data'):
            return None
        
        # 查找HRS服务数据
        for uuid, data in advertisement_data.service_data.items():
            if uuid.startswith("0x180d") or uuid == str(HRS_SERVICE_SHORT_UUID):
                # 解析心率数据 (根据HRS协议)
                if len(data) >= 2:  # 至少需要2个字节：标志位 + 心率值
                    try:
                        flags = data[0]
                        if flags & 0x01:  # 检查是否使用UINT16格式
                            if len(data) >= 3:
                                heart_rate = int.from_bytes(data[1:3], byteorder='little')
                            else:
                                heart_rate = data[1]
                        else:
                            heart_rate = data[1]
                        return heart_rate
                    except (IndexError, ValueError) as e:
                        print(f"解析心率数据失败: {str(e)}")
                        print(f"数据: {data}")
        
        return None
    
    def _on_scan_failed(self, error_msg):
        """扫描失败回调"""
        print(f"扫描失败: {error_msg}")
        self.is_scanning = False
        self.scan_button.setEnabled(True)
        self.scan_button.setText("扫描")
        QMessageBox.warning(self, "扫描失败", f"蓝牙扫描失败: {error_msg}")
    
    def _on_connect_clicked(self):
        """连接设备按钮点击事件"""
        if self.device_combo.currentIndex() == -1:
            self.status_value.setText("请先选择设备")
            return
        
        # 断开现有连接
        if self.client:
            try:
                # 尝试停止通知和断开连接
                if self.client.is_connected:
                    # 使用异步方式处理断开连接，但立即执行
                    def disconnect_sync():
                        try:
                            # 同步方式执行异步操作
                            if self.loop and not self.loop.is_closed():
                                self.loop.run_until_complete(self.client.stop_notify(HEART_RATE_CHAR_UUID))
                                self.loop.run_until_complete(self.client.disconnect())
                        except Exception as e:
                            print(f"断开连接失败: {str(e)}")
                    
                    # 在事件循环中执行断开连接操作
                    if self.loop and not self.loop.is_closed():
                        self.loop.call_soon_threadsafe(disconnect_sync)
            except Exception as e:
                print(f"断开连接过程中发生错误: {str(e)}")
            finally:
                # 无论如何都清理资源
                self.client = None
        
        # 更新状态
        self.is_connected = False
        self.current_heart_rate = 0
        self.disconnect_button.setEnabled(False)
        self.connection_status.emit("未连接", False)
        
        # 连接选中设备
        self.selected_device = self.devices[self.device_combo.currentIndex()]
        self.loop.create_task(self._connect_to_device(self.selected_device))
        
        # 不要过早启用断开按钮，等连接成功后再启用
        # self.disconnect_button.setEnabled(True)
    
    async def _connect_to_device(self, device):
        """异步连接设备"""
        try:
            self.connection_status.emit("连接中...", False)
            # 优化：直接传入device对象而不是地址，避免内部二次扫描，显著提高连接速度
            # 设置较长的超时时间以适应不同设备，但通常会很快连接
            self.client = BleakClient(device, timeout=20.0)
            
            await self.client.connect()
            if self.client.is_connected:
                # 极简连接：直接启动心率特征值通知，不进行任何其他操作
                # 避免触发小米手环对批量读取的保护机制
                self.is_connected = True
                self.connection_status.emit("已连接", True)
                
                # 仅操作目标特征值：心率测量特征值（0x2A37）
                await self.client.start_notify(HEART_RATE_CHAR_UUID, self._heart_rate_callback)
                
                # 记录成功连接信息
                print(f"成功连接到设备 {device.address}，已启动心率通知")
            else:
                self.connection_status.emit("连接失败", False)
        except Exception as e:
            import traceback
            print(f"连接设备时发生错误: {str(e)}")
            traceback.print_exc()
            self.connection_status.emit(f"连接失败: {str(e)}", False)
            self.is_connected = False
    
    def _heart_rate_callback(self, sender, data):
        """心率数据回调函数"""
        if data[0] & 0x01:  # 检查是否使用UINT16格式
            heart_rate = int.from_bytes(data[1:3], byteorder='little')
        else:
            heart_rate = data[1]
        self.heart_rate_update.emit(heart_rate)
    
    def _on_connection_status_changed(self, status, connected):
        """连接状态变化回调"""
        if connected:
            if self.current_heart_rate > 0:
                self.status_value.setText(f"{status} (心率: {self.current_heart_rate} bpm)")
                self.status_value.setStyleSheet("color: green;")
            else:
                self.status_value.setText(status)
                self.status_value.setStyleSheet("color: green;")
            
            # 只要连接成功，就允许断开
            self.disconnect_button.setEnabled(True)
        else:
            self.status_value.setText(status)
            self.status_value.setStyleSheet("color: pink;")
            self.disconnect_button.setEnabled(False)
    
    def _on_heart_rate_updated(self, heart_rate):
        """心率数据更新回调"""
        self.current_heart_rate = heart_rate
        if self.is_connected:
            self.status_value.setText(f"已连接 (心率: {heart_rate} bpm)")
            self.status_value.setStyleSheet("color: green;")
        
        # 更新悬浮窗心率
        if self.float_window and self.float_window_visible:
            self.float_window.update_heart_rate(heart_rate)
    
    
    
    
    async def _disconnect_device(self):
        """异步断开设备连接任务"""
        try:
            if self.client and self.client.is_connected:
                print("正在断开连接...")
                try:
                    await self.client.stop_notify(HEART_RATE_CHAR_UUID)
                except Exception as e:
                    print(f"停止通知失败 (可能已断开): {str(e)}")
                
                await self.client.disconnect()
                print("设备已断开连接")
        except Exception as e:
            print(f"断开连接失败: {str(e)}")
        finally:
            # 清理资源
            self.client = None
            self.is_connected = False
            self.current_heart_rate = 0
            self.disconnect_button.setEnabled(False)
            self.connection_status.emit("未连接", False)
            print("断开连接操作完成")

    def _on_disconnect_clicked(self):
        """断开连接按钮点击事件"""
        print("断开连接按钮被点击")
        self.disconnect_button.setEnabled(False) # 防止重复点击
        
        if self.client:
            # 如果 Loop 可用且未关闭，创建断开连接任务
            if self.loop and not self.loop.is_closed():
                self.loop.create_task(self._disconnect_device())
            else:
                # 如果 Loop 不可用，直接清理状态
                print("Event loop不可用，强制清理状态")
                self.client = None
                self.is_connected = False
                self.current_heart_rate = 0
                self.connection_status.emit("未连接", False)
    
    def _toggle_float_window(self):
        """切换悬浮窗显示状态"""
        if self.float_window_visible:
            self.hide_float_window()
        else:
            self.show_float_window()
    
    def show_float_window(self):
        """显示悬浮窗"""
        if not self.float_window:
            self.float_window = FloatWindow()
            # 应用当前设置
            self.float_window.set_size(self.size_slider.value())
            self.float_window.set_topmost(self.topmost_checkbox.isChecked())
            self.float_window.set_fixed(self.fixed_checkbox.isChecked())
            
        self.float_window.show()
        self.float_window_visible = True
        self.float_window_toggle_button.setText("隐藏悬浮窗")
        self.float_window_toggle_button.setStyleSheet("background-color: blue; color: white;")
        
        # 如果当前有心率数据，更新悬浮窗
        if self.current_heart_rate > 0:
            self.float_window.update_heart_rate(self.current_heart_rate)
    
    def hide_float_window(self):
        """隐藏悬浮窗"""
        if self.float_window and self.float_window_visible:
            self.float_window.hide()
            self.float_window_visible = False
            self.float_window_toggle_button.setText("显示悬浮窗")
            self.float_window_toggle_button.setStyleSheet("") # 恢复默认样式
    
    def _on_size_changed(self, value):
        """滑块值变化处理"""
        self.size_value.setText(str(value))
    
    def _on_size_slider_changed(self, value):
        """大小滑块实时变化处理"""
        if self.float_window:
            self.float_window.set_size(value)
    
    def _on_topmost_changed(self, checked):
        """窗口置顶状态实时变化处理"""
        if self.float_window:
            self.float_window.set_topmost(checked)
    
    def _on_fixed_changed(self, checked):
        """窗口固定状态实时变化处理"""
        if self.float_window:
            self.float_window.set_fixed(checked)
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止事件循环定时器
        if hasattr(self, 'event_loop_timer') and self.event_loop_timer.isActive():
            self.event_loop_timer.stop()
        
        # 使用与断开连接按钮相同的逻辑断开连接
        if self.client:
            try:
                # 尝试停止通知和断开连接
                if self.client.is_connected and self.loop and not self.loop.is_closed():
                    # 同步方式执行异步断开连接操作
                    try:
                        self.loop.run_until_complete(self.client.stop_notify(HEART_RATE_CHAR_UUID))
                        self.loop.run_until_complete(self.client.disconnect())
                    except Exception as e:
                        print(f"断开连接失败: {str(e)}")
            except Exception as e:
                print(f"断开连接过程中发生错误: {str(e)}")
            finally:
                # 清理资源
                self.client = None
        
        # 更新状态
        self.is_connected = False
        self.current_heart_rate = 0
        self.disconnect_button.setEnabled(False)
        
        # 终止扫描线程
        if self.scan_thread and self.scan_thread.isRunning():
            self.scan_thread.terminate()
            self.scan_thread.wait()
        
        # 关闭事件循环
        if self.loop:
            if self.loop.is_running():
                self.loop.stop()
            self.loop.close()
        
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
    app.setPalette(palette)
    
    window = HeartRateMonitor()
    window.show()
    
    sys.exit(app.exec_())