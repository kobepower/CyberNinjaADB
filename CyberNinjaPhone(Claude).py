import sys
import subprocess
import os
import json
import time
import socket
import threading
import platform
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QCheckBox, QLineEdit, QFileDialog, QTextEdit, QComboBox, QGroupBox, 
    QDialog, QTableWidget, QTableWidgetItem, QInputDialog, QMessageBox,
    QSpinBox, QSlider, QTabWidget, QListWidget, QSplitter, QMenu,
    QSystemTrayIcon, QAction
)
from PyQt5.QtGui import QFont, QMovie, QIcon, QPixmap, QTextCursor
from PyQt5.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty, 
    pyqtSignal, pyqtSlot, QThread, QMutex, QMutexLocker
)

# Configuration constants
CONFIG_FILE = "scrcpy_config.json"
DEVICES_FILE = "devices.json"
PROFILES_FILE = "profiles.json"
LOG_FILE = "cyberphone_log.txt"
DEFAULT_BITRATE = "8M"
DEFAULT_MAX_SIZE = "1440"
DEFAULT_FPS = 60
SCAN_TIMEOUT = 0.1
RECONNECT_INTERVAL = 10
MAX_RECONNECT_ATTEMPTS = 3
ADB_TIMEOUT = 5

class DeviceStatus(Enum):
    """Device connection status enumeration"""
    ONLINE = "Online"
    OFFLINE = "Offline"
    CONNECTING = "Connecting"
    UNKNOWN = "Unknown"
    ERROR = "Error"

class ConnectionMode(Enum):
    """Device connection mode enumeration"""
    USB = "usb"
    WIRELESS = "wireless"
    UNKNOWN = "unknown"

@dataclass
class Device:
    """Device information dataclass"""
    id: str
    name: str = ""
    status: DeviceStatus = DeviceStatus.UNKNOWN
    mode: ConnectionMode = ConnectionMode.UNKNOWN
    ip: str = ""
    port: int = 5555
    last_seen: Optional[datetime] = None
    properties: Dict = field(default_factory=dict)

@dataclass
class Profile:
    """Scrcpy configuration profile"""
    name: str
    bitrate: str = DEFAULT_BITRATE
    max_size: str = DEFAULT_MAX_SIZE
    fps: int = DEFAULT_FPS
    fullscreen: bool = False
    record: bool = False
    stay_awake: bool = True
    show_touches: bool = False
    no_audio: bool = False
    custom_options: str = ""

class NetworkScanner(QThread):
    """Threaded network scanner for device discovery"""
    device_found = pyqtSignal(str, str)  # ip, port
    scan_complete = pyqtSignal(list)  # List of found devices
    progress = pyqtSignal(int)  # Progress percentage
    
    def __init__(self, ip_base: str = "192.168.1", port: int = 5555):
        super().__init__()
        self.ip_base = ip_base
        self.port = port
        self.stop_scan = False
        
    def run(self):
        """Scan network for ADB devices"""
        found_devices = []
        for i in range(1, 255):
            if self.stop_scan:
                break
                
            ip = f"{self.ip_base}.{i}"
            self.progress.emit(int((i / 254) * 100))
            
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(SCAN_TIMEOUT)
                result = sock.connect_ex((ip, self.port))
                sock.close()
                
                if result == 0:
                    # Try ADB connection
                    try:
                        cmd = ["adb", "connect", f"{ip}:{self.port}"]
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
                        
                        if "connected" in result.stdout.lower():
                            found_devices.append((ip, str(self.port)))
                            self.device_found.emit(ip, str(self.port))
                    except Exception:
                        pass
            except Exception:
                pass
                
        self.scan_complete.emit(found_devices)
        
    def stop(self):
        """Stop the network scan"""
        self.stop_scan = True
        self.wait()

class DeviceMonitor(QThread):
    """Monitor device connections and status"""
    status_changed = pyqtSignal(str, str)  # device_id, status
    device_connected = pyqtSignal(str)
    device_disconnected = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.monitoring = True
        self.devices = {}
        self.mutex = QMutex()
        
    def run(self):
        """Monitor device status continuously"""
        while self.monitoring:
            try:
                result = subprocess.run(
                    ["adb", "devices"], 
                    capture_output=True, 
                    text=True, 
                    timeout=ADB_TIMEOUT
                )
                
                current_devices = {}
                for line in result.stdout.splitlines()[1:]:
                    if "\t" in line:
                        device_id, status = line.split("\t")
                        current_devices[device_id] = status
                
                with QMutexLocker(self.mutex):
                    # Check for new devices
                    for device_id, status in current_devices.items():
                        if device_id not in self.devices:
                            self.device_connected.emit(device_id)
                        elif self.devices[device_id] != status:
                            self.status_changed.emit(device_id, status)
                    
                    # Check for disconnected devices
                    for device_id in self.devices:
                        if device_id not in current_devices:
                            self.device_disconnected.emit(device_id)
                    
                    self.devices = current_devices
                    
            except Exception as e:
                print(f"Device monitor error: {e}")
                
            time.sleep(2)
    
    def stop(self):
        """Stop monitoring"""
        self.monitoring = False
        self.wait()

