# 小米手环心率监测应用

一个基于Python和PyQt5开发的小米手环心率监测应用，支持实时心率数据显示和悬浮窗功能。

## 功能特点

- 🔍 蓝牙设备扫描和连接
- 💓 实时心率数据监测
- 📊 心率数据可视化显示
- 🪟 可定制的悬浮窗UI
- ⚙️ 自动重连和设备管理
- 📱 支持多种小米手环型号

## 系统要求

- Windows 10/11
- Python 3.7+
- 蓝牙4.0以上支持

## 安装方法

### 1. 克隆仓库
```bash
git clone https://github.com/yourusername/XiaomiHype.git
cd XiaomiHype
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 运行应用
```bash
python main.py
```

## 使用说明

1. 启动应用后，点击"扫描"按钮搜索附近的蓝牙设备
2. 在设备列表中选择您的小米手环
3. 点击"连接设备"按钮建立连接
4. 连接成功后，应用将显示实时心率数据
5. 点击"悬浮窗 UI 选项"可以配置悬浮窗显示
6. 点击"断开连接"按钮断开与设备的连接

## 项目结构

```
XiaomiHype/
├── main.py              # 主应用程序
├── requirements.txt     # 项目依赖
├── README.md           # 项目说明
├── .gitignore         # Git忽略文件
└── test/              # 测试文件
    ├── test_bleak.py
    ├── test_scan.py
    └── test_thread_scan.py
```

## 技术栈

- **Python 3** - 编程语言
- **PyQt5** - GUI框架
- **Bleak** - 蓝牙低功耗库
- **Asyncio** - 异步编程支持

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 联系方式

如有问题或建议，请联系项目维护者。
