#! /usr/bin/env python3
""" Wii Fit Balance Board (WBB) in python 3

Wersja z manualnym wyzwalaczem kalibracji.

usage: wiiboard_refactored.py [-d] [address]
tip: use `bluetoothctl scan on` to get a list of devices addresses

Requires `pybluez` installed via `apt-get install python3-bluez` and a
venv created with `--system-site-packages`.

LICENSE LGPL <http://www.gnu.org/licenses/lgpl.html>
        (c) Nedim Jackman 2008 (c) Pierrick Koch 2016
        Refactored for Python 3 by Logos/Sławek 2025
"""
import time
import logging
import collections
import bluetooth
import sys
import os
import subprocess

# --- Stałe Wiiboard ---
CONTINUOUS_REPORTING = b'\x04'
COMMAND_LIGHT = b'\x11'
COMMAND_REPORTING = b'\x12'
COMMAND_REQUEST_STATUS = b'\x15'
COMMAND_REGISTER = b'\x16'
COMMAND_READ_REGISTER = b'\x17'
INPUT_STATUS = b'\x20'
INPUT_READ_DATA = b'\x21'
EXTENSION_8BYTES = b'\x32'
BUTTON_DOWN_MASK = 0x08
LED1_MASK = 0x10
BATTERY_MAX = 200.0
TOP_RIGHT = 0
BOTTOM_RIGHT = 1
TOP_LEFT = 2
BOTTOM_LEFT = 3
BLUETOOTH_NAME = "Nintendo RVL-WBC-01"

