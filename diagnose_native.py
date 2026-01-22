#! /usr/bin/env python3
import evdev
import sys
import os
import time
import glob

def explore_sysfs(device_path):
    # device_path example: /sys/devices/pci.../input/input34/event16
    # We want to go up to the HID device directory
    print(f"   Sysfs Path: {device_path}")
    
    # Próbujemy znaleźć folder 'extension' w górę drzewa
    current = device_path
    found = False
    for _ in range(5):
        current = os.path.dirname(current)
        # Szukamy czegoś co wygląda jak katalog sterownika wiimote
        # Zazwyczaj ma plik "uevent" i podkatalog "extension" (dla Balance Board)
        ext_path = os.path.join(current, "extension")
        if os.path.exists(ext_path):
            print(f"   >>> ZNALEZIONO KATALOG EXTENSION: {ext_path}")
            found = True
            # Wylistujmy co tam jest
            try:
                files = os.listdir(ext_path)
                print(f"   Zawartość extension: {files}")
            except:
                pass
            break
            
    if not found:
        print("   (Nie znaleziono katalogu 'extension' w pobliżu)")

def main():
    print(">>> 🔍 Skanowanie urządzeń wejściowych (evdev)...")
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    
    wii_board = None
    
    for dev in devices:
        print(f"\nUrządzenie: {dev.name}")
        print(f"   Ścieżka: {dev.path}")
        print(f"   Phys: {dev.phys}")
        
        if "Nintendo" in dev.name and "Balance Board" in dev.name:
            wii_board = dev
            print("   >>> ✅ TO JEST WAGA!")
            
            # Wypisz Capabilities
            print("   Obsługiwane zdarzenia:")
            caps = dev.capabilities(verbose=True)
            for type_code, codes in caps.items():
                print(f"      {type_code}: {codes}")
                
            # Spróbujmy znaleźć sysfs
            # evdev nie daje prosto ścieżki sysfs, ale możemy zgadywać po numerze eventX
            # /sys/class/input/eventX/device/
            sys_path = f"/sys/class/input/{os.path.basename(dev.path)}/device"
            # Rozwiń symlink
            if os.path.exists(sys_path):
                real_path = os.path.realpath(sys_path)
                explore_sysfs(real_path)

    if wii_board:
        print("\n>>> 🟢 Test odczytu (naciśnij na wagę!). Czekam 5 sekund...")
        end_time = time.time() + 5
        try:
            for event in wii_board.read_loop():
                if time.time() > end_time:
                    break
                if event.type == evdev.ecodes.EV_ABS:
                    print(f"   EVENT: {evdev.ecodes.ABS[event.code]} = {event.value}")
        except Exception as e:
            print(f"   Błąd odczytu: {e}")
    else:
        print("\n>>> ❌ Nie znaleziono wagi. Upewnij się, że jest połączona (dioda świeci ciągle).")

if __name__ == '__main__':
    main()
