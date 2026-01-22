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

Upewnij się, że Bluetooth jest włączony.

1. Znajdź adres MAC swojej wagi (wciśnij czerwony guzik *SYNC* pod klapką baterii):
   ```bash
   bluetoothctl scan on
   ```
2. Uruchom skrypt (z uprawnieniami roota, jeśli wymagane dla Bluetooth):
   ```bash
   sudo python3 wiiboard.py <ADRES_MAC>
   ```
   Jeśli nie podasz adresu, skrypt spróbuje połączyć się z **ostatnio zapamiętaną wagą**. Jeśli to się nie uda (lub nie ma zapisanego adresu), rozpocznie skanowanie otoczenia (pamiętaj wtedy o wciśnięciu *SYNC*).

   > Adres ostatnio połączonej wagi jest zapisywany w pliku `~/.wiiboard_config`.

---

# <a name="english"></a>🇬🇧 English Version

## About

This is a refactored version of the Wii Balance Board driver originally written in Python. It allows communication with the Wii Balance Board via Bluetooth, reading mass sensor data, and button states.

**Key changes in this version:**
- **Python 3 Compatibility**: Code updated to modern Python 3 standards.
- **Manual Calibration**: Added a "tare" mechanism (manual trigger for calibration) for easier usage.
- **Improved Logging and Error Handling**: Clearer messages and better stability.

> [!NOTE]
> **AI Attribution**
> This refactoring and project preparation was largely assisted by Artificial Intelligence (AI), in collaboration with the user (Human-in-the-Loop).

## Credits

This project builds upon the work of brilliant developers:
- **Nedim Jackman** (2008) - Original creator of the Python version.
- **Pierrick Koch** (2016) - Further development and fixes.

Original sources:
- [WiiBoard Simple (Google Code Archive)](https://code.google.com/archive/p/wiiboard-simple/)
- [Blog Tracking Balance](http://trackingbalance.blogspot.fr/2008/08/small-milestone.html)

We thank the original creators for their contribution to the Open Source community, which made this version possible.

## License

This project is licensed under the **LGPL (GNU Lesser General Public License)**, respecting the license of the original work. See the `LICENSE` file for details.
