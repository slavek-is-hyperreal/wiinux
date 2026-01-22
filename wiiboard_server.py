#! /usr/bin/env python3
""" Wiiboard "Server" Mode (Hijack Strategy) 
    1. Wait for board to connect to Linux (BlueZ/Kernel).
    2. Detect connection via sysfs.
    3. Unbind kernel driver (hid_wiimote) to free the device.
    4. Connect manually using L2CAP sockets.
"""
import wiiboard
import bluetooth
import sys
import logging
import os
import time
import subprocess
import glob

# Logger setup
logger = logging.getLogger("wiiboard")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('[%(asctime)s][%(levelname)s] %(message)s'))
logger.addHandler(handler)

# Config path
CONFIG_FILE = os.path.expanduser("~/.wiiboard_config")
if "SUDO_USER" in os.environ:
    CONFIG_FILE = os.path.expanduser(f"~{os.environ['SUDO_USER']}/.wiiboard_config")

def unbind_kernel_driver(target_mac):
    """
    Scans /sys/bus/hid/drivers/wiimote/ for the device and unbinds it.
    """
    driver_path = "/sys/bus/hid/drivers/wiimote"
    if not os.path.exists(driver_path):
        return False

    # Look for device IDs like 0005:057E:0306.*
    # We can't easily check MAC here without checking uevent, but usually there's only one.
    devices = glob.glob(os.path.join(driver_path, "0005:057E:0306.*"))
    
    for dev in devices:
        dev_name = os.path.basename(dev)
        # Optional: check uevent for MAC if multiple boards (skipped for simplicity)
        logger.info(f"Wykryto urządzenie sterowane przez kernel: {dev_name}")
        
        try:
            logger.info(f"Odłączanie sterownika systemowego (unbind)...")
            with open(os.path.join(driver_path, "unbind"), "w") as f:
                f.write(dev_name)
            logger.info("Sterownik odłączony. Zasób zwolniony.")
            return True
        except PermissionError:
            logger.error("Brak uprawnień do unbind! Uruchom jako root (sudo).")
        except Exception as e:
            logger.error(f"Błąd podczas unbind: {e}")
            
    return False

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return f.read().strip()
    return None

def main():
    if os.geteuid() != 0:
        logger.warning(">>> ⚠️  Uruchom ten skrypt jako root (sudo), aby móc przejąć kontrolę nad wagą!")
        # Nie wychodzimy, bo może user ma udev rules, ale zazwyczaj unbind wymaga root.

    address = load_config()
    if not address:
        logger.error("Brak zapamiętanego adresu w ~/.wiiboard_config. Uruchom najpierw pair_wiiboard.py!")
        sys.exit(1)

    print(f">>> 🎯 Cel: {address}")
    print(f">>> 🔌 Wciśnij przycisk POWER na wadze teraz.")
    print(f">>> (Czekam na połączenie z systemem, aby je przejąć...)")

    board = wiiboard.WiiboardPrint()
    
    # Pętla oczekiwania na system
    hijacked = False
    
    # 1. Czekamy aż system zobaczy wagę (i załaduje sterownik wiimote)
    #    Lub aż waga będzie dostępna do połączenia.
    while True:
        # Sprawdź czy jest w sterownikach kernela
        if unbind_kernel_driver(address):
            hijacked = True
            logger.info("Przejęto urządzenie. Czekam chwilę na stabilizację...")
            time.sleep(1.0) # Daj czas na zwolnienie zasobów
            break
        
        # Opcjonalnie: Możemy próbować łączyć się bezpośrednio, jeśli kernel jeszcze nie złapał?
        # Ale strategia POWER button polega na tym, że waga inicjuje.
        print("Waiting for device... (POWER button)", end='\r')
        time.sleep(0.5)

    # 2. Łączymy się "na gotowe"
    print("\n>>> 🚀 Próba nawiązania własnego połączenia...")
    connected = False
    for i in range(5):
        try:
            if board.connect(address):
                connected = True
                break
        except bluetooth.btcommon.BluetoothError as e:
            logger.warning(f"Błąd połączenia ({i+1}/5): {e}")
            time.sleep(1)
    
    if connected:
        logger.info(">>> ✅ SUKCES! Połączono w trybie Hijack.")
        
        # UI Manualne tarowanie/Start
        print("\n-----------------------------------------------------------------")
        print(">>> Połóż wagę na płaskiej powierzchni.")
        print(">>> Naciśnij klawisz 't' (tarowanie) i Enter, aby rozpocząć.")
        print("-----------------------------------------------------------------")
        
        # Mała pętla czekająca na 't' (lub dowolny klawisz, ale trzymajmy standard)
        while True:
            try:
                # board.loop() jest blokujący, więc musimy to zrobić przed loopem
                # Ale board.connect() już nawiązał połączenie i czeka.
                # W oryginale user klikał 't' wtedy.
                key = input()
                if key.lower() == 't':
                    break
            except KeyboardInterrupt:
                sys.exit(0)
                
        # Uruchamiamy pętlę zdarzeń
        try:
            logger.info("Start pętli odczytu...")
            board.loop()
        except KeyboardInterrupt:
            print("\nZakończono.")
        finally:
            board.close()
    else:
        logger.error(">>> ❌ Nie udało się połączyć po odłączeniu sterownika.")

if __name__ == '__main__':
    main()