class AnimatedButton(QPushButton):
    """Custom animated button with hover effects"""
    def __init__(self, text: str, icon: str = None):
        super().__init__(text)
        self._animation = None
        self._glow = 0
        if icon:
            self.setText(f"{icon} {text}")
        self.setupAnimation()
        self.updateStyle()
        
    def setupAnimation(self):
        """Setup hover animation"""
        self._animation = QPropertyAnimation(self, b"glow")
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.InOutQuad)
        
    @pyqtProperty(int)
    def glow(self):
        return self._glow
        
    @glow.setter
    def glow(self, value):
        self._glow = value
        self.updateStyle()
        
    def updateStyle(self):
    #"""Update button style based on glow value"""
     glow_color = f"rgba(0, 200, 255, {self._glow})"
     self.setStyleSheet(f"""
        QPushButton {{
            background-color: #001f3f;
            color: #00c8ff;
            border: 2px solid #00c8ff;
            border-radius: 5px;
            padding: 8px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: #003366;
            border: 2px solid #00ffff;
            border-color: {glow_color};
            border-width: {max(2, self._glow//10)}px;
        }}
        QPushButton:pressed {{
            background-color: #004477;
        }}
    """)
        
    def enterEvent(self, event):
        """Handle mouse enter"""
        if self._animation:
            self._animation.setStartValue(0)
            self._animation.setEndValue(20)
            self._animation.start()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        """Handle mouse leave"""
        if self._animation:
            self._animation.setStartValue(self._glow)
            self._animation.setEndValue(0)
            self._animation.start()
        super().leaveEvent(event)

