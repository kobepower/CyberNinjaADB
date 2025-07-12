import sys
import subprocess
import os
import json
import time
import socket
import threading
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QCheckBox, QLineEdit, QFileDialog, QTextEdit, QComboBox, QGroupBox, QDialog,
    QTableWidget, QTableWidgetItem, QInputDialog
)
from PyQt5.QtGui import QFont, QMovie
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty, QMetaObject, Q_ARG, pyqtSlot

CONFIG_FILE = "scrcpy_config.json"
DEVICES_FILE = "devices.json"

class AnimatedButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._glow = 0
        self.setStyleSheet(self._get_style())

    @pyqtProperty(int)
    def glow(self):
        return self._glow

    @glow.setter
    def glow(self, value):
        self._glow = value
        self.setStyleSheet(self._get_style())

    def _get_style(self):
        return f"""
            QPushButton {{
                background-color: #001f3f;
                color: #00c8ff;
                border: 1px solid #00c8ff;
                padding: 5px;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: #003366;
                border: 2px solid #00c8ff;
            }}
        """

    def enterEvent(self, event):
        self._animate_glow(5)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animate_glow(0)
        super().leaveEvent(event)

    def _animate_glow(self, end_value):
        try:
            anim = QPropertyAnimation(self, b"glow")
            anim.setDuration(200)
            anim.setStartValue(self._glow)
            anim.setEndValue(end_value)
            anim.setEasingCurve(QEasingCurve.InOutQuad)
            anim.start()
        except Exception as e:
            print(f"Animation error: {e}")

class DeviceManagerDialog(QDialog):
    def __init__(self, parent, devices, update_callback):
        super().__init__(parent)
        self.setWindowTitle("🥷📋 Manage Devices")
        self.setStyleSheet("""
            QDialog {
                background-color: #000814;
                color: #00c8ff;
                font-family: Consolas;
            }
            QTableWidget {
                background-color: #001f3f;
                color: #00c8ff;
                border: 1px solid #00c8ff;
            }
            QPushButton {
                background-color: #001f3f;
                color: #00c8ff;
                border: 1px solid #00c8ff;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #003366;
                border: 2px solid #00c8ff;
            }
        """)
        self.setGeometry(150, 150, 500, 400)
        self.devices = devices
        self.update_callback = update_callback

        layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["IP:Port", "Status", "Name"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.update_table()

        button_layout = QHBoxLayout()
        self.btn_refresh = AnimatedButton("🔄🔍 Refresh/Scan")
        self.btn_refresh.clicked.connect(self.refresh_devices)
        self.btn_clear = AnimatedButton("🗑️ Clear All")
        self.btn_clear.clicked.connect(self.clear_all)
        self.btn_add = AnimatedButton("➕ Add Device")
        self.btn_add.clicked.connect(self.add_device)
        self.btn_delete = AnimatedButton("➖ Delete")
        self.btn_delete.clicked.connect(self.delete_device)
        self.btn_help = AnimatedButton("❓ Help")
        self.btn_help.clicked.connect(self.show_help)
        self.btn_save = AnimatedButton("💾 Save")
        self.btn_save.clicked.connect(self.save_changes)
        button_layout.addWidget(self.btn_refresh)
        button_layout.addWidget(self.btn_clear)
        button_layout.addWidget(self.btn_add)
        button_layout.addWidget(self.btn_delete)
        button_layout.addWidget(self.btn_help)
        button_layout.addWidget(self.btn_save)

        layout.addWidget(self.table)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def update_table(self):
        self.table.setRowCount(len(self.devices))
        for row, (ip, data) in enumerate(self.devices.items()):
            self.table.setItem(row, 0, QTableWidgetItem(ip))
            self.table.setItem(row, 1, QTableWidgetItem(data.get("status", "Unknown")))
            self.table.setItem(row, 2, QTableWidgetItem(data.get("name", "")))
        self.table.resizeColumnsToContents()

    def refresh_devices(self):
        def scan():
            ip_base = ".".join(self.parent().ip_input.text().split(".")[:3]) or "192.168.1"
            self.parent().log(f"🔍🌐📱 Scanning network: {ip_base}.0/24 ...")
            new_devices = {}
            for i in range(1, 255):
                ip = f"{ip_base}.{i}"
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.1)
                    result = sock.connect_ex((ip, 5555))
                    sock.close()
                    if result == 0:
                        try:
                            adb_result = subprocess.check_output(["adb", "connect", f"{ip}:5555"], stderr=subprocess.STDOUT, timeout=2)
                            msg = adb_result.decode()
                            if "connected" in msg.lower() or "already connected" in msg.lower():
                                new_devices[f"{ip}:5555"] = {"status": "Online", "name": f"Device_{i}"}
                                self.parent().log(f"✅📱 Found device: {ip}:5555")
                        except Exception:
                            pass
                except Exception:
                    pass
            self.devices.update(new_devices)
            QMetaObject.invokeMethod(self, "update_table", Qt.QueuedConnection)
            self.parent().update_device_list_safely()
            self.parent().log(f"🟢📱🌐 Scan done: {len(new_devices)} new devices")
        threading.Thread(target=scan, daemon=True).start()

    def clear_all(self):
        self.devices.clear()
        self.update_table()
        self.parent().update_device_list_safely()

    def add_device(self):
        ip, ok = QInputDialog.getText(self, "Add Device", "Enter IP:Port (e.g., 192.168.1.100:5555):")
        if ok and ip:
            if ":" not in ip:
                ip += ":5555"
            self.devices[ip] = {"status": "Unknown", "name": ""}
            self.update_table()
            self.parent().update_device_list_safely()

    def delete_device(self):
        selected_rows = self.table.selectedIndexes()
        if not selected_rows:
            self.parent().log("⚠️📋 No device selected to delete")
            return
        row = selected_rows[0].row()
        if 0 <= row < self.table.rowCount():
            ip = self.table.item(row, 0).text()
            if ip in self.devices:
                del self.devices[ip]
                self.update_table()
                self.parent().update_device_list_safely()
                self.parent().log(f"🗑️🥷 Deleted device: {ip}")

    def save_changes(self):
        try:
            with open(DEVICES_FILE, "w") as f:
                json.dump(self.devices, f)
            self.update_callback()
            self.accept()
            self.parent().log("💾🥷 Device list saved!")
        except Exception as e:
            self.parent().log(f"🚨📂 Error saving devices: {str(e)}")

    def show_help(self):
        self.parent().log("❓🥷 For more information, check the README file.")

