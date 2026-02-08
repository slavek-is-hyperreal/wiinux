# Wiinux: Wii Accessories Library for Linux (Python 3)

# ENGLISH VERSION (PL BELOW)

---

# <a name="english"></a>🇬🇧 English Version

## About the Project

Wiinux is an advanced library for handling Wii accessories (Balance Board and Wiimote) on Linux, utilizing native kernel drivers (`hid-wiimote`). The project enables precise weight measurement, infrared (IR) point tracking, and interaction with "semantic pointer" objects.

**Main Components:**
- **Wii Balance Board**: Mass reading from 4 sensors, auto-calibration, and taring.
- **Wiimote IR Eye**: Tracking up to 4 IR points, Morse/VLC signal decoding, and signal stability analysis.
- **Unified Library (`Wii_accessories_bib.py`)**: A single base class to handle all accessories in native mode (`evdev`).

**Main Changes in this Version:**
- **Python 3 Compatibility**: Code has been updated and adapted to modern Python 3 standards.
- **Manual Calibration**: Added a "tare" mechanism (manual calibration trigger) for easier use.
- **Improved Logging and Error Handling**: Clearer messages and better stability.

> [!NOTE]
> **AI Attribution / AI Support**
> This refactoring and project preparation was largely performed with the support of Artificial Intelligence (AI), in collaboration with the user (Human-in-the-Loop).

## Authors and Credits

This project is based on the work of brilliant programmers:
- **Nedim Jackman** (2008) - Original creator of the Python version.
- **Pierrick Koch** (2016) - Further development and fixes.
- **Stavros Korokithakis** - Critical discoveries regarding PIN `0000` pairing.

