# Wiinux: Wii Balance Board Interface for Linux (Python 3)

[English Version Below](#english)

---

# <a name="polish"></a>🇵🇱 Wersja Polska

## O projekcie

Jest to zrefaktoryzowana wersja sterownika Wii Balance Board napisanego pierwotnie w Pythonie. Projekt umożliwia komunikację z wagą Wii Balance Board poprzez Bluetooth, odczyt danych z sensorów masy oraz stanu przycisków.

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

Oryginalne źródła:
- [WiiBoard Simple (Google Code Archive)](https://code.google.com/archive/p/wiiboard-simple/)
- [Blog Tracking Balance](http://trackingbalance.blogspot.fr/2008/08/small-milestone.html)

Dziękujemy pierwotnym twórcom za ich wkład w społeczność Open Source, który umożliwił powstanie tej wersji.

## Instalacja

Wymagane jest środowisko Linux z obsługą Bluetooth.

1. Zainstaluj wymagane pakiety systemowe:
   ```bash
   sudo apt-get install python3-bluez bluetooth libbluetooth-dev
   ```

2. (Opcjonalnie) Stwórz wirtualne środowisko z dostępem do pakietów systemowych:
   ```bash
   python3 -m venv venv --system-site-packages
   source venv/bin/activate
   ```

## Użycie

W projekcie znajdują się teraz dwa skrypty, w zależności od preferowanego sposobu łączenia.

### Krok 0: Jednorazowe sparowanie wagi (SETUP)

Aby waga działała poprawnie i łączyła się przyciskiem POWER, musi zostać sparowana.
Przygotowałem skrypt automatyzujący ten proces.

1. Uruchom skrypt parowania (podobnie jak serwer, z sudo i venv):
   ```bash
   sudo ./venv/bin/python pair_wiiboard.py
   ```
2. Postępuj zgodnie z instrukcjami (wciśnij czerwony przycisk **SYNC** gdy zostaniesz poproszony).
3. Skrypt automatycznie wykryje wagę, sparuje ją i zaufa.

---

### Tryb 1: Standardowy (Client Mode) - `wiiboard.py`
Zalecany do pierwszego parowania. Wymaga wciśnięcia czerwonego przycisku **SYNC** na wadze (lub jeśli waga jest już "Zaufana", można próbować POWER, ale bywa to zawodne).

1. Uruchom skrypt:
   ```bash
   sudo python3 wiiboard.py <ADRES_MAC>
   ```
   (Jeśli nie podasz adresu, skrypt poszuka nowej wagi lub połączy się z zapamiętaną).

### Tryb 2: Serwer (Server Mode) - `wiiboard_server.py` **[ZALECANY NA CO DZIEŃ]**
Ten tryb pozwala na łączenie się poprzez wciśnięcie przycisku **POWER** na wadze. Komputer "czeka" na połączenie od wagi.

### Tryb 2: Codzienny (Native/Power Button) - `wiiboard_native.py` **[NAJLEPSZY]**

To jest najbardziej niezawodny sposób używania wagi na Linuxie. Wykorzystuje on fakt, że nowoczesne kernele Linux (sterownik `hid-wiimote`) automatycznie obsługują wagę po wciśnięciu przycisku POWER.

1.  Zainstaluj bibliotekę `evdev` (jeśli jeszcze nie masz):
    ```bash
    sudo ./venv/bin/pip install evdev
    ```
2.  Uruchom skrypt:
    ```bash
    sudo ./venv/bin/python wiiboard_native.py
    ```
3.  **Wciśnij przycisk POWER** na wadze.
4.  Poczekaj chwilę – skrypt automatycznie wykryje podłączenie wagi, odczyta fabryczną kalibrację i wykona auto-tarowanie.
5.  Wejdź na wagę.

> **Zalety:**
> *   Działa natychmiast po wciśnięciu POWER (jak prawdziwa waga).
> *   Najdokładniejszy pomiar (korzysta z kalibracji fabrycznej zaszytej w EEPROM wagi).
> *   Nie blokuje Bluetooth (korzysta z systemowego sterownika).

---

## Źródła i Technikalia

Projekt powstał na bazie analizy wielu rozwiązań open-source oraz inżynierii wstecznej zachowania sterowników Linuxa.

1.  **Oryginalny sterownik Python (Legacy):**
    *   [wiiboard-simple](https://github.com/nedim/wiiboard-simple) (Nedim Jackman, 2008) – podstawa protokołu Bluetooth.
    *   [python-wiiboard](https://github.com/pierrickkoch/python-wiiboard) (Pierrick Koch, 2016) – refaktoryzacja i obsługa zdarzeń.

2.  **Obsługa przycisku POWER (Linux Kernel):**
    *   Dzięki pracy deweloperów jądra Linux, sterownik `hid-wiimote` automatycznie obsługuje połączenie przyciskiem POWER dla sparowanych urządzeń.
    *   Nasz skrypt `wiiboard_native.py` wykorzystuje interfejs `evdev` do czytania zdarzeń bezpośrednio z jądra, zamiast próbować "walczyć" z systemem o dostęp do Bluetooth.

3.  **Kalibracja (Inżynieria Wsteczna):**
    *   Odkryliśmy, że sterownik kernela udostępnia dane kalibracyjne w `/sys/bus/hid/drivers/wiimote/.../bboard_calib`.
    *   Podczas naszych testów ustaliliśmy poprawny format tego pliku (3 bloki po 4 wartości dla sensorów: 0kg, 17kg, 34kg), co pozwoliło na uzyskanie precyzji lepszej niż w oryginalnych skryptach.
    *   Wykorzystujemy interpolację liniową (z uwzględnieniem faktu, że `evdev` raportuje wartości relatywne - delty), co eliminuje błędy pomiarowe przy lekkim nacisku.

4.  **Inspiracje i wiedza (Stavros):**
    *   Duże podziękowania dla [Stavrosa Korokithakisa](https://www.stavros.io/posts/your-weight-online/) za jego wieloletnią walkę z Linuxem i Balance Boardem.
    *   Jego odkrycie, że trwałe sparowanie ("Permanent Pairing" PIN `0000`) i zaufanie urządzenia ("Trusted") jest kluczem do działania przycisku POWER, było fundamentem naszego podejścia:
        > "I eventually discovered that, for permanent pairing, one must needs use the PIN “000000” [...] Using that, the board was permanently paired with my computer, and I would no longer need to turn it over [...] and then (finally) use it, every single time."
        >
        > "To trust the device so it will connect in the future, run `bt-device --set ##:##:##:##:##:## Trusted 1`"

## Licencja
Projekt udostępniony na licencji LGPL (zgodnie z oryginałem).

---

# <a name="english"></a>🇬🇧 English Version

## About

This is a refactored version of the Wii Balance Board driver originally written in Python. It allows communication with the Wii Balance Board via Bluetooth, reading mass sensor data, and button states.

**Key changes in this version:**
- **Python 3 Compatibility**: Code updated to modern Python 3 standards.
- **Manual Calibration**: Added a "tare" mechanism (manual trigger for calibration) for easier usage.
- **Improved Logging and Error Handling**: Clearer messages and better stability.
- **Native Kernel Mode**: Full support for `hid-wiimote` driver with Power button auto-connection.

> [!NOTE]
> **AI Attribution**
> This refactoring and project preparation was largely assisted by Artificial Intelligence (AI), in collaboration with the user (Human-in-the-Loop).

## Sources and Technical Details

This project is built upon the analysis of various open-source solutions and reverse engineering of Linux driver behavior.

1.  **Original Python Driver (Legacy):**
    *   [wiiboard-simple](https://github.com/nedim/wiiboard-simple) (Nedim Jackman, 2008) – base Bluetooth protocol.
    *   [python-wiiboard](https://github.com/pierrickkoch/python-wiiboard) (Pierrick Koch, 2016) – refactoring and event handling.

2.  **Power Button Support (Linux Kernel):**
    *   Thanks to the work of Linux kernel developers, the `hid-wiimote` driver automatically handles connection via the POWER button for paired devices.
    *   Our `wiiboard_native.py` script uses the `evdev` interface to read events directly from the kernel, rather than fighting the system for Bluetooth access.

3.  **Calibration (Reverse Engineering):**
    *   We discovered that the kernel driver exposes calibration data in `/sys/bus/hid/drivers/wiimote/.../bboard_calib`.
    *   During our testing, we determined the correct format of this file (3 blocks of 4 values for sensors: 0kg, 17kg, 34kg), allowing for precision surpassing the original scripts.
    *   We use linear interpolation (accounting for the fact that `evdev` reports relative values/deltas), eliminating measurement errors at light pressure.

4.  **Inspiration and Knowledge (Stavros):**
    *   Huge thanks to [Stavros Korokithakis](https://www.stavros.io/posts/your-weight-online/) for his years of struggle with Linux and the Balance Board.
    *   His discovery that "Permanent Pairing" (PIN `0000`) and trusting the device ("Trusted") is the key to making the POWER button work was the foundation of our approach:
        > "I eventually discovered that, for permanent pairing, one must needs use the PIN “000000” [...] Using that, the board was permanently paired with my computer, and I would no longer need to turn it over [...] and then (finally) use it, every single time."
        >
        > "To trust the device so it will connect in the future, run `bt-device --set ##:##:##:##:##:## Trusted 1`"

## Credits

This project builds upon the work of brilliant developers:
- **Nedim Jackman** (2008) - Original creator of the Python version.
- **Pierrick Koch** (2016) - Further development and fixes.
- **Stavros Korokithakis** - Critical insights on pairing and connection management.

Original sources:
- [WiiBoard Simple (Google Code Archive)](https://code.google.com/archive/p/wiiboard-simple/)
- [Blog Tracking Balance](http://trackingbalance.blogspot.fr/2008/08/small-milestone.html)

We thank the original creators for their contribution to the Open Source community, which made this version possible.

## License

This project is licensed under the **LGPL (GNU Lesser General Public License)**, respecting the license of the original work. See the `LICENSE` file for details.
