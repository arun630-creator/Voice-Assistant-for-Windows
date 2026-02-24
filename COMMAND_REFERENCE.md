# Nova Voice Assistant — Complete Command Reference

> **Wake words:** Say **"Hello"**, **"Hi"**, or **"Hey"** to activate Nova, then speak your command.
> Example: *"Hello, open Chrome"* or *"Hi Nova, what time is it"*

---

## Table of Contents

1. [Informational](#1-informational)
2. [App Control](#2-app-control)
3. [Volume & Audio](#3-volume--audio)
4. [Brightness](#4-brightness)
5. [Power Control](#5-power-control)
6. [Network (Wi-Fi & Bluetooth)](#6-network-wi-fi--bluetooth)
7. [System Info](#7-system-info)
8. [Timer](#8-timer)
9. [Clipboard](#9-clipboard)
10. [File & Folder Management](#10-file--folder-management)
11. [Messaging (WhatsApp / Telegram / Signal)](#11-messaging-whatsapp--telegram--signal)
12. [Email](#12-email)
13. [Contacts](#13-contacts)
14. [Media Playback](#14-media-playback)
15. [Web Browsing & Search](#15-web-browsing--search)
16. [Screenshots](#16-screenshots)
17. [Notes & Memory](#17-notes--memory)
18. [Desktop App / System Tray](#18-desktop-app--system-tray)

---

## 1. Informational

| Command | Example Phrases |
|---------|----------------|
| **Get current time** | "What time is it" · "Tell me the time" · "Current time" · "Time" |
| **Get today's date** | "What's the date" · "Today's date" · "What day is it" · "Date" |
| **Greeting** | "Hello" · "Hey" · "Hi" · "Good morning" · "Good afternoon" · "What's up" |

---

## 2. App Control

Nova supports **80+ apps** out of the box (browsers, Office, media, dev tools, games, etc.). If an app isn't whitelisted, Nova will try to find it via Windows Start Menu search.

| Command | Example Phrases |
|---------|----------------|
| **Open an app** | "Open Chrome" · "Launch VS Code" · "Start Spotify" · "Run calculator" |
| **Close an app** | "Close Chrome" · "Quit Spotify" · "Exit Notepad" · "Kill Discord" · "Stop Teams" |

### Supported Apps (partial list)

| Category | Apps |
|----------|------|
| **Browsers** | Chrome, Firefox, Edge, Brave, Opera, Vivaldi, Tor |
| **System** | Notepad, Calculator, File Explorer, CMD, Terminal, PowerShell, Task Manager, Control Panel, Settings, Snipping Tool |
| **Office** | Word, Excel, PowerPoint, Outlook, OneNote, Access, Publisher, Teams |
| **Media** | Paint, Photos, Spotify, VLC, Media Player, Movies and TV, Audacity, OBS Studio |
| **Development** | VS Code, Visual Studio, Android Studio, IntelliJ, PyCharm, Sublime Text, Notepad++, Git Bash, Postman, Docker |
| **Communication** | Discord, Telegram, WhatsApp, Zoom, Skype, Slack, Signal |
| **Gaming** | Steam, Epic Games Launcher, Xbox Game Bar |
| **Productivity** | Notion, Obsidian, Todoist, Bitwarden, 1Password, 7-Zip, WinRAR, Blender, GIMP |

---

## 3. Volume & Audio

| Command | Example Phrases |
|---------|----------------|
| **Set volume** (0–100) | "Set volume to 50" · "Change volume to 80" · "Turn volume to 30 percent" · "Put volume to 60" |
| **Volume up** (+10%) | "Volume up" · "Turn it up" · "Make it louder" · "Turn the volume higher" |
| **Volume down** (−10%) | "Volume down" · "Turn it down" · "Make it quieter" · "Turn the volume lower" |
| **Mute** | "Mute" · "Mute the volume" · "Silence the speakers" · "Mute audio" |
| **Unmute** | "Unmute" · "Unmute the volume" · "Unmute audio" |

---

## 4. Brightness

| Command | Example Phrases |
|---------|----------------|
| **Set brightness** (0–100) | "Set brightness to 70" · "Change brightness to 50" · "Adjust screen brightness to 40 percent" |

---

## 5. Power Control

| Command | Example Phrases |
|---------|----------------|
| **Shut down** | "Shut down" · "Shutdown" · "Power off" · "Turn off the computer" · "Turn off the PC" |
| **Restart** | "Restart" · "Reboot" · "Restart the PC" · "Reboot the computer" |
| **Cancel shutdown** | "Cancel shutdown" · "Abort restart" · "Stop the shutdown" |
| **Lock PC** | "Lock" · "Lock the PC" · "Lock the computer" · "Lock screen" |
| **Sleep** | "Sleep" · "Sleep the PC" · "Put computer to sleep" · "Suspend" |
| **Hibernate** | "Hibernate" · "Hibernate the PC" · "Hibernate the computer" |

---

## 6. Network (Wi-Fi & Bluetooth)

| Command | Example Phrases |
|---------|----------------|
| **Wi-Fi on** | "Turn on Wi-Fi" · "Enable Wi-Fi" · "Connect Wi-Fi" · "Switch on Wi-Fi" · "Wi-Fi on" |
| **Wi-Fi off** | "Turn off Wi-Fi" · "Disable Wi-Fi" · "Disconnect Wi-Fi" · "Switch off Wi-Fi" · "Wi-Fi off" |
| **Wi-Fi status** | "Wi-Fi status" · "Am I connected" · "What's my Wi-Fi" |
| **Bluetooth on** | "Turn on Bluetooth" · "Enable Bluetooth" · "Switch on Bluetooth" · "Bluetooth on" · "Bluetooth turn on" |
| **Bluetooth off** | "Turn off Bluetooth" · "Disable Bluetooth" · "Switch off Bluetooth" · "Bluetooth off" · "Bluetooth turn off" |

> Nova first tries the WinRT Radio API to toggle Bluetooth programmatically. If that fails, it opens Settings and auto-clicks the toggle via UI automation.

### 6b. Quick Settings Toggles

| Command | Example Phrases |
|---------|----------------|
| **Night Light on** | "Turn on night light" · "Enable night light" · "Night light on" · "Night light turn on" |
| **Night Light off** | "Turn off night light" · "Disable night light" · "Night light off" |
| **Airplane Mode on** | "Turn on airplane mode" · "Enable airplane mode" · "Flight mode on" · "Airplane mode turn on" |
| **Airplane Mode off** | "Turn off airplane mode" · "Disable airplane mode" · "Flight mode off" |
| **Energy Saver on** | "Turn on energy saver" · "Enable battery saver" · "Energy saver on" · "Battery saver turn on" |
| **Energy Saver off** | "Turn off energy saver" · "Disable battery saver" · "Energy saver off" |
| **Mobile Hotspot on** | "Turn on hotspot" · "Enable mobile hotspot" · "Hotspot on" · "Switch on hotspot" |
| **Mobile Hotspot off** | "Turn off hotspot" · "Disable mobile hotspot" · "Hotspot off" |

> These toggles open the corresponding Windows Settings page and auto-click the toggle switch via UI automation.

---

## 7. System Info

| Command | Example Phrases |
|---------|----------------|
| **Battery status** | "Battery status" · "Battery level" · "How much battery" · "Check the battery" · "Charge remaining" · "Battery" |
| **IP address** | "What's my IP" · "My IP address" · "Show my IP" · "IP address" |

---

## 8. Timer

| Command | Example Phrases |
|---------|----------------|
| **Set a timer** | "Set a timer for 5 minutes" · "Timer for 30 seconds" · "Set timer for 1 hour 30 minutes" · "Start a timer for 2 minutes and 30 seconds" · "Remind me in 10 minutes" |
| **Cancel timer** | "Cancel the timer" · "Stop the timer" · "Clear timer" · "Remove timer" |

> Opens the Windows Clock app and also sets a background timer. Nova speaks "Time's up!" when the timer expires.

---

## 9. Clipboard

| Command | Example Phrases |
|---------|----------------|
| **Read clipboard** | "Read clipboard" · "Show clipboard" · "What's on the clipboard" · "Paste clipboard" |
| **Clear clipboard** | "Clear the clipboard" · "Empty clipboard" · "Wipe the clipboard" |

---

## 10. File & Folder Management

| Command | Example Phrases |
|---------|----------------|
| **Create folder** | "Create folder Projects" · "Make a folder called Notes" · "New directory Backup on Desktop" |
| **Delete folder** | "Delete folder old_stuff" · "Remove the folder Temp" |
| **Rename folder** | "Rename folder OldName to NewName" · "Rename the directory Draft to Final" |
| **Open folder** | "Open folder Documents" · "Show the folder Downloads" · "Go to the folder Projects" |
| **Open special folders** | "Open Desktop" · "Open my Documents" · "Open Downloads" · "Open Music" · "Open Pictures" · "Open Videos" · "Open Recycle Bin" · "Open Recent Files" |
| **List files** | "List files in Documents" · "Show files in Desktop" · "What files are in Downloads" · "What's in my Music" |

> "List files" opens the folder in File Explorer so you can browse visually.
| **Empty recycle bin** | "Empty the recycle bin" · "Clear the trash" · "Clean the recycle bin" |

> **Safe roots:** File operations are restricted to Desktop, Documents, Downloads, and configured drives for safety.

---

## 11. Messaging (WhatsApp / Telegram / Signal)

| Command | Example Phrases |
|---------|----------------|
| **Send by contact name** | "Send hello to Varun on WhatsApp" · "WhatsApp send good morning to Mom" · "Text Ravi saying I'll be late on Telegram" · "Message Dad that I'm coming via Signal" |
| **Send to phone number** | "Send hi to +919876543210" · "Send hello to 9876543210" · "Send meeting at 5 to +1 555 123 4567" |
| **Default app** | If you omit the app name, WhatsApp is used by default |

> **Phone numbers:** 10-digit numbers are auto-prefixed with +91 (India). Include country code for international numbers.
> **Contacts:** Names are matched against your saved contacts in `data/contacts.json`.

---

## 12. Email

| Command | Example Phrases |
|---------|----------------|
| **Send email (to address)** | "Email user@example.com saying meeting at 3pm" · "Send an email to boss@company.com about the project update" · "Mail admin@site.com with the report" |
| **Send email (to contact name)** | "Send email to Varun saying hello" · "Email Ravi about tomorrow's meeting" |

> Opens your default email client with the recipient and body pre-filled.

---

## 13. Contacts

| Command | Example Phrases |
|---------|----------------|
| **Add contact** | "Add contact John phone +919876543210" · "Save contact Alice email alice@example.com" · "New contact Bob number 9876543210" |
| **List contacts** | "Show my contacts" · "List contacts" · "Display contacts" |

> Contacts are stored locally in `data/contacts.json`.

---

## 14. Media Playback

| Command | Example Phrases |
|---------|----------------|
| **Play on YouTube** | "Play Despacito on YouTube" · "Watch funny cats on YouTube" · "Play pilla raa on YouTube" |
| **Play on Spotify** | "Play Shape of You on Spotify" · "Listen to jazz on Spotify" · "Spotify play workout playlist" |

> YouTube: Nova opens the search results and auto-plays the first video. Spotify: Opens the Spotify web search.

---

## 15. Web Browsing & Search

| Command | Example Phrases |
|---------|----------------|
| **Open a website** | "Open google.com" · "Go to github.com" · "Visit https://reddit.com" · "Browse wikipedia.org" |
| **Search the web** | "Search how to make pasta" · "Google Python tutorials" · "Look up weather forecast" · "Find online best laptops 2025" |

---

## 16. Screenshots

| Command | Example Phrases |
|---------|----------------|
| **Take screenshot** | "Take a screenshot" · "Capture screenshot" · "Grab a screen cap" · "Take a snip" |

> Screenshots are saved to Desktop as `screenshot_YYYYMMDD_HHMMSS.png` using PowerShell .NET. Falls back to pyautogui or Snipping Tool if needed.

---

## 17. Notes & Memory

| Command | Example Phrases |
|---------|----------------|
| **Save a note** | "Remember that my password is 1234" · "Save meeting is at 3pm" · "Note buy groceries tomorrow" · "Store the WiFi password is Nova123" |
| **Recall notes** | "What did I tell you to remember" · "Recall notes" · "Show notes" · "What did I say" |

> Notes persist across sessions in the local database.

---

## 18. Desktop App / System Tray

Nova can run as a **background desktop app** — no terminal window needed.

### How to Launch

| Method | Command / Action |
|--------|------------------|
| **Tray mode (terminal)** | `python main.py --tray` or `python tray_app.py` |
| **Silent launch (no console)** | Double-click `nova_start.bat` |
| **Start with Windows** | Right-click tray icon → check "Start with Windows" |

### System Tray Icon States

| Icon Colour | Meaning |
|-------------|----------|
| 🟢 **Green** | Listening for wake word — assistant is active |
| 🟠 **Orange** | Recording your command — speak now |
| ⚪ **Grey** | Assistant is stopped / paused |
| 🔴 **Red** | An error occurred |

### Tray Menu Options

| Option | Description |
|--------|-------------|
| **Start Assistant** | Begin listening (shown when stopped) |
| **Stop Assistant** | Pause the assistant (shown when running) |
| **Start with Windows** | Toggle auto-launch at Windows login (registry) |
| **Status** | Shows current state (Listening / Recording / Stopped) |
| **Quit Nova** | Stop the assistant and exit completely |

> The tray app uses `pythonw.exe` so no console window is shown. Nova speaks "Nova is ready" when the assistant starts.

---

## Quick Tips

| Tip | Details |
|-----|--------|
| **Wake word** | Say "Hello", "Hi", or "Hey" before your command |
| **Natural phrasing** | Speak naturally — Nova understands many variations of the same command |
| **App names** | Use common names: "Chrome" not "Google Chrome.exe" |
| **Keyboard mode** | `python main.py --keyboard` to type commands instead of speaking |
| **Tray mode** | `python main.py --tray` to run as a background desktop app |
| **Compound commands** | Combine actions: "Open WhatsApp and send hello to Varun" |
| **Cancel** | Say "Cancel" during recording to abort the current command |

---

*Generated for Nova Voice Assistant v1.2 — 53+ intents, 80+ apps, 60+ regex patterns, system tray desktop app*