Original Sources:
- [WiiBoard Simple (Google Code Archive)](https://code.google.com/archive/p/wiiboard-simple/)
- [Blog Tracking Balance](http://trackingbalance.blogspot.fr/2008/08/small-milestone.html)

Thank you to the original creators for their contribution to the Open Source community, which made this version possible.

## Key R&D Discoveries (IR)

During the work on infrared support, we discovered critical technical phenomena:
- **Frequency Aliasing**: Standard TV remotes pulse at a frequency of 38kHz. The Wiimote camera samples images at 100Hz. This causes "ghosts" and artifacts (blooming), which were previously mistaken for noise.
- **Ghosting**: We identified that one strong IR emitter (e.g., a remote) generates "islands" of repeatable coordinates on the PixArt sensor. We can use this for the **Spatial Fingerprint** of a button.

## Installation

A Linux environment with Bluetooth support is required.

1. Install required system packages:
   ```bash
   sudo apt-get install python3-bluez bluetooth libbluetooth-dev
   ```

2. Install the `evdev` library:
   ```bash
   sudo ./venv/bin/pip install evdev
   ```

## Usage

### Step 0: One-time Accessory Pairing (SETUP)

For devices to work correctly and connect automatically, they must be paired. I have prepared a script to automate this process.

1. Run the pairing script (with sudo and venv):
   ```bash
   sudo ./venv/bin/python pair_wiimote.py  # For the remote
   sudo ./venv/bin/python pair_wiiboard.py # For the board
   ```
2. Follow the instructions (press the red **SYNC** button when prompted).

---

### Mode 1: Unified Library (`Wii_accessories_bib.py`) **[RECOMMENDED]**
This is the main entry point for modern accessory handling.

1.  **Run Diagnostics**:
    ```bash
    sudo ./venv/bin/python Wii_accessories_bib.py
    ```
2.  **Raw Mode (Raw Discovery)**:
    If you want to see pure data from the IR sensor without filtration:
    ```bash
    sudo ./venv/bin/python Wii_accessories_bib.py --raw
    ```

### Mode 2: Dedicated Board (`wiiboard_native.py`)
Uses the `hid-wiimote` driver to handle the board with the POWER button.

1.  Run the script:
    ```bash
    sudo ./venv/bin/python wiiboard_native.py
    ```
2.  **Press the POWER button** on the board.

---

## Programming Games and Apps (API)

The file `Wii_accessories_bib.py` can be used as a library in your projects.

```python
from Wii_accessories_bib import WiiEyeNative

eye = WiiEyeNative()
if eye.connect():
    while True:
        eye.update()
        if eye.points[0]:
            print(f"Point 0 at position: {eye.points[0]}")
```

See the file `example_game.py` for a ready-made example of implementing a simple body-balance game (ASCII).

---

## Sources and Technical Details

The project was created based on the analysis of many open-source solutions and reverse engineering of Linux driver behavior.

1.  **Original Python Driver (Legacy):**
    *   [wiiboard-simple](https://github.com/nedim/wiiboard-simple) (Nedim Jackman, 2008) – base of the Bluetooth protocol.
    *   [python-wiiboard](https://github.com/pierrickkoch/python-wiiboard) (Pierrick Koch, 2016) – refactoring and event handling.

2.  **POWER Button Support (Linux Kernel):**
    *   Thanks to the work of Linux kernel developers, the `hid-wiimote` driver automatically handles connection via the POWER button for paired devices. Our scripts use the `evdev` interface to read events directly from the kernel.

3.  **Calibration (Reverse Engineering):**
    *   I discovered that the kernel driver exposes calibration data in `/sys/bus/hid/drivers/wiimote/.../bboard_calib`. 
    *   The format of this file (3 blocks of 4 values for sensors: 0kg, 17kg, 34kg) allows for precision better than original scripts thanks to linear interpolation.

4.  **Inspiration and Knowledge (Stavros):**
    *   Big thanks to [Stavros Korokithakis](https://www.stavros.io/posts/your-weight-online/) for his years-long struggle with Linux. His discovery that PIN `0000` pairing and trusting the device ("Trusted") is the key to POWER button functionality was the foundation of my approach.

## Future: Object Recognition
The project offers two paths for object identification:
- **Spatial Method**: Recognizing geometric arrangements of multiple LEDs (fast, requires battery/LED array).
- **Temporal Method (VLC)**: Recognizing the blinking sequence of a single LED (slower, simple construction).

## License
Project released under the LGPL license (as per the original).

---

# <a name="polish"></a>🇵🇱 Wersja Polska

## O projekcie

Wiinux to zaawansowana biblioteka do obsługi akcesoriów Wii (Balance Board oraz Wiimote) na systemie Linux, wykorzystująca natywne sterowniki jądra (`hid-wiimote`). Projekt umożliwia precyzyjny odczyt masy, śledzenie punktów podczerwieni (IR) oraz interakcję z obiektami "semantic pointer".

**Główne komponenty:**
- **Wii Balance Board**: Odczyt masy z 4 sensorów, auto-kalibracja i tarowanie.
- **Wiimote IR Eye**: Śledzenie do 4 punktów IR, dekodowanie sygnałów Morse'a/VLC oraz analiza stabilności sygnału.
- **Unified Library (`Wii_accessories_bib.py`)**: Jedna klasa bazowa do obsługi wszystkich akcesoriów w trybie natywnym (`evdev`).

**Główne zmiany w tej wersji:**
- **Kompatybilność z Python 3**: Kod został zaktualizowany i dostosowany do nowoczesnych standardów Pythona 3.
- **Ręczna kalibracja**: Dodano mechanizm "tarowania" (manualnego wyzwalania kalibracji), co ułatwia pracę z urządzeniem.
- **Usprawnione logowanie i obsługa błędów**: Czytelniejsze komunikaty i lepsza stabilność.

> [!NOTE]
> **AI Attribution / Wsparcie AI**
> Ten refaktoring oraz przygotowanie projektu do publikacji zostało wykonane w dużej mierze przy wsparciu Sztucznej Inteligencji (AI), we współpracy z użytkownikiem (Human-in-the-Loop).

## Autorzy i Źródła (Credits)

Ten projekt bazuje na pracy wspaniałych programistów:
- **Nedim Jackman** (2008) - Oryginalny twórca wersji Pythonowej.
- **Pierrick Koch** (2016) - Dalszy rozwój i poprawki.
- **Stavros Korokithakis** - Kluczowe odkrycia dotyczące parowania PIN `0000`.

Oryginalne źródła:
- [WiiBoard Simple (Google Code Archive)](https://code.google.com/archive/p/wiiboard-simple/)
- [Blog Tracking Balance](http://trackingbalance.blogspot.fr/2008/08/small-milestone.html)

Dziękuję pierwotnym twórcom za ich wkład w społeczność Open Source, który umożliwił powstanie tej wersji.

## Kluczowe Odkrycia R&D (IR)

Podczas prac nad obsługą podczerwieni odkryliśmy krytyczne zjawiska techniczne:
- **Aliasing Częstotliwości**: Standardowe piloty TV migają z częstotliwością 38kHz. Kamera Wiimote próbkuje obraz z prędkością 100Hz. Powoduje to powstawanie "duchów" i artefaktów (blooming), które wcześniej były brane za szum.
- **Ghosting (Duchowanie)**: Zidentyfikowaliśmy, że jeden silny emiter IR (np. pilot) generuje "wyspy" powtarzalnych współrzędnych na sensorze PixArt. Możemy to wykorzystać do **Przestrzennego Odcisku Palca (Spatial Fingerprint)** przycisku.

## Instalacja

Wymagane jest środowisko Linux z obsługą Bluetooth.

1. Zainstaluj wymagane pakiety systemowe:
   ```bash
   sudo apt-get install python3-bluez bluetooth libbluetooth-dev
   ```

2. Zainstaluj bibliotekę `evdev`:
   ```bash
   sudo ./venv/bin/pip install evdev
   ```

## Użycie

### Krok 0: Jednorazowe sparowanie akcesorium (SETUP)

Aby urządzenia działały poprawnie i łączyły się automatycznie, muszą zostać sparowane. Przygotowałem skrypt automatyzujący ten proces.

1. Uruchom skrypt parowania (z sudo i venv):
   ```bash
   sudo ./venv/bin/python pair_wiimote.py  # Dla pilota
   sudo ./venv/bin/python pair_wiiboard.py # Dla wagi
   ```
2. Postępuj zgodnie z instrukcjami (wciśnij czerwony przycisk **SYNC** gdy zostaniesz poproszony).

---

### Tryb 1: Biblioteka Zunifikowana (`Wii_accessories_bib.py`) **[ZALECANE]**
To jest główny punkt wejścia do nowoczesnej obsługi akcesoriów.

1.  **Uruchomienie Diagnostyki**:
    ```bash
    sudo ./venv/bin/python Wii_accessories_bib.py
    ```
2.  **Tryb Surowy (Raw Discovery)**:
    Jeśli chcesz zobaczyć czyste dane z sensora IR bez filtracji:
    ```bash
    sudo ./venv/bin/python Wii_accessories_bib.py --raw
    ```

### Tryb 2: Dedykowana Waga (`wiiboard_native.py`)
Wykorzystuje sterownik `hid-wiimote` do obsługi wagi przyciskiem POWER.

1.  Uruchom skrypt:
    ```bash
    sudo ./venv/bin/python wiiboard_native.py
    ```
2.  **Wciśnij przycisk POWER** na wadze.

---

## Programowanie gier i aplikacji (API)

Plik `Wii_accessories_bib.py` może być używany jako biblioteka w Twoich projektach.

```python
from Wii_accessories_bib import WiiEyeNative

eye = WiiEyeNative()
if eye.connect():
    while True:
        eye.update()
        if eye.points[0]:
            print(f"Punkt 0 na pozycji: {eye.points[0]}")
```

Zobacz plik `example_game.py` dla gotowego przykładu implementacji prostej gry opartej na balansie ciała (ASCII).

---

## Źródła i Technikalia

Projekt powstał na bazie analizy wielu rozwiązań open-source oraz inżynierii wstecznej zachowania sterowników Linuxa.

1.  **Oryginalny sterownik Python (Legacy):**
    *   [wiiboard-simple](https://github.com/nedim/wiiboard-simple) (Nedim Jackman, 2008) – podstawa protokołu Bluetooth.
    *   [python-wiiboard](https://github.com/pierrickkoch/python-wiiboard) (Pierrick Koch, 2016) – refaktoryzacja i obsługa zdarzeń.

2.  **Obsługa przycisku POWER (Linux Kernel):**
    *   Dzięki pracy deweloperów jądra Linux, sterownik `hid-wiimote` automatycznie obsługuje połączenie przyciskiem POWER dla sparowanych urządzeń. Nasze skrypty wykorzystują interfejs `evdev` do czytania zdarzeń bezpośrednio z jądra.

3.  **Kalibracja (Inżynieria Wsteczna):**
    *   Odkryłem, że sterownik kernela udostępnia dane kalibracyjne w `/sys/bus/hid/drivers/wiimote/.../bboard_calib`. 
    *   Format tego pliku (3 bloki po 4 wartości dla sensorów: 0kg, 17kg, 34kg) pozwala na uzyskanie precyzji lepszej niż w oryginalnych skryptach dzięki interpolacji liniowej.

4.  **Inspiracje i wiedza (Stavros):**
    *   Duże podziękowania dla [Stavrosa Korokithakisa](https://www.stavros.io/posts/your-weight-online/) za jego wieloletnią walkę z Linuxem. Jego odkrycie, że parowanie PIN `0000` i zaufanie urządzenia ("Trusted") jest kluczem do działania przycisku POWER, było fundamentem mojego podejścia.

## Przyszłość: Rozpoznawanie Przedmiotów
Projekt oferuje dwie ścieżki identyfikacji obiektów:
- **Metoda Przestrzenna**: Rozpoznawanie geometrycznego układu wielu diod (szybkie, wymaga baterii/układu diod).
- **Metoda Czasowa (VLC)**: Rozpoznawanie sekwencji migania jednej diody (wolniejsze, prosta budowa).

## Licencja
Projekt udostępniony na licencji LGPL (zgodnie z oryginałem).