# --- Konfiguracja logowania ---
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('[%(asctime)s][%(levelname)s] %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# --- Funkcja pomocnicza ---
def bytes_to_int(b):
    """Konwertuje ciąg bajtów (bytes) na liczbę całkowitą (int)."""
    return int.from_bytes(b, 'big')

def discover(duration=6, prefix=BLUETOOTH_NAME):
    """Wyszukuje urządzenia Bluetooth."""
    logger.info(f"Skanowanie urządzeń Bluetooth przez {duration} sekund...")
    devices = bluetooth.discover_devices(duration=duration, lookup_names=True)
    logger.debug(f"Znaleziono urządzenia: {devices}")
    return [address for address, name in devices if name.startswith(prefix)]

class Wiiboard:
    """Główna klasa do obsługi Wii Balance Board."""
    def __init__(self, address=None):
        self.controlsocket = None
        self.receivesocket = None
        self.calibration = [[10000.0] * 4] * 3
        self.calibration_requested = False
        self.light_state = False
        self.button_down = False
        self.battery = 0.0
        self.running = True
        if address:
            self.connect(address)

    def connect(self, address):
        """Łączy się z podanym adresem MAC i czeka na sygnał do kalibracji."""
        logger.info(f"Łączenie z {address}...")
        try:
            self.controlsocket = bluetooth.BluetoothSocket(bluetooth.L2CAP)
            self.receivesocket = bluetooth.BluetoothSocket(bluetooth.L2CAP)
            self.controlsocket.connect((address, 0x11))
            self.receivesocket.connect((address, 0x13))
            logger.info("Połączenie udane!")

            # <<< NOWA ZMIANA TUTAJ
            print("\n-----------------------------------------------------------------")
            print(">>> Połóż wagę na płaskiej powierzchni.")
            print(">>> Naciśnij klawisz 't' (od tarowanie) i Enter, aby rozpocząć.")
            print("-----------------------------------------------------------------")
            while True:
                key = input()
                if key.lower() == 't':
                    break
                else:
                    print("Oczekuję na 't'...")
            # >>> KONIEC ZMIANY

            logger.info("Rozpoczynam kalibrację...")
            logger.debug("Wysyłanie żądania o dane kalibracyjne...")
            self.send(COMMAND_READ_REGISTER, b"\x04\xA4\x00\x24\x00\x18")
            self.calibration_requested = True

            logger.debug("Łączenie z rozszerzeniem wagi, aby czytać dane masowe...")
            self.send(COMMAND_REGISTER, b"\x04\xA4\x00\x40\x00")

            logger.debug("Żądanie statusu...")
            self.status()
            self.light(False)
            return True
        except bluetooth.btcommon.BluetoothError as e:
            logger.error(f"Nie udało się połączyć. Upewnij się, że urządzenie jest sparowane. Błąd: {e}")
            self.close()
            return False

    def send(self, *data):
        if not self.controlsocket: return
        self.controlsocket.send(b'\x52' + b''.join(data))

    def reporting(self, mode=CONTINUOUS_REPORTING, extension=EXTENSION_8BYTES):
        self.send(COMMAND_REPORTING, mode, extension)

    def light(self, on_off=True):
        self.send(COMMAND_LIGHT, b'\x10' if on_off else b'\x00')

    def status(self):
        self.send(COMMAND_REQUEST_STATUS, b'\x00')

    def calc_mass(self, raw, pos):
        cal_0kg = float(self.calibration[0][pos])
        cal_17kg = float(self.calibration[1][pos])
        cal_34kg = float(self.calibration[2][pos])

        if raw < cal_0kg:
            return 0.0
        elif raw < cal_17kg:
            if cal_17kg == cal_0kg: return None
            return 17.0 * (raw - cal_0kg) / (cal_17kg - cal_0kg)
        else:
            if cal_34kg == cal_17kg: return None
            return 17.0 + 17.0 * (raw - cal_17kg) / (cal_34kg - cal_17kg)

    def check_button(self, state):
        if state == BUTTON_DOWN_MASK:
            if not self.button_down:
                self.button_down = True
                self.on_pressed()
        elif self.button_down:
            self.button_down = False
            self.on_released()

    def get_mass(self, data):
        mass_data = {}
        raw_tr = bytes_to_int(data[0:2])
        raw_br = bytes_to_int(data[2:4])
        raw_tl = bytes_to_int(data[4:6])
        raw_bl = bytes_to_int(data[6:8])

        mass_data['top_right'] = self.calc_mass(raw_tr, TOP_RIGHT)
        mass_data['bottom_right'] = self.calc_mass(raw_br, BOTTOM_RIGHT)
        mass_data['top_left'] = self.calc_mass(raw_tl, TOP_LEFT)
        mass_data['bottom_left'] = self.calc_mass(raw_bl, BOTTOM_LEFT)
        return mass_data

    def loop(self):
        while self.running and self.receivesocket:
            try:
                data = self.receivesocket.recv(32)
                if len(data) < 2: continue
                input_type = data[1:2]

                if input_type == INPUT_STATUS:
                    battery_raw = bytes_to_int(data[6:8])
                    self.battery = min(1.0, battery_raw / 4800.0)
                    self.light_state = (bytes_to_int(data[4:5]) & LED1_MASK) == LED1_MASK
                    self.on_status()
                elif input_type == INPUT_READ_DATA:
                    if self.calibration_requested:
                        length = bytes_to_int(data[4:5]) // 16 + 1
                        payload = data[7 : 7 + length]
                        def parse_cal_chunk(d):
                            return [bytes_to_int(d[j:j+2]) for j in [0, 2, 4, 6]]

                        if length == 16:
                            self.calibration = [parse_cal_chunk(payload[0:8]), parse_cal_chunk(payload[8:16]), [10000.0] * 4]
                        elif length == 8:
                            self.calibration[2] = parse_cal_chunk(payload[0:8])
                            self.calibration_requested = False
                            self.on_calibrated()
                elif input_type == EXTENSION_8BYTES:
                    mass_data = self.get_mass(data[4:12])
                    if all(v is not None for v in mass_data.values()):
                        self.on_mass(mass_data)
                    self.check_button(bytes_to_int(data[2:4]))
            except bluetooth.btcommon.BluetoothError:
                logger.warning("Rozłączono.")
                self.close()
            except Exception as e:
                logger.error(f"Niespodziewany błąd w pętli: {e}", exc_info=True)
                self.close()

    def on_status(self):
        self.reporting()
        logger.info(f"Status: bateria: {self.battery*100:.0f}%, dioda: {'on' if self.light_state else 'off'}")
        self.light(True)

    def on_calibrated(self):
        logger.info("Waga pomyślnie skalibrowana. Rozpoczynam pomiary...")
        self.light(True)

    def on_mass(self, mass): pass
    def on_pressed(self):
        logger.info("Przycisk naciśnięty")
        self.running = False
    def on_released(self):
        logger.info("Przycisk zwolniony")

    def close(self):
        if not self.running: return
        logger.info("Zamykanie połączenia...")
        self.running = False
        if self.receivesocket: self.receivesocket.close()
        if self.controlsocket: self.controlsocket.close()
        self.receivesocket = None
        self.controlsocket = None

    def __del__(self): self.close()
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): self.close()