class DeviceManagerDialog(QDialog):
    """Enhanced device management dialog"""
    def __init__(self, parent, devices: Dict[str, Device]):
        super().__init__(parent)
        self.devices = devices
        self.initUI()
        
    def initUI(self):
        """Initialize the user interface"""
        self.setWindowTitle("📱 Device Manager")
        self.setModal(True)
        self.setMinimumSize(600, 400)
        
        # Apply dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #000814;
                color: #00c8ff;
            }
            QTableWidget {
                background-color: #001f3f;
                color: #00c8ff;
                border: 1px solid #00c8ff;
                gridline-color: #003366;
            }
            QHeaderView::section {
                background-color: #002244;
                color: #00c8ff;
                padding: 5px;
                border: 1px solid #00c8ff;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Device table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Device ID", "Name", "Status", "Mode", "Last Seen"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.showContextMenu)
        
        self.updateTable()
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.btn_refresh = AnimatedButton("Refresh", "🔄")
        self.btn_add = AnimatedButton("Add Device", "➕")
        self.btn_edit = AnimatedButton("Edit", "✏️")
        self.btn_delete = AnimatedButton("Delete", "🗑️")
        self.btn_export = AnimatedButton("Export", "💾")
        
        self.btn_refresh.clicked.connect(self.refreshDevices)
        self.btn_add.clicked.connect(self.addDevice)
        self.btn_edit.clicked.connect(self.editDevice)
        self.btn_delete.clicked.connect(self.deleteDevice)
        self.btn_export.clicked.connect(self.exportDevices)
        
        button_layout.addWidget(self.btn_refresh)
        button_layout.addWidget(self.btn_add)
        button_layout.addWidget(self.btn_edit)
        button_layout.addWidget(self.btn_delete)
        button_layout.addWidget(self.btn_export)
        button_layout.addStretch()
        
        layout.addWidget(self.table)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def updateTable(self):
        """Update the device table"""
        self.table.setRowCount(len(self.devices))
        
        for row, (device_id, device) in enumerate(self.devices.items()):
            self.table.setItem(row, 0, QTableWidgetItem(device.id))
            self.table.setItem(row, 1, QTableWidgetItem(device.name))
            self.table.setItem(row, 2, QTableWidgetItem(device.status.value))
            self.table.setItem(row, 3, QTableWidgetItem(device.mode.value))
            
            last_seen = device.last_seen.strftime("%Y-%m-%d %H:%M:%S") if device.last_seen else "Never"
            self.table.setItem(row, 4, QTableWidgetItem(last_seen))
            
            # Color code based on status
            status_item = self.table.item(row, 2)
            if device.status == DeviceStatus.ONLINE:
                status_item.setForeground(Qt.green)
            elif device.status == DeviceStatus.OFFLINE:
                status_item.setForeground(Qt.red)
            else:
                status_item.setForeground(Qt.yellow)
                
    def showContextMenu(self, position):
        """Show context menu for device actions"""
        menu = QMenu(self)
        
        connect_action = QAction("Connect", self)
        disconnect_action = QAction("Disconnect", self)
        properties_action = QAction("Properties", self)
        
        connect_action.triggered.connect(self.connectDevice)
        disconnect_action.triggered.connect(self.disconnectDevice)
        properties_action.triggered.connect(self.showProperties)
        
        menu.addAction(connect_action)
        menu.addAction(disconnect_action)
        menu.addSeparator()
        menu.addAction(properties_action)
        
        menu.exec_(self.table.mapToGlobal(position))
        
    def refreshDevices(self):
        """Refresh device list"""
        # Trigger parent's device update
        self.parent().updateDeviceList()
        self.updateTable()
        
    def addDevice(self):
        """Add a new device manually"""
        dialog = QInputDialog(self)
        dialog.setWindowTitle("Add Device")
        dialog.setLabelText("Enter device IP:Port (e.g., 192.168.1.100:5555):")
        
        if dialog.exec_():
            device_id = dialog.textValue()
            if ":" not in device_id:
                device_id += ":5555"
                
            device = Device(
                id=device_id,
                name=f"Device_{len(self.devices) + 1}",
                mode=ConnectionMode.WIRELESS
            )
            self.devices[device_id] = device
            self.updateTable()
            
    def editDevice(self):
        """Edit selected device"""
        row = self.table.currentRow()
        if row >= 0:
            device_id = self.table.item(row, 0).text()
            device = self.devices.get(device_id)
            
            if device:
                name, ok = QInputDialog.getText(
                    self, "Edit Device", "Device Name:", 
                    text=device.name
                )
                if ok:
                    device.name = name
                    self.updateTable()
                    
    def deleteDevice(self):
        """Delete selected device"""
        row = self.table.currentRow()
        if row >= 0:
            device_id = self.table.item(row, 0).text()
            
            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Delete device {device_id}?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                del self.devices[device_id]
                self.updateTable()
                
    def connectDevice(self):
        """Connect to selected device"""
        row = self.table.currentRow()
        if row >= 0:
            device_id = self.table.item(row, 0).text()
            self.parent().connectToDevice(device_id)
            
    def disconnectDevice(self):
        """Disconnect from selected device"""
        row = self.table.currentRow()
        if row >= 0:
            device_id = self.table.item(row, 0).text()
            self.parent().disconnectFromDevice(device_id)
            
    def showProperties(self):
        """Show device properties"""
        row = self.table.currentRow()
        if row >= 0:
            device_id = self.table.item(row, 0).text()
            device = self.devices.get(device_id)
            
            if device:
                props = json.dumps(device.properties, indent=2)
                QMessageBox.information(
                    self, f"Device Properties - {device_id}",
                    props
                )
                
    def exportDevices(self):
        """Export device list to file"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Devices", "devices_export.json",
            "JSON Files (*.json)"
        )
        
        if filename:
            export_data = {}
            for device_id, device in self.devices.items():
                export_data[device_id] = {
                    "name": device.name,
                    "status": device.status.value,
                    "mode": device.mode.value,
                    "properties": device.properties
                }
                
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
                
            QMessageBox.information(
                self, "Export Complete",
                f"Devices exported to {filename}"
            )

class CyberPhoneNinja(QWidget):
    """Main application window"""
    
    # Signals
    device_list_updated = pyqtSignal()
    log_message = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.devices = {}
        self.profiles = {}
        self.current_profile = None
        self.scrcpy_processes = {}
        self.network_scanner = None
        self.device_monitor = None
        
        self.initUI()
        self.loadConfiguration()
        self.startMonitoring()
        
    def initUI(self):
        """Initialize the user interface"""
        self.setWindowTitle("🥷 CyberNinjaPhone - Android Controller")
        self.setGeometry(100, 100, 900, 700)
        
        # Apply dark cyber theme
        self.setStyleSheet("""
            QWidget {
                background-color: #000814;
                color: #00c8ff;
                font-family: 'Consolas', 'Monaco', monospace;
            }
            QGroupBox {
                border: 2px solid #00c8ff;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #00ffff;
            }
            QLineEdit, QTextEdit, QComboBox, QSpinBox {
                background-color: #001f3f;
                color: #00c8ff;
                border: 1px solid #00c8ff;
                padding: 5px;
                border-radius: 3px;
            }
            QTabWidget::pane {
                border: 1px solid #00c8ff;
                background-color: #000814;
            }
            QTabBar::tab {
                background-color: #001f3f;
                color: #00c8ff;
                padding: 8px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #003366;
                border-bottom: 2px solid #00ffff;
            }
        """)
        
        # Main layout
        main_layout = QVBoxLayout()
        
        # Title
        title = QLabel("🥷 CyberNinjaPhone - Android Controller")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #00ffff;
            padding: 10px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #001f3f, stop:0.5 #003366, stop:1 #001f3f);
            border-radius: 5px;
        """)
        main_layout.addWidget(title)
        
        # Tab widget
        tabs = QTabWidget()
        
        # Connection tab
        connection_tab = self.createConnectionTab()
        tabs.addTab(connection_tab, "🔌 Connection")
        
        # Control tab
        control_tab = self.createControlTab()
        tabs.addTab(control_tab, "🎮 Control")
        
        # Recording tab
        recording_tab = self.createRecordingTab()
        tabs.addTab(recording_tab, "🎥 Recording")
        
        # Profiles tab
        profiles_tab = self.createProfilesTab()
        tabs.addTab(profiles_tab, "💾 Profiles")
        
        # Advanced tab
        advanced_tab = self.createAdvancedTab()
        tabs.addTab(advanced_tab, "⚙️ Advanced")
        
        main_layout.addWidget(tabs)
        
        # Log output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(150)
        self.log_output.setStyleSheet("""
            background-color: #000000;
            color: #00ff00;
            font-family: monospace;
            font-size: 12px;
            border: 1px solid #00ff00;
        """)
        
        log_group = QGroupBox("📋 System Log")
        log_layout = QVBoxLayout()
        log_layout.addWidget(self.log_output)
        
        # Log controls
        log_controls = QHBoxLayout()
        self.btn_clear_log = AnimatedButton("Clear", "🗑️")
        self.btn_save_log = AnimatedButton("Save", "💾")
        self.btn_clear_log.clicked.connect(self.clearLog)
        self.btn_save_log.clicked.connect(self.saveLog)
        
        log_controls.addWidget(self.btn_clear_log)
        log_controls.addWidget(self.btn_save_log)
        log_controls.addStretch()
        
        log_layout.addLayout(log_controls)
        log_group.setLayout(log_layout)
        
        main_layout.addWidget(log_group)
        
        # Status bar
        self.status_label = QLabel("⚡ System Ready")
        self.status_label.setStyleSheet("""
            background-color: #001f3f;
            color: #00ffff;
            padding: 5px;
            border: 1px solid #00c8ff;
            border-radius: 3px;
        """)
        main_layout.addWidget(self.status_label)
        
        self.setLayout(main_layout)
        
        # Connect signals
        self.log_message.connect(self.log)
        
        # Setup system tray
        self.setupSystemTray()
        
    def createConnectionTab(self):
        """Create connection management tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Device selection
        device_group = QGroupBox("Device Selection")
        device_layout = QVBoxLayout()
        
        # Device combo
        device_row = QHBoxLayout()
        self.device_combo = QComboBox()
        self.btn_refresh = AnimatedButton("Refresh", "🔄")
        self.btn_manage = AnimatedButton("Manage", "📋")
        
        self.btn_refresh.clicked.connect(self.updateDeviceList)
        self.btn_manage.clicked.connect(self.openDeviceManager)
        
        device_row.addWidget(QLabel("Device:"))
        device_row.addWidget(self.device_combo, 1)
        device_row.addWidget(self.btn_refresh)
        device_row.addWidget(self.btn_manage)
        
        device_layout.addLayout(device_row)
        
        # Connection mode
        mode_row = QHBoxLayout()
        self.radio_usb = QCheckBox("USB")
        self.radio_wireless = QCheckBox("Wireless")
        self.radio_wireless.toggled.connect(self.toggleWirelessMode)
        
        mode_row.addWidget(QLabel("Mode:"))
        mode_row.addWidget(self.radio_usb)
        mode_row.addWidget(self.radio_wireless)
        mode_row.addStretch()
        
        device_layout.addLayout(mode_row)
        
        # Wireless settings
        self.wireless_group = QGroupBox("Wireless Settings")
        wireless_layout = QVBoxLayout()
        
        ip_row = QHBoxLayout()
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.100")
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(5555)
        
        ip_row.addWidget(QLabel("IP:"))
        ip_row.addWidget(self.ip_input)
        ip_row.addWidget(QLabel("Port:"))
        ip_row.addWidget(self.port_spin)
        
        wireless_layout.addLayout(ip_row)
        
        # Network scan
        scan_row = QHBoxLayout()
        self.btn_scan = AnimatedButton("Scan Network", "🔍")
        self.btn_connect_wifi = AnimatedButton("Connect", "📶")
        self.scan_progress = QLabel("")
        
        self.btn_scan.clicked.connect(self.scanNetwork)
        self.btn_connect_wifi.clicked.connect(self.connectWireless)
        
        scan_row.addWidget(self.btn_scan)
        scan_row.addWidget(self.btn_connect_wifi)
        scan_row.addWidget(self.scan_progress)
        scan_row.addStretch()
        
        wireless_layout.addLayout(scan_row)
        
        self.wireless_group.setLayout(wireless_layout)
        self.wireless_group.setEnabled(False)
        
        device_layout.addWidget(self.wireless_group)
        device_group.setLayout(device_layout)
        
        # Quick actions
        quick_group = QGroupBox("Quick Actions")
        quick_layout = QHBoxLayout()
        
        self.btn_connect = AnimatedButton("Connect", "🔗")
        self.btn_disconnect = AnimatedButton("Disconnect", "⛓️")
        self.btn_reconnect = AnimatedButton("Reconnect All", "🔄")
        
        self.btn_connect.clicked.connect(self.connectDevice)
        self.btn_disconnect.clicked.connect(self.disconnectDevice)
        self.btn_reconnect.clicked.connect(self.reconnectAll)
        
        quick_layout.addWidget(self.btn_connect)
        quick_layout.addWidget(self.btn_disconnect)
        quick_layout.addWidget(self.btn_reconnect)
        quick_layout.addStretch()
        
        quick_group.setLayout(quick_layout)
        
        layout.addWidget(device_group)
        layout.addWidget(quick_group)
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
        
    def createControlTab(self):
        """Create device control tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Display settings
        display_group = QGroupBox("Display Settings")
        display_layout = QVBoxLayout()
        
        # Resolution
        res_row = QHBoxLayout()
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "Original", "1920x1080", "1440x900", "1280x720", 
            "1024x768", "800x600", "Custom"
        ])
        
        res_row.addWidget(QLabel("Resolution:"))
        res_row.addWidget(self.resolution_combo)
        res_row.addStretch()
        
        display_layout.addLayout(res_row)
        
        # Bitrate
        bitrate_row = QHBoxLayout()
        self.bitrate_input = QLineEdit(DEFAULT_BITRATE)
        self.bitrate_slider = QSlider(Qt.Horizontal)
        self.bitrate_slider.setRange(1, 50)
        self.bitrate_slider.setValue(8)
        self.bitrate_slider.valueChanged.connect(
            lambda v: self.bitrate_input.setText(f"{v}M")
        )
        
        bitrate_row.addWidget(QLabel("Bitrate:"))
        bitrate_row.addWidget(self.bitrate_input)
        bitrate_row.addWidget(self.bitrate_slider)
        
        display_layout.addLayout(bitrate_row)
        
        # FPS
        fps_row = QHBoxLayout()
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 120)
        self.fps_spin.setValue(DEFAULT_FPS)
        
        fps_row.addWidget(QLabel("FPS:"))
        fps_row.addWidget(self.fps_spin)
        fps_row.addStretch()
        
        display_layout.addLayout(fps_row)
        
        # Options
        options_row = QHBoxLayout()
        self.check_fullscreen = QCheckBox("Fullscreen")
        self.check_always_on_top = QCheckBox("Always on Top")
        self.check_no_control = QCheckBox("View Only")
        
        options_row.addWidget(self.check_fullscreen)
        options_row.addWidget(self.check_always_on_top)
        options_row.addWidget(self.check_no_control)
        
        display_layout.addLayout(options_row)
        
        display_group.setLayout(display_layout)
        
        # Launch controls
        launch_group = QGroupBox("Launch Controls")
        launch_layout = QVBoxLayout()
        
        # Single device
        single_row = QHBoxLayout()
        self.btn_launch = AnimatedButton("Launch Scrcpy", "🚀")
        self.btn_stop = AnimatedButton("Stop", "⏹️")
        
        self.btn_launch.clicked.connect(self.launchScrcpy)
        self.btn_stop.clicked.connect(self.stopScrcpy)
        
        single_row.addWidget(self.btn_launch)
        single_row.addWidget(self.btn_stop)
        single_row.addStretch()
        
        launch_layout.addLayout(single_row)
        
        # Multi device
        multi_row = QHBoxLayout()
        self.btn_launch_all = AnimatedButton("Launch All", "🚀")
        self.btn_stop_all = AnimatedButton("Stop All", "⏹️")
        
        self.btn_launch_all.clicked.connect(self.launchAllDevices)
        self.btn_stop_all.clicked.connect(self.stopAllDevices)
        
        multi_row.addWidget(self.btn_launch_all)
        multi_row.addWidget(self.btn_stop_all)
        multi_row.addStretch()
        
        launch_layout.addLayout(multi_row)
        
        launch_group.setLayout(launch_layout)
        
        layout.addWidget(display_group)
        layout.addWidget(launch_group)
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
        
    def createRecordingTab(self):
        """Create recording settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Recording settings
        record_group = QGroupBox("Recording Settings")
        record_layout = QVBoxLayout()
        
        # Enable recording
        self.check_record = QCheckBox("Enable Recording")
        record_layout.addWidget(self.check_record)
        
        # File settings
        file_row = QHBoxLayout()
        self.record_path = QLineEdit("recording.mp4")
        self.btn_browse_record = AnimatedButton("Browse", "📁")
        self.btn_browse_record.clicked.connect(self.browseRecordPath)
        
        file_row.addWidget(QLabel("Output File:"))
        file_row.addWidget(self.record_path)
        file_row.addWidget(self.btn_browse_record)
        
        record_layout.addLayout(file_row)
        
        # Format
        format_row = QHBoxLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp4", "mkv", "webm"])
        
        format_row.addWidget(QLabel("Format:"))
        format_row.addWidget(self.format_combo)
        format_row.addStretch()
        
        record_layout.addLayout(format_row)
        
        # Time limit
        time_row = QHBoxLayout()
        self.check_time_limit = QCheckBox("Time Limit (seconds):")
        self.time_limit_spin = QSpinBox()
        self.time_limit_spin.setRange(1, 3600)
        self.time_limit_spin.setValue(300)
        self.time_limit_spin.setEnabled(False)
        
        self.check_time_limit.toggled.connect(self.time_limit_spin.setEnabled)
        
        time_row.addWidget(self.check_time_limit)
        time_row.addWidget(self.time_limit_spin)
        time_row.addStretch()
        
        record_layout.addLayout(time_row)
        
        record_group.setLayout(record_layout)
        
        # Recording control
        control_group = QGroupBox("Recording Control")
        control_layout = QHBoxLayout()
        
        self.btn_start_record = AnimatedButton("Start Recording", "🔴")
        self.btn_pause_record = AnimatedButton("Pause", "⏸️")
        self.btn_stop_record = AnimatedButton("Stop", "⏹️")
        
        self.btn_start_record.clicked.connect(self.startRecording)
        self.btn_pause_record.clicked.connect(self.pauseRecording)
        self.btn_stop_record.clicked.connect(self.stopRecording)
        
        control_layout.addWidget(self.btn_start_record)
        control_layout.addWidget(self.btn_pause_record)
        control_layout.addWidget(self.btn_stop_record)
        control_layout.addStretch()
        
        control_group.setLayout(control_layout)
        
        layout.addWidget(record_group)
        layout.addWidget(control_group)
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
        
    def createProfilesTab(self):
        """Create profiles management tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Profile list
        profile_group = QGroupBox("Saved Profiles")
        profile_layout = QVBoxLayout()
        
        self.profile_list = QListWidget()
        self.profile_list.itemDoubleClicked.connect(self.loadProfile)
        
        profile_layout.addWidget(self.profile_list)
        
        # Profile controls
        profile_controls = QHBoxLayout()
        self.btn_save_profile = AnimatedButton("Save", "💾")
        self.btn_load_profile = AnimatedButton("Load", "📂")
        self.btn_delete_profile = AnimatedButton("Delete", "🗑️")
        
        self.btn_save_profile.clicked.connect(self.saveProfile)
        self.btn_load_profile.clicked.connect(self.loadProfile)
        self.btn_delete_profile.clicked.connect(self.deleteProfile)
        
        profile_controls.addWidget(self.btn_save_profile)
        profile_controls.addWidget(self.btn_load_profile)
        profile_controls.addWidget(self.btn_delete_profile)
        profile_controls.addStretch()
        
        profile_layout.addLayout(profile_controls)
        
        profile_group.setLayout(profile_layout)
        
        layout.addWidget(profile_group)
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
        
    def createAdvancedTab(self):
        """Create advanced settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # ADB settings
        adb_group = QGroupBox("ADB Settings")
        adb_layout = QVBoxLayout()
        
        # ADB path
        adb_path_row = QHBoxLayout()
        self.adb_path = QLineEdit()
        self.btn_browse_adb = AnimatedButton("Browse", "📁")
        self.btn_browse_adb.clicked.connect(self.browseAdbPath)
        
        adb_path_row.addWidget(QLabel("ADB Path:"))
        adb_path_row.addWidget(self.adb_path)
        adb_path_row.addWidget(self.btn_browse_adb)
        
        adb_layout.addLayout(adb_path_row)
        
        # Scrcpy path
        scrcpy_path_row = QHBoxLayout()
        self.scrcpy_path = QLineEdit()
        self.btn_browse_scrcpy = AnimatedButton("Browse", "📁")
        self.btn_browse_scrcpy.clicked.connect(self.browseScrcpyPath)
        
        scrcpy_path_row.addWidget(QLabel("Scrcpy Path:"))
        scrcpy_path_row.addWidget(self.scrcpy_path)
        scrcpy_path_row.addWidget(self.btn_browse_scrcpy)
        
        adb_layout.addLayout(scrcpy_path_row)
        
        adb_group.setLayout(adb_layout)
        
        # Custom options
        custom_group = QGroupBox("Custom Options")
        custom_layout = QVBoxLayout()
        
        self.custom_options = QTextEdit()
        self.custom_options.setPlaceholderText(
            "Enter custom scrcpy options, one per line:\n"
            "--no-audio\n"
            "--stay-awake\n"
            "--show-touches"
        )
        self.custom_options.setMaximumHeight(100)
        
        custom_layout.addWidget(self.custom_options)
        
        custom_group.setLayout(custom_layout)
        
        # ADB Terminal
        terminal_group = QGroupBox("ADB Terminal")
        terminal_layout = QVBoxLayout()
        
        cmd_row = QHBoxLayout()
        self.adb_command = QLineEdit()
        self.adb_command.setPlaceholderText("Enter ADB command...")
        self.btn_run_adb = AnimatedButton("Run", "▶️")
        self.btn_run_adb.clicked.connect(self.runAdbCommand)
        
        cmd_row.addWidget(self.adb_command)
        cmd_row.addWidget(self.btn_run_adb)
        
        terminal_layout.addLayout(cmd_row)
        
        self.adb_output = QTextEdit()
        self.adb_output.setReadOnly(True)
        self.adb_output.setMaximumHeight(100)
        self.adb_output.setStyleSheet("""
            background-color: #000000;
            color: #00ff00;
            font-family: monospace;
        """)
        
        terminal_layout.addWidget(self.adb_output)
        
        terminal_group.setLayout(terminal_layout)
        
        layout.addWidget(adb_group)
        layout.addWidget(custom_group)
        layout.addWidget(terminal_group)
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
        
    def setupSystemTray(self):
        """Setup system tray icon and menu"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
            
        self.tray_icon = QSystemTrayIcon(self)
        
        # Create tray menu
        tray_menu = QMenu()
        
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        
        hide_action = QAction("Hide", self)
        hide_action.triggered.connect(self.hide)
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(hide_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        
        # Set icon (create a simple one if no icon file exists)
        icon = QIcon()
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        icon.addPixmap(pixmap)
        self.tray_icon.setIcon(icon)
        
        self.tray_icon.setToolTip("CyberPhone Ninja")
        self.tray_icon.show()
        
    def toggleWirelessMode(self, checked):
        """Toggle wireless mode settings"""
        self.wireless_group.setEnabled(checked)
        
    def scanNetwork(self):
        """Scan network for devices"""
        if self.network_scanner and self.network_scanner.isRunning():
            self.log("Network scan already in progress")
            return
            
        ip_base = ".".join(self.ip_input.text().split(".")[:3]) if self.ip_input.text() else "192.168.1"
        port = self.port_spin.value()
        
        self.network_scanner = NetworkScanner(ip_base, port)
        self.network_scanner.device_found.connect(self.onDeviceFound)
        self.network_scanner.scan_complete.connect(self.onScanComplete)
        self.network_scanner.progress.connect(
            lambda p: self.scan_progress.setText(f"Scanning... {p}%")
        )
        
        self.log(f"Starting network scan on {ip_base}.0/24:{port}")
        self.network_scanner.start()
        
    def onDeviceFound(self, ip, port):
        """Handle device found during scan"""
        device_id = f"{ip}:{port}"
        self.log(f"Found device: {device_id}")
        
        device = Device(
            id=device_id,
            name=ip,
            status=DeviceStatus.ONLINE,
            mode=ConnectionMode.WIRELESS,
            ip=ip,
            port=int(port),
            last_seen=datetime.now()
        )
        
        self.devices[device_id] = device
        self.updateDeviceCombo()
        
    def onScanComplete(self, devices):
        """Handle scan completion"""
        self.scan_progress.setText("")
        self.log(f"Network scan complete. Found {len(devices)} device(s)")
        
    def connectWireless(self):
        """Connect to wireless device"""
        ip = self.ip_input.text()
        port = self.port_spin.value()
        
        if not ip:
            self.log("Please enter an IP address")
            return
            
        device_id = f"{ip}:{port}"
        self.connectToDevice(device_id)
        
    def connectDevice(self):
        """Connect to selected device"""
        device_id = self.device_combo.currentData()
        if device_id:
            self.connectToDevice(device_id)
            
    def connectToDevice(self, device_id):
        """Connect to a specific device"""
        try:
            self.log(f"Connecting to {device_id}...")
            
            result = subprocess.run(
                ["adb", "connect", device_id],
                capture_output=True,
                text=True,
                timeout=ADB_TIMEOUT
            )
            
            if "connected" in result.stdout.lower():
                self.log(f"Successfully connected to {device_id}")
                
                device = self.devices.get(device_id, Device(id=device_id))
                device.status = DeviceStatus.ONLINE
                device.last_seen = datetime.now()
                self.devices[device_id] = device
                
                self.updateStatus(f"Connected to {device_id}")
            else:
                self.log(f"Failed to connect: {result.stdout}")
                
        except Exception as e:
            self.log(f"Connection error: {e}")
            
    def disconnectDevice(self):
        """Disconnect from selected device"""
        device_id = self.device_combo.currentData()
        if device_id:
            self.disconnectFromDevice(device_id)
            
    def disconnectFromDevice(self, device_id):
        """Disconnect from a specific device"""
        try:
            self.log(f"Disconnecting from {device_id}...")
            
            result = subprocess.run(
                ["adb", "disconnect", device_id],
                capture_output=True,
                text=True,
                timeout=ADB_TIMEOUT
            )
            
            self.log(f"Disconnected: {result.stdout}")
            
            if device_id in self.devices:
                self.devices[device_id].status = DeviceStatus.OFFLINE
                
            self.updateStatus(f"Disconnected from {device_id}")
            
        except Exception as e:
            self.log(f"Disconnect error: {e}")
            
    def reconnectAll(self):
        """Reconnect to all known devices"""
        self.log("Reconnecting to all devices...")
        
        for device_id in self.devices:
            self.connectToDevice(device_id)
            
    def launchScrcpy(self):
        """Launch scrcpy for selected device"""
        device_id = self.device_combo.currentData()
        if not device_id:
            self.log("No device selected")
            return
            
        self.launchScrcpyForDevice(device_id)
        
    def launchScrcpyForDevice(self, device_id):
        """Launch scrcpy for specific device"""
        if not self.scrcpy_path.text():
            self.log("Scrcpy path not configured")
            return
            
        # Build command
        cmd = [self.scrcpy_path.text(), "-s", device_id]
        
        # Add display options
        if self.bitrate_input.text():
            cmd.extend(["--video-bit-rate", self.bitrate_input.text()])
            
        if self.fps_spin.value():
            cmd.extend(["--max-fps", str(self.fps_spin.value())])
            
        if self.check_fullscreen.isChecked():
            cmd.append("--fullscreen")
            
        if self.check_always_on_top.isChecked():
            cmd.append("--always-on-top")
            
        if self.check_no_control.isChecked():
            cmd.append("--no-control")
            
        # Add recording options
        if self.check_record.isChecked():
            cmd.extend(["--record", self.record_path.text()])
            
            if self.check_time_limit.isChecked():
                cmd.extend(["--time-limit", str(self.time_limit_spin.value())])
                
        # Add custom options
        custom = self.custom_options.toPlainText().strip()
        if custom:
            cmd.extend(custom.split())
            
        # Launch process
        try:
            self.log(f"Launching: {' '.join(cmd)}")
            process = subprocess.Popen(cmd)
            self.scrcpy_processes[device_id] = process
            self.log(f"Scrcpy launched for {device_id}")
            
        except Exception as e:
            self.log(f"Failed to launch scrcpy: {e}")
            
    def stopScrcpy(self):
        """Stop scrcpy for selected device"""
        device_id = self.device_combo.currentData()
        if device_id and device_id in self.scrcpy_processes:
            self.stopScrcpyForDevice(device_id)
            
    def stopScrcpyForDevice(self, device_id):
        """Stop scrcpy for specific device"""
        if device_id in self.scrcpy_processes:
            process = self.scrcpy_processes[device_id]
            process.terminate()
            del self.scrcpy_processes[device_id]
            self.log(f"Stopped scrcpy for {device_id}")
            
    def launchAllDevices(self):
        """Launch scrcpy for all connected devices"""
        for device_id, device in self.devices.items():
            if device.status == DeviceStatus.ONLINE:
                self.launchScrcpyForDevice(device_id)
                
    def stopAllDevices(self):
        """Stop all scrcpy processes"""
        for device_id in list(self.scrcpy_processes.keys()):
            self.stopScrcpyForDevice(device_id)
            
    def startRecording(self):
        """Start recording"""
        device_id = self.device_combo.currentData()
        if not device_id:
            self.log("No device selected")
            return
            
        # If scrcpy is running, need to restart with recording
        if device_id in self.scrcpy_processes:
            self.stopScrcpyForDevice(device_id)
            
        self.check_record.setChecked(True)
        self.launchScrcpyForDevice(device_id)
        
    def pauseRecording(self):
        """Pause recording (not directly supported by scrcpy)"""
        self.log("Recording pause not supported. Stop and restart to pause.")
        
    def stopRecording(self):
        """Stop recording"""
        device_id = self.device_combo.currentData()
        if device_id and device_id in self.scrcpy_processes:
            self.stopScrcpyForDevice(device_id)
            self.log(f"Recording saved to {self.record_path.text()}")
            
    def saveProfile(self):
        """Save current settings as profile"""
        name, ok = QInputDialog.getText(self, "Save Profile", "Profile Name:")
        if ok and name:
            profile = Profile(
                name=name,
                bitrate=self.bitrate_input.text(),
                max_size=self.resolution_combo.currentText(),
                fps=self.fps_spin.value(),
                fullscreen=self.check_fullscreen.isChecked(),
                record=self.check_record.isChecked()
            )
            
            self.profiles[name] = profile
            self.updateProfileList()
            self.saveProfiles()
            self.log(f"Profile '{name}' saved")
            
    def loadProfile(self):
        """Load selected profile"""
        item = self.profile_list.currentItem()
        if item:
            name = item.text()
            profile = self.profiles.get(name)
            
            if profile:
                self.bitrate_input.setText(profile.bitrate)
                self.fps_spin.setValue(profile.fps)
                self.check_fullscreen.setChecked(profile.fullscreen)
                self.check_record.setChecked(profile.record)
                
                self.current_profile = profile
                self.log(f"Profile '{name}' loaded")
                
    def deleteProfile(self):
        """Delete selected profile"""
        item = self.profile_list.currentItem()
        if item:
            name = item.text()
            
            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Delete profile '{name}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                del self.profiles[name]
                self.updateProfileList()
                self.saveProfiles()
                self.log(f"Profile '{name}' deleted")
                
    def updateProfileList(self):
        """Update profile list widget"""
        self.profile_list.clear()
        for name in self.profiles:
            self.profile_list.addItem(name)
            
    def browseRecordPath(self):
        """Browse for recording output file"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Recording As", 
            self.record_path.text(),
            "Video Files (*.mp4 *.mkv *.webm)"
        )
        if filename:
            self.record_path.setText(filename)
            
    def browseAdbPath(self):
        """Browse for ADB executable"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select ADB Executable",
            "", "Executable (*.exe)" if platform.system() == "Windows" else "All Files (*)"
        )
        if filename:
            self.adb_path.setText(filename)
            
    def browseScrcpyPath(self):
        """Browse for scrcpy executable"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Scrcpy Executable",
            "", "Executable (*.exe)" if platform.system() == "Windows" else "All Files (*)"
        )
        if filename:
            self.scrcpy_path.setText(filename)
            
    def runAdbCommand(self):
        """Run custom ADB command"""
        cmd = self.adb_command.text().strip()
        if not cmd:
            return
            
        device_id = self.device_combo.currentData()
        
        try:
            full_cmd = ["adb"]
            if device_id:
                full_cmd.extend(["-s", device_id])
            full_cmd.extend(cmd.split())
            
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=ADB_TIMEOUT
            )
            
            output = result.stdout + result.stderr
            self.adb_output.setText(output)
            
        except Exception as e:
            self.adb_output.setText(f"Error: {e}")
            
    def openDeviceManager(self):
        """Open device manager dialog"""
        dialog = DeviceManagerDialog(self, self.devices)
        dialog.exec_()
        self.updateDeviceCombo()
        
    def updateDeviceList(self):
        """Update device list from ADB"""
        try:
            result = subprocess.run(
                ["adb", "devices"],
                capture_output=True,
                text=True,
                timeout=ADB_TIMEOUT
            )
            
            for line in result.stdout.splitlines()[1:]:
                if "\t" in line:
                    device_id, status = line.split("\t")
                    
                    device = self.devices.get(device_id, Device(id=device_id))
                    device.status = DeviceStatus.ONLINE if status == "device" else DeviceStatus.OFFLINE
                    device.mode = ConnectionMode.WIRELESS if ":" in device_id else ConnectionMode.USB
                    device.last_seen = datetime.now()
                    
                    self.devices[device_id] = device
                    
            self.updateDeviceCombo()
            
        except Exception as e:
            self.log(f"Failed to update device list: {e}")
            
    def updateDeviceCombo(self):
        """Update device combo box"""
        self.device_combo.clear()
        
        for device_id, device in self.devices.items():
            display = f"{device.name or device_id} ({device.status.value})"
            self.device_combo.addItem(display, device_id)
            
    def startMonitoring(self):
        """Start device monitoring"""
        self.device_monitor = DeviceMonitor()
        self.device_monitor.device_connected.connect(
            lambda d: self.log(f"Device connected: {d}")
        )
        self.device_monitor.device_disconnected.connect(
            lambda d: self.log(f"Device disconnected: {d}")
        )
        self.device_monitor.status_changed.connect(
            lambda d, s: self.log(f"Device {d} status: {s}")
        )
        self.device_monitor.start()
        
    def log(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_output.append(f"[{timestamp}] {message}")
        
        # Auto-scroll to bottom
        cursor = self.log_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_output.setTextCursor(cursor)
        
        # Also write to file
        try:
            with open(LOG_FILE, "a") as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass
            
    def clearLog(self):
        """Clear log output"""
        self.log_output.clear()
        
    def saveLog(self):
        """Save log to file"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Log", 
            f"cyberphone_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt)"
        )
        
        if filename:
            with open(filename, "w") as f:
                f.write(self.log_output.toPlainText())
            self.log(f"Log saved to {filename}")
            
    def updateStatus(self, message):
        """Update status bar"""
        self.status_label.setText(f"⚡ {message}")
        
    def loadConfiguration(self):
        """Load saved configuration"""
        # Load main config
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    
                self.scrcpy_path.setText(config.get("scrcpy_path", ""))
                self.adb_path.setText(config.get("adb_path", ""))
                self.bitrate_input.setText(config.get("bitrate", DEFAULT_BITRATE))
                self.fps_spin.setValue(config.get("fps", DEFAULT_FPS))
                self.check_fullscreen.setChecked(config.get("fullscreen", False))
                self.check_record.setChecked(config.get("record", False))
                self.record_path.setText(config.get("record_path", "recording.mp4"))
                
            except Exception as e:
                self.log(f"Failed to load config: {e}")
                
        # Load devices
        if os.path.exists(DEVICES_FILE):
            try:
                with open(DEVICES_FILE, "r") as f:
                    devices_data = json.load(f)
                    
                for device_id, data in devices_data.items():
                    device = Device(
                        id=device_id,
                        name=data.get("name", ""),
                        status=DeviceStatus(data.get("status", "Unknown")),
                        mode=ConnectionMode(data.get("mode", "unknown"))
                    )
                    self.devices[device_id] = device
                    
                self.updateDeviceCombo()
                
            except Exception as e:
                self.log(f"Failed to load devices: {e}")
                
        # Load profiles
        self.loadProfiles()
        
    def saveConfiguration(self):
        """Save current configuration"""
        config = {
            "scrcpy_path": self.scrcpy_path.text(),
            "adb_path": self.adb_path.text(),
            "bitrate": self.bitrate_input.text(),
            "fps": self.fps_spin.value(),
            "fullscreen": self.check_fullscreen.isChecked(),
            "record": self.check_record.isChecked(),
            "record_path": self.record_path.text()
        }
        
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
            
        # Save devices
        devices_data = {}
        for device_id, device in self.devices.items():
            devices_data[device_id] = {
                "name": device.name,
                "status": device.status.value,
                "mode": device.mode.value
            }
            
        with open(DEVICES_FILE, "w") as f:
            json.dump(devices_data, f, indent=2)
            
    def loadProfiles(self):
        """Load saved profiles"""
        if os.path.exists(PROFILES_FILE):
            try:
                with open(PROFILES_FILE, "r") as f:
                    profiles_data = json.load(f)
                    
                for name, data in profiles_data.items():
                    profile = Profile(name=name, **data)
                    self.profiles[name] = profile
                    
                self.updateProfileList()
                
            except Exception as e:
                self.log(f"Failed to load profiles: {e}")
                
    def saveProfiles(self):
        """Save profiles to file"""
        profiles_data = {}
        for name, profile in self.profiles.items():
            profiles_data[name] = asdict(profile)
            
        with open(PROFILES_FILE, "w") as f:
            json.dump(profiles_data, f, indent=2)
            
    def closeEvent(self, event):
        """Handle application close"""
        # Stop all processes
        self.stopAllDevices()
        
        # Stop monitoring
        if self.device_monitor:
            self.device_monitor.stop()
            
        # Stop network scanner
        if self.network_scanner and self.network_scanner.isRunning():
            self.network_scanner.stop()
            
        # Save configuration
        self.saveConfiguration()
        
        event.accept()

def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = CyberPhoneNinja()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()