class CyberScrcpy(QWidget):
    def __init__(self):
        super().__init__()
        try:
            self.setWindowTitle("🥷📱⚔️ CyberPhoneNinja ADB Viewer")
            self.setStyleSheet("""
                QWidget {
                    background-color: #000814;
                    color: #00c8ff;
                    font-family: Consolas;
                }
                QLabel {
                    color: #00c8ff;
                }
                QLineEdit, QTextEdit, QComboBox {
                    background-color: #001f3f;
                    color: #00c8ff;
                    border: 1px solid #00c8ff;
                }
                QCheckBox {
                    color: #00c8ff;
                }
                QGroupBox {
                    color: #00c8ff;
                    border: 1px solid #00c8ff;
                    margin-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 3px 0 3px;
                }
            """)
            self.setGeometry(100, 100, 600, 700)

            font_title = QFont("Consolas", 14, QFont.Bold)
            font_small = QFont("Consolas", 9)

            self.title = QLabel("🔬 CyberNinja Microscope Mode")
            self.title.setFont(font_title)
            self.title.setStyleSheet("margin-bottom: 10px;")

            self.status_label = QLabel("🚨💀🥷Disconnected")
            self.status_label.setFont(font_small)
            self.status_gif = QMovie("loading.gif") if os.path.exists("loading.gif") else None
            if self.status_gif:
                self.status_label.setMovie(self.status_gif)
                self.status_gif.setPaused(True)

            self.device_label = QLabel("Select Device:")
            self.device_combo = QComboBox()
            self.device_combo.currentIndexChanged.connect(self.update_device_selection)

            self.checkbox_wireless = QCheckBox("Enable Wireless Mode")
            self.checkbox_wireless.stateChanged.connect(self.toggle_ip_input)
            self.ip_label = QLabel("Phone IP Address:")
            self.ip_input = QLineEdit()
            self.ip_input.setMinimumWidth(150)
            self.ip_input.setPlaceholderText("192.168.1.100")
            self.btn_scan_ip = AnimatedButton("🔍 Scan Network")
            self.btn_scan_ip.clicked.connect(self.scan_network)
            self.btn_quick_reconnect = AnimatedButton("🔄🦉 Quick Reconnect")
            self.btn_quick_reconnect.clicked.connect(self.quick_reconnect)
            self.btn_wifi_connect = AnimatedButton("📶📡 WiFi Connect")
            self.btn_wifi_connect.clicked.connect(self.wifi_connect)

            self.checkbox_record = QCheckBox("Record Session")
            self.btn_file = AnimatedButton("📂 Choose Record File")
            self.btn_file.clicked.connect(self.choose_record_file)
            self.btn_start_record = AnimatedButton("🔴▶️ Start Recording")
            self.btn_start_record.clicked.connect(self.start_recording)
            self.btn_stop_record = AnimatedButton("🚨⏹️ Stop Recording")
            self.btn_stop_record.clicked.connect(self.stop_recording)
            self.btn_stop_record.setEnabled(False)

            self.checkbox_fullscreen = QCheckBox("Fullscreen")
            self.btn_browse_scrcpy = AnimatedButton("🕵️📁 Locate scrcpy.exe")
            self.btn_browse_scrcpy.clicked.connect(self.choose_scrcpy_path)

            self.bit_rate_label = QLabel("Video Bitrate (e.g. 2M):")
            self.bit_rate_input = QLineEdit("8M")
            self.max_size_label = QLabel("Max Size (e.g. 1024):")
            self.max_size_input = QLineEdit("1440")

            self.custom_options_label = QLabel("Custom scrcpy Options (e.g. --max-fps=30):")
            self.custom_options_input = QLineEdit()

            self.adb_terminal_label = QLabel("⚠️💀🛑 ADB Command Terminal (Use at your own risk)")
            self.adb_input = QLineEdit()
            self.btn_run_adb = AnimatedButton("🧙️🤖 Run ADB Command")
            self.btn_run_adb.clicked.connect(self.run_adb_command)

            self.btn_launch_all = AnimatedButton("🚀🦾🤖 Launch All Devices")
            self.btn_launch_all.clicked.connect(self.launch_all_devices)

            self.btn_start = AnimatedButton("🟢🥷🔓Launch scrcpy")
            self.btn_start.clicked.connect(self.launch_scrcpy)

            self.btn_manage_devices = AnimatedButton("🥷📋 Manage Devices")
            self.btn_manage_devices.clicked.connect(self.manage_devices)

            self.log_output = QTextEdit()
            self.log_output.setReadOnly(True)
            self.log_output.setStyleSheet("background-color: #001f3f; color: #00c8ff;")
            self.log_output.setFont(font_small)

            layout = QVBoxLayout()
            connection_group = QGroupBox("Connection Settings")
            connection_layout = QVBoxLayout()
            connection_layout.addWidget(self.status_label)
            device_row = QHBoxLayout()
            device_row.addWidget(self.device_label)
            device_row.addWidget(self.device_combo)
            connection_layout.addLayout(device_row)
            connection_layout.addWidget(self.checkbox_wireless)
            ip_row = QHBoxLayout()
            ip_row.addWidget(self.ip_label)
            ip_row.addWidget(self.ip_input)
            ip_row.addWidget(self.btn_scan_ip)
            ip_row.addWidget(self.btn_quick_reconnect)
            ip_row.addWidget(self.btn_wifi_connect)
            connection_layout.addLayout(ip_row)
            connection_group.setLayout(connection_layout)
            layout.addWidget(connection_group)

            recording_group = QGroupBox("Recording Settings")
            recording_layout = QHBoxLayout()
            recording_layout.addWidget(self.checkbox_record)
            recording_layout.addWidget(self.btn_file)
            recording_layout.addWidget(self.btn_start_record)
            recording_layout.addWidget(self.btn_stop_record)
            recording_group.setLayout(recording_layout)
            layout.addWidget(recording_group)

            video_group = QGroupBox("Video Settings")
            video_layout = QVBoxLayout()
            bitrate_row = QHBoxLayout()
            bitrate_row.addWidget(self.bit_rate_label)
            bitrate_row.addWidget(self.bit_rate_input)
            video_layout.addLayout(bitrate_row)
            size_row = QHBoxLayout()
            size_row.addWidget(self.max_size_label)
            size_row.addWidget(self.max_size_input)
            video_layout.addLayout(size_row)
            video_layout.addWidget(self.custom_options_label)
            video_layout.addWidget(self.custom_options_input)
            video_group.setLayout(video_layout)
            layout.addWidget(video_group)

            adb_group = QGroupBox("ADB Terminal")
            adb_layout = QHBoxLayout()
            adb_layout.addWidget(self.adb_terminal_label)
            adb_layout.addWidget(self.adb_input)
            adb_layout.addWidget(self.btn_run_adb)
            adb_group.setLayout(adb_layout)
            layout.addWidget(adb_group)

            layout.addWidget(self.checkbox_fullscreen)
            layout.addWidget(self.btn_browse_scrcpy)
            layout.addWidget(self.btn_launch_all)
            layout.addWidget(self.btn_start)
            layout.addWidget(self.btn_manage_devices)
            layout.addWidget(self.log_output)
            self.setLayout(layout)

            self.record_path = "microscope_record.mp4"
            self.scrcpy_path = ""
            self.device_ip = ""
            self.devices = []
            self.device_id = None
            self.scrcpy_process = None
            self.devices_data = self.load_devices()
            self.load_config()
            self.update_device_list_safely()

            self.log("🥷⚔️💥 CyberNinja Phone is ready to go! NINJA MODE ENGAGED")
            self.log("CyberNinja HUD Initialized... Ready to launch scrcpy")

            self.device_timer = QTimer()
            self.device_timer.timeout.connect(self.update_device_list_safely)
            self.device_timer.start(5000)
        except Exception as e:
            self.log(f"🛑💣 App initialization failed: {str(e)}")

    def load_devices(self):
        try:
            if os.path.exists(DEVICES_FILE):
                with open(DEVICES_FILE, "r") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return {item: {"status": "Unknown", "name": item.split(":")[0]} for item in data}
                    return data
        except Exception as e:
            self.log(f"🚨📂 Error loading devices file: {str(e)}")
        return {}

    def save_devices(self):
        try:
            with open(DEVICES_FILE, "w") as f:
                json.dump(self.devices_data, f)
        except Exception as e:
            self.log(f"🚨📂 Error saving devices: {str(e)}")

    def toggle_ip_input(self):
        self.ip_input.setEnabled(self.checkbox_wireless.isChecked())
        self.btn_scan_ip.setEnabled(self.checkbox_wireless.isChecked())
        self.btn_quick_reconnect.setEnabled(self.checkbox_wireless.isChecked())

    def choose_record_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Recording As", "microscope_record.mp4", "MP4 Files (*.mp4)")
        if path:
            self.record_path = path
            self.save_config()

    def choose_scrcpy_path(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select scrcpy.exe", "", "Executable (*.exe)")
        if path:
            self.scrcpy_path = path
            self.save_config()
            self.log(f"🧙‍♂️📍 scrcpy path set to: {path}")

    def save_config(self):
        config = {
            "scrcpy_path": self.scrcpy_path,
            "record_path": self.record_path,
            "bitrate": self.bit_rate_input.text(),
            "max_size": self.max_size_input.text(),
            "fullscreen": self.checkbox_fullscreen.isChecked(),
            "wireless": self.checkbox_wireless.isChecked(),
            "record": self.checkbox_record.isChecked(),
            "ip": self.ip_input.text(),
            "custom_options": self.custom_options_input.text()
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    self.scrcpy_path = data.get("scrcpy_path", "")
                    self.record_path = data.get("record_path", "microscope_record.mp4")
                    self.bit_rate_input.setText(data.get("bitrate", "8M"))
                    self.max_size_input.setText(data.get("max_size", "1440"))
                    self.checkbox_fullscreen.setChecked(data.get("fullscreen", False))
                    self.checkbox_wireless.setChecked(data.get("wireless", False))
                    self.checkbox_record.setChecked(data.get("record", False))
                    self.ip_input.setText(data.get("ip", ""))
                    self.custom_options_input.setText(data.get("custom_options", ""))
                    self.toggle_ip_input()
            except Exception as e:
                self.log(f"🚨💣📂 Error loading config: {str(e)}")

    def log(self, text):
        try:
            self.log_output.append(f"{text}\n")
        except Exception as e:
            print(f"Log error: {e}")

    def scan_network(self):
        def scan():
            if not self.checkbox_wireless.isChecked():
                self.log("📶⚙️ Enable Wireless Mode to scan for devices.")
                return
            ip_base = ".".join(self.ip_input.text().split(".")[:3]) if self.ip_input.text() else "192.168.1"
            self.log(f"🔍🌐📱 Scanning network: {ip_base}.0/24 ...")
            found_ips = []
            for i in range(1, 255):
                ip = f"{ip_base}.{i}"
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.1)
                    result = sock.connect_ex((ip, 5555))
                    sock.close()
                    if result == 0:
                        try:
                            adb_result = subprocess.check_output(["adb", "connect", f"{ip}:5555"], stderr=subprocess.STDOUT, timeout=2)
                            msg = adb_result.decode()
                            if "connected" in msg.lower() or "already connected" in msg.lower():
                                found_ips.append(ip)
                                self.devices_data[f"{ip}:5555"] = {"status": "Online", "name": f"Device_{i}"}
                                self.save_devices()
                                QMetaObject.invokeMethod(self.device_combo, "addItem", Qt.QueuedConnection, Q_ARG(str, f"{ip}:5555 (wireless)"))
                                self.log(f"✅📱 Found device: {ip}:5555")
                        except Exception as adb_e:
                            pass
                except:
                    pass
            if found_ips:
                self.update_ip_input(found_ips[0])
                self.log(f"🟢📱🌐 Scan done: {', '.join(found_ips)}")
            else:
                self.log("⚠️📱🌐 No ADB devices found on network")
        threading.Thread(target=scan, daemon=True).start()

    @pyqtSlot(str)
    def update_ip_input(self, ip):
        self.ip_input.setText(ip)

    def detect_connection_mode(self):
        try:
            subprocess.run(["adb", "start-server"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            result = subprocess.run(["adb", "devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.log(f"ADB devices output: {result.stdout}")
            output = result.stdout.splitlines()
            devices = []
            for line in output:
                if "\tdevice" in line:
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        device_id = parts[0]
                        mode = "wireless" if ":" in device_id else "usb"
                        devices.append((device_id, mode))
            return devices
        except Exception as e:
            self.log(f"🚨📱🔌Error checking ADB devices: {str(e)}")
            return []

    def quick_reconnect(self):
        ip = self.ip_input.text().strip()
        if not ip:
            self.log("⚠️🛑🌐 No IP entered! Using default: 192.168.3.27 🛑\n👉 Please enter your own device IP to connect.")
            return
        if not self.checkbox_wireless.isChecked():
            self.log("📡📶 Enable Wireless Mode to reconnect via WiFi.")
            return
        usb_device = next((d for d, m in self.detect_connection_mode() if m == "usb"), None)
        if usb_device:
            try:
                self.log(f"Setting {usb_device} to TCP/IP mode ...")
                subprocess.run(["adb", "-s", usb_device, "tcpip", "5555"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
                time.sleep(1)
            except Exception as e:
                self.log(f"⚠️🚨 Could not set TCP/IP mode: {str(e)}")
        try:
            connect_result = subprocess.check_output(["adb", "connect", f"{ip}:5555"], stderr=subprocess.STDOUT, timeout=4)
            msg = connect_result.decode().strip()
            self.log(msg)
            if "connected" in msg.lower() or "already connected" in msg.lower():
                self.status_label.setText("🟢 Connected")
                self.device_combo.addItem(f"{ip}:5555 (wireless)")
                self.device_id = f"{ip}:5555"
            else:
                self.status_label.setText("🔴📱🔌 Disconnected")
        except Exception as e:
            self.status_label.setText("🔴📱🔌 Disconnected")
            self.log(f"🚨🌐📡 Error during reconnect: {str(e)}")

    def update_device_list_safely(self):
        try:
            self.devices = self.detect_connection_mode()
            self.device_combo.blockSignals(True)
            current_text = self.device_combo.currentText()
            self.device_combo.clear()
            self.device_combo.addItem("Select Device")
            seen_ids = set()
            if isinstance(self.devices_data, dict):
                for ip, data in self.devices_data.items():
                    if ip not in seen_ids:
                        display = f"{data.get('name', ip.split(':')[0])} ({ip})" if data.get("name") else f"{ip}"
                        self.device_combo.addItem(display)
                        seen_ids.add(ip)
            for device_id, mode in self.devices:
                if device_id not in seen_ids:
                    item_text = f"{device_id} ({mode})"
                    self.device_combo.addItem(item_text)
                    seen_ids.add(device_id)
            if current_text and self.device_combo.findText(current_text) != -1:
                self.device_combo.setCurrentText(current_text)
            elif self.device_id and self.device_combo.findText(self.device_id) != -1:
                self.device_combo.setCurrentText(self.device_id)
            else:
                self.device_combo.setCurrentIndex(0)
                self.device_id = None
            self.device_combo.blockSignals(False)
        except Exception as e:
            self.log(f"🚨📲🧩 Error updating device list: {str(e)}")

    def update_device_selection(self):
        try:
            if self.device_combo.currentIndex() == 0 or not self.devices:
                self.device_id = None
                self.ip_input.clear()
                self.toggle_ip_input()
                self.status_label.setText("📱🔌❌ Disconnected")
                return
            selected_text = self.device_combo.currentText()
            for ip, data in self.devices_data.items():
                name = data.get("name", ip.split(":")[0])
                display = f"{name} ({ip})" if name else f"{ip}"
                if display == selected_text:
                    self.device_id = ip
                    self.ip_input.setText(ip.split(":")[0])
                    try:
                        result = subprocess.check_output(["adb", "connect", ip], stderr=subprocess.STDOUT, timeout=2, universal_newlines=True)
                        if "cannot connect" in result.lower() or "offline" in result.lower():
                            self.status_label.setText("🔴📱🔌 Offline")
                            self.log(f"🔴📱🔌 Offline device: {ip}")
                            data["status"] = "Offline"
                        else:
                            self.status_label.setText("🟢📱🔌 Connected")
                            data["status"] = "Online"
                    except Exception as e:
                        self.status_label.setText("🔴📱🔌 Offline")
                        self.log(f"🔴📱🔌 Offline device: {ip} - {str(e)}")
                        data["status"] = "Offline"
                    break
                elif f"{ip} (usb)" == selected_text or f"{ip} (wireless)" == selected_text:
                    self.device_id = ip
                    self.ip_input.setText(ip.split(":")[0])
                    try:
                        result = subprocess.check_output(["adb", "connect", ip], stderr=subprocess.STDOUT, timeout=2, universal_newlines=True)
                        if "cannot connect" in result.lower() or "offline" in result.lower():
                            self.status_label.setText("🔴📱🔌 Offline")
                            self.log(f"🔴📱🔌 Offline device: {ip}")
                            data["status"] = "Offline"
                        else:
                            self.status_label.setText("🟢📱🔌 Connected")
                            data["status"] = "Online"
                    except Exception as e:
                        self.status_label.setText("🔴📱🔌 Offline")
                        self.log(f"🔴📱🔌 Offline device: {ip} - {str(e)}")
                        data["status"] = "Offline"
                    break
            self.toggle_ip_input()
            self.save_devices()
        except Exception as e:
            self.log(f"⚠️🚨 Error updating device selection: {str(e)}")

    def wifi_connect(self):
        ip = self.ip_input.text().strip()
        if not ip:
            self.log("🚨🌐📶 No IP entered! Using default: 192.168.3.27\n📝 👉 Set your device IP in the input box above for best results.")
            return
        if ":5555" not in ip:
            ip_full = f"{ip}:5555"
        else:
            ip_full = ip
        try:
            self.log(f"🔌 Running: adb connect {ip_full}")
            result = subprocess.check_output(["adb", "connect", ip_full], stderr=subprocess.STDOUT, universal_newlines=True, timeout=5)
            self.log(result)
            if "connected" in result.lower() or "already connected" in result.lower():
                self.device_combo.addItem(f"{ip_full} (wireless)")
                self.status_label.setText("🟢📶 Connected (Wireless)")
                self.devices_data[ip_full] = {"status": "Online", "name": ip}
                self.save_devices()
            else:
                self.log(f"⚠️📱🔌 Offline device: {ip_full}")
                self.status_label.setText("🔴📱🔌 Disconnected")
        except subprocess.CalledProcessError as e:
            self.log(f"🔴📱🔌 Offline device: {ip_full} - {e.output}")
            self.status_label.setText("🔴📱🔌 Disconnected")
        except Exception as e:
            self.log(f"🚨 Unexpected error during WiFi connect: {str(e)}")
            self.status_label.setText("🔴📱🔌 Disconnected")

    def launch_all_devices(self):
        if not self.scrcpy_path or not os.path.exists(self.scrcpy_path):
            self.log("🚨🥷🔒 scrcpy.exe not found. Use 'Locate scrcpy.exe' first.")
            return

        if not os.path.exists(DEVICES_FILE):
            self.log(f"🚨📱🔒 {DEVICES_FILE} not found in the current directory.")
            return

        try:
            with open(DEVICES_FILE, "r") as f:
                device_data = json.load(f)
                if not device_data:
                    self.log("🚨📱🔒 No devices listed in devices.json.")
                    return
        except Exception as e:
            self.log(f"🚨📱🔒 Error loading devices.json: {str(e)}")
            return

        self.log(f"🧙✨🚀 Launching scrcpy for {len(device_data)} devices...")
        for device_id, data in device_data.items():
            try:
                result = subprocess.check_output(["adb", "connect", device_id], stderr=subprocess.STDOUT, timeout=5, universal_newlines=True)
                if "cannot connect" in result.lower() or "offline" in result.lower():
                    self.log(f"⚠️📱🔌 Offline device: {device_id}")
                    continue
            except Exception as e:
                self.log(f"⚠️📱🔌 Offline device: {device_id} - {str(e)}")
                continue

            args = [self.scrcpy_path, "-s", device_id]
            if self.checkbox_fullscreen.isChecked():
                args.append("--fullscreen")
            if self.checkbox_record.isChecked():
                record_path = f"{device_id.replace(':', '_')}_{self.record_path}"
                args += ["--record", record_path]
            if self.bit_rate_input.text():
                args += ["--video-bit-rate", self.bit_rate_input.text()]
            if self.max_size_input.text():
                args += ["--max-size", self.max_size_input.text()]
            if self.custom_options_input.text():
                custom_args = self.custom_options_input.text().strip().split()
                valid_args = [arg for arg in custom_args if arg.startswith("--") or arg.isalnum() or "=" in arg]
                if len(valid_args) != len(custom_args):
                    self.log(f"⚠️🚨 Invalid custom scrcpy options ignored for {device_id}")
                args.extend(valid_args)

            if ":" in device_id and self.checkbox_wireless.isChecked():
                try:
                    self.log(f"Ensuring {device_id} is in TCP/IP mode...")
                    subprocess.run(["adb", "tcpip", "5555"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
                    time.sleep(1)
                    connect_result = subprocess.check_output(["adb", "connect", device_id], stderr=subprocess.STDOUT, timeout=5)
                    if "cannot connect" in connect_result.lower():
                        self.log(f"🚨 Failed to connect to {device_id}: {connect_result.decode().strip()}")
                        continue
                except Exception as e:
                    self.log(f"🚨 Error setting up {device_id} for wireless: {str(e)}")
                    continue

            try:
                subprocess.Popen(args)
                self.log(f"🚀🥷🔓 scrcpy launched for device {device_id}")
            except Exception as e:
                self.log(f"🚨☠️ Error launching scrcpy for {device_id}: {str(e)}")

    def setup_adb(self):
        if not self.device_combo.currentIndex() or self.device_combo.currentIndex() == 0:
            self.log("⚠️📱🔒 No device selected")
            return False, None

        try:
            device_id, mode = self.devices[self.device_combo.currentIndex() - 1]
            self.log(f"📲🔌⚡️ Selected device: {device_id} ({mode})")
        except IndexError:
            self.log("⚠️📱🔌 Invalid device selection")
            self.status_label.setText("🔴📱🔌 Disconnected")
            return False, None

        self.status_label.setText("⏳Connecting...")
        if self.status_gif:
            self.status_gif.start()

        if mode == "usb" and not self.checkbox_wireless.isChecked():
            self.log(f"Checking USB device: {device_id}")
            try:
                result = subprocess.run(["adb", "-s", device_id, "shell", "echo", "test"],
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
                if result.returncode == 0 and result.stdout.strip() == "test":
                    self.log("✅🔌🔓 USB ADB connected")
                    self.status_label.setText("🟢🔌🔋 Connected (USB)")
                    if self.status_gif:
                        self.status_gif.stop()
                    return True, device_id
                else:
                    self.log(f"🚨🔌 USB device not responding: {result.stderr}")
            except Exception as e:
                self.log(f"🚨🔌 USB connection error: {str(e)}")
            self.status_label.setText("🔴 Disconnected")
            if self.status_gif:
                self.status_gif.stop()
            return False, None

        if self.checkbox_wireless.isChecked():
            ip = self.ip_input.text().strip()
            if not ip or not all(part.isdigit() and 0 <= int(part) <= 255 for part in ip.split(".")):
                self.log("⚠️🚨🌐 Invalid or missing IP address")
                self.status_label.setText("🔴 Disconnected")
                if self.status_gif:
                    self.status_gif.stop()
                return False, None

            self.log(f"Attempting initial wireless connection to {ip}:5555")
            try:
                if mode == "usb":
                    connect = subprocess.run(
                        ["adb", "connect", f"{ip}:5555"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=5
                    )
                    self.log(f"Initial connect output: {connect.stdout}")
                    if not ("connected" in connect.stdout.lower() or "already connected" in connect.stdout.lower()):
                        self.log(f"🚨🥷🔒 Initial connect failed: {connect.stderr}")
                        self.status_label.setText("🔴📱🔌 Disconnected")
                        if self.status_gif:
                            self.status_gif.stop()
                        return False, None

                result = subprocess.run(
                    ["adb", "-s", device_id, "tcpip", "5555"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=5
                )
                if result.returncode != 0:
                    self.log(f"🚨🌐📡 Failed to enable TCP/IP: {result.stderr}")
                    self.status_label.setText("🔴📱🔌 Disconnected")
                    if self.status_gif:
                        self.status_gif.stop()
                    return False, None
                time.sleep(2)
                device_id = f"{ip}:5555"

                for attempt in range(3):
                    connect = subprocess.run(
                        ["adb", "connect", f"{ip}:5555"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=5
                    )
                    self.log(f"Connection attempt {attempt + 1} output: {connect.stdout}")
                    if "connected" in connect.stdout.lower() or "already connected" in connect.stdout.lower():
                        self.log("✅📶 Wireless ADB connected")
                        self.status_label.setText("🟢📶 Connected (Wireless)")
                        if self.status_gif:
                            self.status_gif.stop()
                        return True, f"{ip}:5555"
                    self.log(f"🚨📶🚫 Wireless connection failed: {connect.stderr}")
                    time.sleep(1)
                self.log("🚨🧠💀 All connection attempts failed")
            except Exception as e:
                self.log(f"🚨📶 Wireless ADB exception: {str(e)}")
                self.status_label.setText("🔴 Disconnected")
                if self.status_gif:
                    self.status_gif.stop()
                return False, None

        self.log("🚨📱🔒 No ADB device detected")
        self.status_label.setText("🔴 Disconnected")
        if self.status_gif:
            self.status_gif.stop()
        return False, None

    def launch_scrcpy(self):
        if not self.scrcpy_path or not os.path.exists(self.scrcpy_path):
            self.log("🚨⚠️🔒 scrcpy.exe not found. Use 'Locate scrcpy.exe' first.")
            return

        success, device_id = self.setup_adb()
        if not success or not device_id:
            self.log("🚨📱🔒 Device setup failed or no device ID")
            return

        args = [self.scrcpy_path, "-s", device_id]
        if self.checkbox_fullscreen.isChecked():
            args.append("--fullscreen")
        if self.checkbox_record.isChecked():
            args += ["--record", self.record_path]
        if self.bit_rate_input.text():
            args += ["--video-bit-rate", self.bit_rate_input.text()]
        if self.max_size_input.text():
            args += ["--max-size", self.max_size_input.text()]
        if self.custom_options_input.text():
            custom_args = self.custom_options_input.text().strip().split()
            valid_args = [arg for arg in custom_args if arg.startswith("--") or arg.isalnum() or "=" in arg]
            if len(valid_args) != len(custom_args):
                self.log("⚠️ Invalid custom scrcpy options ignored")
            args.extend(valid_args)

        try:
            self.scrcpy_process = subprocess.Popen(args)
            self.log("✅🥷🔓 scrcpy launched successfully!")
        except Exception as e:
            self.log(f"🚨☠️ Error launching scrcpy: {str(e)}")

    def start_recording(self):
        if not self.device_id:
            self.log("🚨📲🔒 No device selected")
            return
        if self.scrcpy_process and self.scrcpy_process.poll() is None:
            self.log("⚡️🟢🎬 scrcpy already running; stop current session to start recording")
            return

        args = [self.scrcpy_path, "-s", self.device_id, "--record", self.record_path]
        try:
            self.scrcpy_process = subprocess.Popen(args)
            self.btn_start_record.setEnabled(False)
            self.btn_stop_record.setEnabled(True)
            self.log("✅🎥🎬 Recording started")
        except Exception as e:
            self.log(f"🚨🎥🎬 Error starting recording: {str(e)}")

    def stop_recording(self):
        if self.scrcpy_process and self.scrcpy_process.poll() is None:
            self.scrcpy_process.terminate()
            self.scrcpy_process = None
            self.btn_start_record.setEnabled(True)
            self.btn_stop_record.setEnabled(False)
            self.log("⏹️🛑 Recording stopped")
        else:
            self.log("⚠️⏸️ No recording active")

    def run_adb_command(self):
        command = self.adb_input.text().strip()
        if not command:
            self.log("⚠️🚨 No ADB command provided")
            return

        dangerous_commands = ["reboot", "fastboot", "recovery", "bootloader"]
        if any(cmd in command.lower() for cmd in dangerous_commands):
            self.log("🛑💀🚨 Blocked dangerous command: reboot-related commands are disabled")
            return

        try:
            args = ["adb"] + (["-s", self.device_id] if self.device_id else []) + command.split()
            result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            if result.stdout:
                self.log(f"✅🤖 ADB output: {result.stdout}")
            if result.stderr:
                self.log(f"⚠️🚨 ADB error: {result.stderr}")
        except Exception as e:
            self.log(f"🚨⚠️ Error executing ADB command: {str(e)}")

    def manage_devices(self):
        dialog = DeviceManagerDialog(self, self.devices_data, self.update_device_list_safely)
        dialog.exec_()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CyberScrcpy()
    window.show()
    sys.exit(app.exec_()) 