class WiiboardPrint(Wiiboard):
    def __init__(self, address=None):
        self.tare_value = 0.0
        self.is_tared = False
        self.reading_count = 0
        super().__init__(address)

    def on_calibrated(self):
        super().on_calibrated()
        print("Upewnij się, że waga stoi PUSTA. Automatyczne tarowanie za chwilę...")


    def on_mass(self, mass):
        total_mass = sum(mass.values())
        if not self.is_tared:
            if self.reading_count < 10:
                self.tare_value += total_mass
                self.reading_count += 1
            else:
                self.tare_value /= self.reading_count
                self.is_tared = True
                logger.info(f"Automatyczne tarowanie zakończone. Offset: {self.tare_value:.2f} kg.")
        else:
            final_weight = total_mass - self.tare_value
            if final_weight < 0: final_weight = 0.0
            print(f"Aktualna waga: {final_weight:.2f} kg      ", end='\r')

# --- Konfiguracja pliku zapisu ---
CONFIG_FILE = os.path.expanduser("~/.wiiboard_config")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return f.read().strip()
        except:
            return None
    return None

def save_config(address):
    try:
        with open(CONFIG_FILE, 'w') as f:
            f.write(address)
    except:
        pass

def trust_device(address):
    logger.info(f"Próba dodania urządzenia {address} do zaufanych (dla przycisku Power)...")
    try:
        # Wymaga bluetoothctl w systemie
        subprocess.run(["bluetoothctl", "trust", address], check=True, stdout=subprocess.DEVNULL)
        logger.info(f"Urządzenie {address} zostało dodane do zaufanych.")
        return True
    except subprocess.CalledProcessError:
        logger.warning(f"Nie udało się dodać urządzenia {address} do zaufanych (może brak uprawnień?)")
    except FileNotFoundError:
        logger.warning("Nie znaleziono polecenia bluetoothctl.")
    return False

if __name__ == '__main__':
    if '-d' in sys.argv:
        logger.setLevel(logging.DEBUG)
        sys.argv.remove('-d')

    board = WiiboardPrint()
    address = None
    connected = False

    # 1. Priorytet: Argument wiersza poleceń
    if len(sys.argv) > 1:
        address = sys.argv[1]
        logger.info(f"Łączenie z adresem podanym w argumencie: {address}")
        if board.connect(address):
            connected = True
            save_config(address)
            trust_device(address)
        else:
            logger.error("Nie udało się połączyć z podanym adresem.")
            sys.exit(1)

    # 2. Priorytet: Plik konfiguracyjny
    if not connected:
        cached_address = load_config()
        if cached_address:
            logger.info(f"Znaleziono zapamiętany adres: {cached_address}")
            print(f"\n>>> 💡 Proszę wcisnąć przycisk POWER na wadze, aby się połączyć...", end="\n\n")
            
            # Próba połączenia przez kilka sekund (np. 5 sekund)
            for i in range(1, 20):
                print(f"   Próba połączenia {i}/20...   ", end='\r')
                if board.connect(cached_address):
                    print(f"\n")
                    connected = True
                    address = cached_address
                    trust_device(address) # Upewniamy się, że jest zaufane
                    break
                time.sleep(0.5) 

            if not connected:
                logger.warning("\nNie udało się połączyć z zapamiętaną wagą. Przechodzę do skanowania...")

    # 3. Priorytet: Skanowanie
    if not connected:
        print(">>> Rozpoczynam skanowanie otoczenia (to może chwilę potrwać)...")
        try:
            wiiboards = discover()
            if not wiiboards:
                logger.error("Nie znaleziono żadnej wagi. Naciśnij czerwony przycisk synchronizacji i spróbuj ponownie.")
                sys.exit(1)
            address = wiiboards[0]
            logger.info(f"Znaleziono wagę: {address}")
            if board.connect(address):
                connected = True
                save_config(address)
                trust_device(address)
        except bluetooth.btcommon.BluetoothError as e:
            logger.error(f"Błąd Bluetooth podczas skanowania: {e}")
            logger.error("Upewnij się, że Bluetooth jest włączony i masz odpowiednie uprawnienia (uruchom jako sudo).")
            sys.exit(1)

    if connected:
        try:
            if board.controlsocket:
                logger.info("Naciśnij przycisk zasilania na wadze lub CTRL+C, aby zakończyć.")
                board.loop()
        except KeyboardInterrupt:
            print("\nProgram przerwany przez użytkownika.")
        except Exception as e:
            logger.error(f"Wystąpił nieoczekiwany błąd: {e}", exc_info=True)
        finally:
            board.close()