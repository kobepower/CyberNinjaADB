\# 🥷 CyberNinjaADB



A fast, wireless Android control tool built with Python, scrcpy, and ADB.  

No cables needed — just click and connect over WiFi. Designed for ease of use and cyberpunk flair.  



---



\## 🚀 Features



\- ✅ USB \& Wireless ADB connection

\- 📱 Auto-connect to saved Android device IPs

\- 🖥️ Launch scrcpy for screen mirroring

\- 🔌 One-click WiFi pairing

\- 📂 Configurable `devices.json` file

\- 💻 Windows-compatible `.exe` build ready (via PyInstaller)



---



\## 📦 Requirements



\- Python 3.8+

\- `scrcpy` installed and accessible in your system path

\- Android device with ADB over WiFi enabled



---



\## 🔧 Setup



1\. 📝 \*\*Edit `devices.json`\*\*

&nbsp;  

&nbsp;  In the root folder, find the file named `devices.json`.  

&nbsp;  Update it with your device's name and IP like this:



&nbsp;  ```json

&nbsp;  \[

&nbsp;    {

&nbsp;      "name": "My Phone",

&nbsp;      "ip": "192.168.1.123"

&nbsp;    }

&nbsp;  ]

If you’re not sure how to find your phone’s IP:



Go to Settings → WiFi → Your Network



Look under IP address



🛠️ Enable ADB on Your Android Device



Open Settings > About Phone



Tap Build Number 7 times to unlock Developer Options



Go back to Settings > Developer Options



Turn on USB Debugging and Wireless Debugging (on Android 11+)



🔗 Pair with ADB



Plug in USB once (for pairing)



Use:



bash

Copy

Edit

adb tcpip 5555

adb connect <your-phone-ip>

▶️ Run the Tool



bash

Copy

Edit

python CyberNinjaPhone.py

🛠️ Build .exe (Optional)

To create a standalone executable:



Install PyInstaller:



bash

Copy

Edit

pip install pyinstaller

Create the exe:



bash

Copy

Edit

pyinstaller --noconfirm --onefile CyberNinjaPhone.py

Find the .exe in the dist/ folder and copy it to your USB or SD card.



📁 Folder Structure

arduino

Copy

Edit

CyberNinjaADB/

├── CyberNinjaPhone.py

├── devices.json        ← Your device config

├── Image/              ← GUI icons, if needed

├── LICENSE

├── README.md

└── .gitignore

💬 Tips

If your phone doesn’t connect, make sure it’s on the same WiFi network.



You can add multiple devices to devices.json as needed.



🧠 Coming Soon

Multiple device switching



Bluetooth ADB (if supported)



Auto-device discovery



Built with love by 🧠 Kobe — because walking across the room to grab your phone is so last century.

