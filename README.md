# 🥷 CyberNinjaADB

A fast, wireless Android control tool built with Python, scrcpy, and ADB.  
No cables needed — just click and connect over WiFi.  
Designed for ease of use and cyberpunk flair.

---

## 👨‍💻 Developer Statement

> “I built this using AI and open-source tools to help people with broken screens, lost phones, or just to save time. It’s 100% local and safe — no funny business.”  
> — **Kobe**, Creator of **CyberNinjaPhone**

This tool exists because I was tired of clunky Android screen tools and wanted something **cool, fast, and cyberpunk-themed** that *just works* — no setup headaches, no spyware, no BS.

🧠 Built with ChatGPT  
🛠️ Powered by ADB + scrcpy  
🔒 100% Local. No Data Leaves Your PC.

---

## 🚀 Features

- ✅ USB & Wireless ADB connection  
- 📱 Auto-connect to saved Android device IPs  
- 🖥️ Launch scrcpy for screen mirroring  
- 🔌 One-click WiFi pairing  
- 📂 Configurable `devices.json` file  
- 💻 Windows-compatible `.exe` build (via PyInstaller)  

---

## 🧰 Setup Instructions

### 1. Clone this repo

```bash
git clone https://github.com/kobepower/CyberNinjaPhone.git
cd CyberNinjaPhone



2. Create a virtual environment (recommended)
python -m venv venv
venv\Scripts\activate


 3. Install dependencies
pip install -r requirements.txt


4. 4. Run the app
python CyberNinjaPhone.py


🔐 devices.json Notes
This file is auto-generated at runtime when needed.

If it contains user IPs or data — do NOT push it to GitHub.

Add it to .gitignore like so:

gitignore
Copy
Edit

devices.json


📦 Requirements
Python 3.8+

scrcpy installed and accessible in your system PATH

Android device with ADB over WiFi enabled

🔧 Manual Setup (First Time Only)
📝 Edit devices.json
In the root folder, create or update devices.json like:

json
Copy
Edit
[
  {
    "name": "My Phone",
    "ip": "192.168.1.123"
  }
]
Find your phone’s IP:
Settings → WiFi → Your Network → IP Address


🛠️ Enable ADB on Android
Open Settings → About Phone

Tap Build Number 7 times

Go back to Settings → Developer Options

Enable USB Debugging and Wireless Debugging



🔗 Pair Over WiFi
Use a USB cable once to pair:


adb tcpip 5555
adb connect <your-phone-ip>

Once connected, the tool will remember the IP.

📁 Folder Structure

CyberNinjaADB/
├── CyberNinjaPhone.py         ← Main app
├── devices.json               ← Generated at runtime
├── Image/                     ← Icon resources
├── scrcpy/                    ← (optional) local scrcpy binaries
├── venv/                      ← Virtual environment (if used)
├── LICENSE
├── README.md
├── requirements.txt
├── scrcpy_config.json         ← (optional) custom scrcpy config
└── .gitignore

💬 Tips
Phone not showing up? Make sure it’s on the same WiFi.

Add multiple devices in devices.json if needed.

.exe build acts exactly like the Python script.

No data ever leaves your PC — everything runs offline.


🧠 Coming Soon
📱 Multiple device switching

🔗 Bluetooth ADB (experimental)

🔍 Auto-device discovery

🌐 Cross-platform (Linux & macOS)


Built with 💻 by Kobe
Because walking across the room to grab your phone is so last century. 🧠


## 🔏 License

This project is licensed under the **MIT License** — you are free to use, modify, and distribute it.

---

MIT License  

Copyright (c) 2025 Kobe  

Permission is hereby granted, free of charge, to any person obtaining a copy  
of this software and associated documentation files (the "Software"), to deal  
in the Software without restriction, including without limitation the rights  
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell  
copies of the Software, and to permit persons to whom the Software is  
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all  
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR  
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,  
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE  
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER  
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,  
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE  
SOFTWARE.



---

Let me know when you're ready to push and I’ll verify `.gitignore`, folder structure, and badge generation too if you want shields.io-style badges for PyPI, Python version, etc.






















