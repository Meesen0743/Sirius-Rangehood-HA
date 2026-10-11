# Sirius Smart-Switch Range Hood - Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/default)
[![Validate](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)

Custom component for Home Assistant to control **Sirius Smart-Switch Range Hoods** via the Sirius Cloud IoT platform (P.G.A. IoT infrastructure).

Tested on models including:
- **Sirius SL926 DL 850 T-SHAPE ARISIT** (and all models running Sirius / PGA IoT firmware).

---

## 🌟 Features Supported

- **Fan Entity (`fan.sirius_hood_fan`)**:
  - Turn On / Off
  - 4-Speed variable control (Speeds 1, 2, 3, 4)
  - Boost mode preset (timed high extraction)
  - Real-time live status push via MQTT
  - Fan airflow sensor (`m³/h`) and wattage consumption (`W`)
- **Light Entities (`light.sirius_hood_main_light`, `light.sirius_hood_ambient_light`)**:
  - Turn On / Off
  - Brightness slider (10% – 100%)
  - Color temperature slider (2700K – 6000K warm-to-cool Kelvin)
  - Light power sensor (`W`)
- **Switches (`switch.sirius_hood_*`)**:
  - **Smart-Switch Bi-Power**: Toggle between Energy-Saving Bi-Power mode and maximum extraction
  - **24h Clean Air Mode**: Cycles fan periodically to keep kitchen air fresh
  - **Auto Mode**: Automatic sensor-based speed regulation
  - **Air Quality Monitoring**: Real-time sensor monitoring
- **Sensors (`sensor.sirius_hood_*`)**:
  - Real-time Fan Power (`W`) & Light Power (`W`)
  - Air Flow Rate (`m³/h`)
  - CO₂ Concentration (`ppm`)
  - IAQ Index (Indoor Air Quality)
  - Temperature (°C) & Humidity (%)
  - Main & Secondary Filter Life remaining

---

## 📦 Installation via HACS (Recommended)

1. Open **HACS** in your Home Assistant sidebar.
2. Click the **3 dots** menu in the top right corner $\rightarrow$ select **Custom repositories**.
3. In the dialog, enter:
   - **Repository:** `https://github.com/Meesen0743/Sirius-Rangehood-HA`
   - **Type:** `Integration`
4. Click **Add**.
5. Search for **Sirius Smart-Switch Range Hood** in HACS and click **Download**.
6. **Restart Home Assistant**.

---

## 🚀 Setup & Configuration

### 1. Account Setup & Device Sharing
Because Sirius cloud accounts are designed for single-session mobile phone apps, it is recommended to create and use a dedicated secondary Sirius account to connect Home Assistant without logging out your mobile phone.

1. In your primary Sirius mobile app, open your hood settings $\rightarrow$ tap **Share Device**.
2. Enter your secondary Sirius account email as the guest user.
3. Accept the sharing invitation on your secondary account.

### 2. Add the Integration in Home Assistant
1. In Home Assistant, go to **Settings** $\rightarrow$ **Devices & Services**.
2. Click **Add Integration** in the bottom right corner.
3. Search for **Sirius Smart-Switch Range Hood**.
4. Enter the credentials of your secondary Sirius account:
   - **Email**: `your_secondary_account@example.com`
   - **Password**: `your_password`
5. Click **Submit**. Your range hood fan, lights, switches, and sensors will immediately appear!
