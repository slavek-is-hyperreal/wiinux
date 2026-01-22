#! /usr/bin/env python3
""" Wiiboard Native Mode (Kernel/Evdev)
    Reads "bboard_calib" from sysfs to perform factory-grade calibration.
    Then reads /dev/input/event* to calculate real weight in KG.
"""
import evdev
import time
import sys
import os
import glob
import select
import logging

# Logger setup
logging.basicConfig(level=logging.INFO, format='[%(asctime)s][%(levelname)s] %(message)s')
logger = logging.getLogger("wiiboard_native")

class WiiboardNative:
    def __init__(self):
        self.device = None
        # Corners mapping (Evdev Code -> Internal Index 0..3)
        # 16: TopRight, 17: BottomRight, 18: TopLeft, 19: BottomLeft
        # Indices in calib: 0=TR, 1=BR, 2=TL, 3=BL
        self.code_to_index = {
            16: 0, 
            17: 1, 
            18: 2, 
            19: 3
        }
        self.raw_values = [0] * 4
        
        # Calibration: 3 points (0kg, 17kg, 34kg) for 4 sensors
        # Format: self.calib[sensor_index][point_index]
        self.calib = [] 
        self.tare_offset = 0.0

    def find_device_and_calib(self):
        logger.info("Szukanie wagi w systemie (evdev)...")
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        
        for dev in devices:
            if "Nintendo" in dev.name and "Balance Board" in dev.name:
                logger.info(f"Znaleziono wagę: {dev.name} ({dev.path})")
                self.device = dev
                
                # Try to find calibration data map in sysfs
                # Device path: /sys/class/input/eventX/device/device/driver/...
                # But easiest is to scan /sys/bus/hid/drivers/wiimote/...
                if self.load_calibration():
                    return True
                else:
                    logger.warning("Nie udało się załadować danych kalibracyjnych. Używam domyślnych.")
                    # Default dummy calib if fails
                    self.calib = [[0, 1000, 2000] for _ in range(4)]
                    return True
        return False

    def load_calibration(self):
        # Scan for bboard_calib
        paths = glob.glob("/sys/bus/hid/drivers/wiimote/*/bboard_calib")
        if not paths:
            return False
        
        calib_file = paths[0]
        try:
            with open(calib_file, 'r') as f:
                content = f.read().strip()
                # Format: 0cc3:3f50:4e29:0656:1397:45f4:54f6:0d3c:1a68:4c9f:5bc6:1426
                parts = content.split(':')
                if len(parts) != 12:
                    return False
                
                vals = [int(p, 16) for p in parts]
                
                # CORRECT MAPPING based on analysis:
                # The file contains 3 blocks of 4 values each.
                # Block 1 (Idx 0-3): 0kg for sensors 0,1,2,3
                # Block 2 (Idx 4-7): 17kg for sensors 0,1,2,3
                # Block 3 (Idx 8-11): 34kg for sensors 0,1,2,3
                
                # self.calib[sensor_index] = [0kg, 17kg, 34kg]
                self.calib = []
                for s in range(4): # For each sensor 0..3
                    s_vals = [
                        vals[s],      # 0kg
                        vals[s + 4],  # 17kg
                        vals[s + 8]   # 34kg
                    ]
                    self.calib.append(s_vals)
                
                logger.info(f"Załadowano kalibrację: {self.calib}")
                return True
        except Exception as e:
            logger.error(f"Błąd czytania kalibracji: {e}")
            return False

    def get_weight_for_sensor(self, index, raw_input):
        # The evdev driver (hid-wiimote) seems to report values relative to 0kg (deltas),
        # not the absolute values found in bboard_calib.
        # So 'raw_input' is essentially (Current_Raw - c0).
        
        c0, c17, c34 = self.calib[index]
        
        # Calculate resolution (units per 17kg)
        range1 = c17 - c0
        range2 = c34 - c17
        
        # Avoid division by zero
        if range1 == 0: range1 = 1700
        if range2 == 0: range2 = 1700
        
        # Interpolation
        if raw_input < range1:
            return 17.0 * raw_input / range1
        else:
            return 17.0 + 17.0 * (raw_input - range1) / range2

    def calc_total_weight(self):
        total = 0.0
        for i in range(4):
            total += self.get_weight_for_sensor(i, self.raw_values[i])
        return total

    def loop(self):
        if not self.device:
            return

        print("\n-----------------------------------------------------------------")
        print(">>> ✅ Waga połączona natywnie (Sterownik Kernel + Evdev)!")
        print(">>> Używam fabrycznej kalibracji z EEPROM.")
        print(">>> Wykonuję AUTO-TAROWANIE (Zero) - nie stawaj jeszcze na wadze!")
        print("-----------------------------------------------------------------")
        
        # Give it a second to stabilize readings
        logger.info("Stabilizacja odczytów...")
        start_wait = time.time()
        # Read some events to flush and get current state
        while time.time() - start_wait < 1.0:
             r, w, x = select.select([self.device.fd], [], [], 0.1)
             if r:
                 for event in self.device.read():
                     if event.type == evdev.ecodes.EV_ABS:
                         if event.code in self.code_to_index:
                             idx = self.code_to_index[event.code]
                             self.raw_values[idx] = event.value

        # Auto-Tare
        self.tare_offset = self.calc_total_weight()
        print(f">>> ⚖️  AUTO-TAROWANIE ZAKOŃCZONE. Offset: {self.tare_offset:.2f} kg")
        print(">>> 🟢 GOTOWE! Możesz wejść na wagę.")
        print(">>> (Naciśnij 't' aby wytarować ponownie ręcznie)")

        last_print = time.time()
        
        while True:
            r, w, x = select.select([self.device.fd, sys.stdin], [], [])
            
            for fd in r:
                if fd == self.device.fd:
                    for event in self.device.read():
                        if event.type == evdev.ecodes.EV_ABS:
                            if event.code in self.code_to_index:
                                idx = self.code_to_index[event.code]
                                self.raw_values[idx] = event.value
                
                if fd == sys.stdin:
                    line = sys.stdin.readline()
                    if 't' in line:
                        weight = self.calc_total_weight()
                        self.tare_offset = weight
                        print(f"\n>>> ⚖️  Wytarowano. Offset: {self.tare_offset:.2f} kg")

            if time.time() - last_print > 0.1:
                weight = self.calc_total_weight()
                final_weight = weight - self.tare_offset
                # Display raw values for debugging and final KG
                rv = self.raw_values
                sys.stdout.write(f"\rWaga: {final_weight:6.2f} kg  [Raw: {rv[0]:4} {rv[1]:4} {rv[2]:4} {rv[3]:4}]")
                sys.stdout.flush()
                last_print = time.time()

if __name__ == '__main__':
    if not os.access('/dev/input/event0', os.R_OK):
         logger.warning("Brak uprawnień. Uruchom przez sudo!")
    
    native = WiiboardNative()
    if native.find_device_and_calib():
        try:
            native.loop()
        except KeyboardInterrupt:
            print("\nZakończono.")
    else:
        logger.error("Nie znaleziono wagi.")
