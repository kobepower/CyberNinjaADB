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
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal, pyqtSlot

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
                                new_devices[f"{ip}:5555"] = {"status": "Online", "name": f"Device_{i}", "last_status": "Online"}
                                self.parent().log(f"✅📱 Found device: {ip}:5555")
                        except Exception:
                            pass
                except Exception:
                    pass
            self.devices.update(new_devices)
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
    # Custom signal for thread-safe GUI updates
    DeviceListUpdated = pyqtSignal(list, dict, str, str)

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
            self.btn_start.clicked.connect(self.launch_selected_device)

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
            self.reconnect_attempts = {}
            self.last_reconnect_time = {}
            self.last_status = {}
            self.DeviceListUpdated.connect(self.update_combo_box)

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

    def ensure_adb_server(self):
        try:
            result = subprocess.run(["adb", "version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
            if result.returncode != 0:
                self.log("🚨 ADB server not running, starting server...")
                subprocess.run(["adb", "start-server"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
                self.log("✅ ADB server started")
        except Exception as e:
            self.log(f"🚨 Error checking/starting ADB server: {str(e)}")

    def attempt_reconnect(self, ip, data):
        def reconnect():
            if ip not in self.last_reconnect_time or (time.time() - self.last_reconnect_time.get(ip, 0)) >= 10:
                if ip not in self.reconnect_attempts:
                    self.reconnect_attempts[ip] = 0
                if self.reconnect_attempts[ip] >= 3:
                    if self.last_status.get(ip) != "MaxAttempts":
                        self.log(f"⚠️ Max reconnect attempts reached for {ip}")
                        self.last_status[ip] = "MaxAttempts"
                    return
                self.reconnect_attempts[ip] += 1
                self.last_reconnect_time[ip] = time.time()
                self.log(f"🔄 Attempting reconnect to {ip} (Attempt {self.reconnect_attempts[ip]}/3)")
                try:
                    connect_result = subprocess.check_output(["adb", "connect", ip], stderr=subprocess.STDOUT, text=True, timeout=4)
                    if "connected" in connect_result.lower() or "already connected" in connect_result.lower():
                        data["status"] = "Online"
                        self.reconnect_attempts[ip] = 0
                        self.last_status[ip] = "Online"
                        self.log(f"✅ Reconnected to {ip}")
                        self.DeviceListUpdated.emit(self.devices, self.devices_data, self.device_id or "", ip)
                    else:
                        if self.last_status.get(ip) != "Offline":
                            self.log(f"⚠️ Failed to reconnect to {ip}: {connect_result.strip()}")
                            self.last_status[ip] = "Offline"
                except Exception as e:
                    if self.last_status.get(ip) != "Offline":
                        self.log(f"🚨 Error reconnecting to {ip}: {str(e)}")
                        self.last_status[ip] = "Offline"
        threading.Thread(target=reconnect, daemon=True).start()

    @pyqtSlot(list, dict, str, str)
    def update_combo_box(self, devices, devices_data, current_device_id, updated_ip):
        self.device_combo.blockSignals(True)
        current_text = self.device_combo.currentText()
        self.device_combo.clear()
        self.device_combo.addItem("Select Device")
        seen_ids = set()
        if isinstance(devices_data, dict):
            for ip, data in devices_data.items():
                if ip not in seen_ids:
                    display = f"{data.get('name', ip.split(':')[0])} ({ip})" if data.get('name') else f"{ip}"
                    self.device_combo.addItem(display)
                    seen_ids.add(ip)
        for device_id, mode in devices:
            if device_id not in seen_ids:
                item_text = f"{device_id} ({mode})"
                self.device_combo.addItem(item_text)
                seen_ids.add(device_id)
                if device_id not in devices_data:
                    devices_data[device_id] = {"status": "Online", "name": device_id.split(":")[0], "last_status": "Online"}
        if current_text and self.device_combo.findText(current_text) != -1:
            self.device_combo.setCurrentText(current_text)
        elif current_device_id and self.device_combo.findText(current_device_id) != -1:
            self.device_combo.setCurrentText(current_device_id)
        else:
            self.device_combo.setCurrentIndex(0)
            self.device_id = None
            self.status_label.setText("🚨💀🥷Disconnected")
        self.device_combo.blockSignals(False)
        self.update_device_selection()

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
                                self.devices_data[f"{ip}:5555"] = {"status": "Online", "name": f"Device_{i}", "last_status": "Online"}
                                self.save_devices()
                                self.DeviceListUpdated.emit(self.devices, self.devices_data, self.device_id or "", f"{ip}:5555")
                                self.log(f"✅📱 Found device: {ip}:5555")
                        except Exception as adb_e:
                            pass
                except:
                    pass
            if found_ips:
                self.ip_input.setText(found_ips[0])
                self.log(f"🟢📱🌐 Scan done: {', '.join(found_ips)}")
            else:
                self.log("⚠️📱🌐 No ADB devices found on network")
        threading.Thread(target=scan, daemon=True).start()

    def detect_connection_mode(self):
        try:
            self.ensure_adb_server()
            result = subprocess.run(["adb", "devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output = result.stdout.splitlines()
            devices = []
            for line in output:
                if "\tdevice" in line or "\toffline" in line:
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
        if not self.checkbox_wireless.isChecked():
            self.log("📡📶 Enable Wireless Mode to reconnect via WiFi.")
            return
        def reconnect_all():
            self.log("🔄🦉 Starting quick reconnect for all wireless devices...")
            self.ensure_adb_server()
            devices = self.detect_connection_mode()
            for device_id, mode in devices:
                if mode == "usb":
                    if self.last_status.get(device_id) != "Skipped":
                        self.log(f"🚫 Skipping USB-only device: {device_id}")
                        self.last_status[device_id] = "Skipped"
                    continue
                data = self.devices_data.get(device_id, {"status": "Offline", "name": device_id.split(":")[0]})
                if data["status"] == "Offline":
                    if device_id not in self.reconnect_attempts:
                        self.reconnect_attempts[device_id] = 0
                    if self.reconnect_attempts[device_id] >= 3:
                        if self.last_status.get(device_id) != "MaxAttempts":
                            self.log(f"⚠️ Max reconnect attempts reached for {device_id}")
                            self.last_status[device_id] = "MaxAttempts"
                        continue
                    if device_id not in self.last_reconnect_time or (time.time() - self.last_reconnect_time.get(device_id, 0)) >= 10:
                        self.reconnect_attempts[device_id] += 1
                        self.last_reconnect_time[device_id] = time.time()
                        self.log(f"🔄 Attempting reconnect to {device_id} (Attempt {self.reconnect_attempts[device_id]}/3)")
                        try:
                            connect_result = subprocess.check_output(["adb", "connect", device_id], stderr=subprocess.STDOUT, text=True, timeout=4)
                            if "connected" in connect_result.lower() or "already connected" in connect_result.lower():
                                data["status"] = "Online"
                                self.reconnect_attempts[device_id] = 0
                                self.last_status[device_id] = "Online"
                                self.log(f"✅ Reconnected to {device_id}")
                                self.DeviceListUpdated.emit(self.devices, self.devices_data, self.device_id or "", device_id)
                            else:
                                if self.last_status.get(device_id) != "Offline":
                                    self.log(f"⚠️ Failed to reconnect to {device_id}: {connect_result.strip()}")
                                    self.last_status[device_id] = "Offline"
                        except Exception as e:
                            if self.last_status.get(device_id) != "Offline":
                                self.log(f"🚨 Error reconnecting to {device_id}: {str(e)}")
                                self.last_status[device_id] = "Offline"
            self.log("🟢 Quick reconnect completed")
        threading.Thread(target=reconnect_all, daemon=True).start()

    def update_device_list_safely(self):
        try:
            self.devices = self.detect_connection_mode()
            for ip, data in self.devices_data.items():
                if ":" not in ip:
                    if self.last_status.get(ip) != "Skipped":
                        self.log(f"🚫 Skipping USB-only device: {ip}")
                        self.last_status[ip] = "Skipped"
                    continue
                try:
                    result = subprocess.run(["adb", "-s", ip, "shell", "echo", "test"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
                    new_status = "Online" if result.returncode == 0 and result.stdout.strip() == "test" else "Offline"
                    if new_status != data.get("status"):
                        data["status"] = new_status
                        self.last_status[ip] = new_status
                        self.log(f"{'🟢' if new_status == 'Online' else '🔴'} Device {ip}: {new_status}")
                    if new_status == "Offline":
                        self.attempt_reconnect(ip, data)
                except Exception:
                    if data.get("status") != "Offline":
                        data["status"] = "Offline"
                        self.last_status[ip] = "Offline"
                        self.log(f"🔴 Device {ip}: Offline")
                        self.attempt_reconnect(ip, data)
            self.DeviceListUpdated.emit(self.devices, self.devices_data, self.device_id or "", "")
            self.save_devices()
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
                if display == selected_text or f"{ip} (usb)" == selected_text or f"{ip} (wireless)" == selected_text:
                    self.device_id = ip
                    self.ip_input.setText(ip.split(":")[0] if ":" in ip else ip)
                    try:
                        result = subprocess.run(["adb", "-s", ip, "shell", "echo", "test"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
                        new_status = "Online" if result.returncode == 0 and result.stdout.strip() == "test" else "Offline"
                        if new_status != data.get("status"):
                            data["status"] = new_status
                            self.last_status[ip] = new_status
                            self.log(f"{'🟢' if new_status == 'Online' else '🔴'} Device {ip}: {new_status}")
                        status_text = f"🟢📱🔌 Connected ({'Wireless' if ':' in ip else 'USB'})" if new_status == "Online" else "🔴📱🔌 Offline"
                        self.status_label.setText(status_text)
                    except Exception as e:
                        if data.get("status") != "Offline":
                            data["status"] = "Offline"
                            self.last_status[ip] = "Offline"
                            self.log(f"🔴 Device {ip}: Offline - {str(e)}")
                        self.status_label.setText("🔴📱🔌 Offline")
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
                self.devices_data[ip_full] = {"status": "Online", "name": ip, "last_status": "Online"}
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

        def launch_device(device_id, data):
            if not (":" in device_id or device_id.replace(".", "").isdigit()):
                self.log(f"⚠️📱🔌 Invalid device ID format: {device_id}")
                data["status"] = "Offline"
                return

            try:
                result = subprocess.run(["adb", "-s", device_id, "shell", "echo", "test"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
                if result.returncode != 0 or result.stdout.strip() != "test":
                    if self.last_status.get(device_id) != "Offline":
                        self.log(f"⚠️📱🔌 Offline device: {device_id}")
                        self.last_status[device_id] = "Offline"
                    data["status"] = "Offline"
                    return
            except Exception as e:
                if self.last_status.get(device_id) != "Offline":
                    self.log(f"⚠️📱🔌 Offline device: {device_id} - {str(e)}")
                    self.last_status[device_id] = "Offline"
                data["status"] = "Offline"
                return

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
                    connect_result = subprocess.check_output(["adb", "connect", device_id], stderr=subprocess.STDOUT, timeout=5, text=True)
                    if "cannot connect" in connect_result.lower():
                        self.log(f"🚨 Failed to connect to {device_id}: {connect_result.strip()}")
                        data["status"] = "Offline"
                        return
                except Exception as e:
                    self.log(f"🚨 Error setting up {device_id} for wireless: {str(e)}")
                    data["status"] = "Offline"
                    return

            try:
                subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.log(f"🚀🥷🔓 scrcpy launched for device {device_id}")
                data["status"] = "Online"
                self.last_status[device_id] = "Online"
            except Exception as e:
                self.log(f"🚨☠️ Error launching scrcpy for {device_id}: {str(e)}")
                data["status"] = "Offline"
                self.last_status[device_id] = "Offline"

        self.log(f"🧙✨🚀 Launching scrcpy for {len(device_data)} devices...")
        for device_id, data in device_data.items():
            threading.Thread(target=launch_device, args=(device_id, data), daemon=True).start()
        QTimer.singleShot(1000, self.update_device_list_safely)

    def setup_adb(self):
        if not self.device_combo.currentIndex() or self.device_combo.currentIndex() == 0 or not self.devices:
            self.log("⚠️📱🔌 Invalid device selection")
            self.status_label.setText("🔴📱🔌 Disconnected")
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

        try:
            result = subprocess.run(["adb", "-s", device_id, "shell", "echo", "test"],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
            if result.returncode == 0 and result.stdout.strip() == "test":
                self.log(f"✅🔌🔓 {'USB' if mode == 'usb' else 'Wireless'} ADB connected")
                self.status_label.setText(f"🟢🔌🔋 Connected ({'USB' if mode == 'usb' else 'Wireless'})")
                if self.status_gif:
                    self.status_gif.stop()
                if device_id in self.devices_data:
                    self.devices_data[device_id]["status"] = "Online"
                    self.last_status[device_id] = "Online"
                return True, device_id
            else:
                if self.last_status.get(device_id) != "Offline":
                    self.log(f"🚨🔌 Device not responding: {result.stderr}")
                    self.last_status[device_id] = "Offline"
                self.status_label.setText("🔴📱🔌 Offline")
                if device_id in self.devices_data:
                    self.devices_data[device_id]["status"] = "Offline"
        except Exception as e:
            if self.last_status.get(device_id) != "Offline":
                self.log(f"🚨🔌 Connection error: {str(e)}")
                self.last_status[device_id] = "Offline"
            self.status_label.setText("🔴📱🔌 Offline")
            if device_id in self.devices_data:
                self.devices_data[device_id]["status"] = "Offline"
        if self.status_gif:
            self.status_gif.stop()
        return False, None

    def launch_selected_device(self):
        if not self.scrcpy_path or not os.path.exists(self.scrcpy_path):
            self.log("🚨⚠️🔒 scrcpy.exe not found. Use 'Locate scrcpy.exe' first.")
            self.status_label.setText("🔴📱🔌 Disconnected")
            return

        device = self.device_combo.currentText().split()[0]
        if not device or device == "Select":
            self.log("⚠️📱🔌 No device selected")
            self.status_label.setText("🔴📱🔌 Disconnected")
            return

        try:
            result = subprocess.run(["adb", "-s", device, "shell", "echo", "test"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
            if result.returncode != 0 or result.stdout.strip() != "test":
                if self.last_status.get(device) != "Offline":
                    self.log(f"🔴📱🔌 Offline device: {device}")
                    self.last_status[device] = "Offline"
                self.status_label.setText("🔴📱🔌 Offline")
                if device in self.devices_data:
                    self.devices_data[device]["status"] = "Offline"
                return
        except Exception as e:
            if self.last_status.get(device) != "Offline":
                self.log(f"🚨📱🔌 Error checking device status: {str(e)}")
                self.last_status[device] = "Offline"
            self.status_label.setText("🔴📱🔌 Offline")
            if device in self.devices_data:
                self.devices_data[device]["status"] = "Offline"
            return

        self.status_label.setText("✅ Launching scrcpy...")
        def _launch():
            try:
                args = [self.scrcpy_path, "-s", device]
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

                self.scrcpy_process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if device in self.devices_data:
                    self.devices_data[device]["status"] = "Online"
                    self.last_status[device] = "Online"
                self.status_label.setText(f"🟢 Connected to: {device}")
                self.log(f"✅🥷🔓 scrcpy launched successfully for {device}")

                while self.scrcpy_process.poll() is None:
                    try:
                        result = subprocess.run(["adb", "-s", device, "shell", "echo", "test"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
                        if result.returncode != 0 or result.stdout.strip() != "test":
                            self.scrcpy_process.terminate()
                            self.status_label.setText("🔴📱🔌 Offline")
                            if self.last_status.get(device) != "Offline":
                                self.log(f"🔴📱🔌 Device {device} disconnected during scrcpy")
                                self.last_status[device] = "Offline"
                            if device in self.devices_data:
                                self.devices_data[device]["status"] = "Offline"
                            break
                    except Exception:
                        self.scrcpy_process.terminate()
                        self.status_label.setText("🔴📱🔌 Offline")
                        if self.last_status.get(device) != "Offline":
                            self.log(f"🔴📱🔌 Device {device} disconnected during scrcpy")
                            self.last_status[device] = "Offline"
                        if device in self.devices_data:
                            self.devices_data[device]["status"] = "Offline"
                        break
                    time.sleep(1)
                if self.scrcpy_process.poll() is not None:
                    self.status_label.setText("🔴📱🔌 Disconnected")
                    self.log(f"🔴📱🔌 scrcpy process for {device} ended")
                    if device in self.devices_data:
                        self.devices_data[device]["status"] = "Offline"
                        self.last_status[device] = "Offline"
                    self.scrcpy_process = None
            except Exception as e:
                self.status_label.setText(f"🔴📱🔌 Disconnected")
                self.log(f"🚨☠️ Error launching scrcpy for {device}: {str(e)}")
                if device in self.devices_data:
                    self.devices_data[device]["status"] = "Offline"
                    self.last_status[device] = "Offline"
                self.scrcpy_process = None

        threading.Thread(target=_launch, daemon=True).start()

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
            if self.device_id in self.devices_data:
                self.devices_data[self.device_id]["status"] = "Online"
                self.last_status[self.device_id] = "Online"
        except Exception as e:
            self.log(f"🚨🎥🎬 Error starting recording: {str(e)}")
            if self.device_id in self.devices_data:
                self.devices_data[self.device_id]["status"] = "Offline"
                self.last_status[self.device_id] = "Offline"

    def stop_recording(self):
        if self.scrcpy_process and self.scrcpy_process.poll() is None:
            self.scrcpy_process.terminate()
            self.scrcpy_process = None
            self.btn_start_record.setEnabled(True)
            self.btn_stop_record.setEnabled(False)
            self.log("⏹️🛑 Recording stopped")
            if self.device_id in self.devices_data:
                self.devices_data[self.device_id]["status"] = "Offline"
                self.last_status[self.device_id] = "Offline"
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

    def closeEvent(self, event):
        if self.scrcpy_process and self.scrcpy_process.poll() is None:
            self.scrcpy_process.terminate()
            self.scrcpy_process = None
        self.status_label.setText("🔴📱🔌 Disconnected")
        if self.device_id in self.devices_data:
            self.devices_data[self.device_id]["status"] = "Offline"
            self.last_status[self.device_id] = "Offline"
        self.save_devices()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CyberScrcpy()
    window.show()
    sys.exit(app.exec_())