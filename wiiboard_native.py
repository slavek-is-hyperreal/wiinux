#! /usr/bin/env python3
""" Wiiboard Native Library (Kernel/Evdev)
    
    This library allows easy integration of the Wii Balance Board 
    into Python games and applications on Linux.
    It uses the native 'hid-wiimote' kernel driver and 'evdev'.

    Usage:
        board = WiiboardNative()
        if board.connect():
            while True:
                # Call this in your game loop
                board.update() 
                print(board.weight)
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
        self.code_to_index = {16: 0, 17: 1, 18: 2, 19: 3}
        self.raw_values = [0] * 4
        self.calib = [] 
        self.tare_offset = 0.0
        self.weight = 0.0
        self.last_event_time = 0

    def connect(self):
        """ Attempts to find and connect to the Wii Balance Board.
            Returns True if successful, False otherwise. 
        """
        logger.info("Szukanie wagi w systemie (evdev)...")
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        
        for dev in devices:
            if "Nintendo" in dev.name and "Balance Board" in dev.name:
                logger.info(f"Znaleziono wagę: {dev.name} ({dev.path})")
                self.device = dev
                
                if self.load_calibration():
                    self._auto_tare_sequence()
                    return True
                else:
                    logger.warning("Nie udało się załadować danych kalibracyjnych.")
                    # Fallback to dummy? Or maybe just try anyway.
                    # Let's fail for now to be safe, or use dummy.
                    self.calib = [[0, 1000, 2000] for _ in range(4)]
                    return True
        return False

    def load_calibration(self):
        paths = glob.glob("/sys/bus/hid/drivers/wiimote/*/bboard_calib")
        if not paths:
            return False
        
        calib_file = paths[0]
        try:
            with open(calib_file, 'r') as f:
                content = f.read().strip()
                parts = content.split(':')
                if len(parts) != 12:
                    return False
                
                vals = [int(p, 16) for p in parts]
                
                # Format: 3 blocks of 4 values (0kg, 17kg, 34kg)
                self.calib = []
                for s in range(4): 
                    s_vals = [vals[s], vals[s + 4], vals[s + 8]]
                    self.calib.append(s_vals)
                
                logger.info(f"Załadowano kalibrację: {self.calib}")
                return True
        except Exception as e:
            logger.error(f"Błąd czytania kalibracji: {e}")
            return False

    def _auto_tare_sequence(self):
        logger.info("Stabilizacja i Auto-Tarowanie...")
        # Read for a short time to clear buffer and get latest values
        start = time.time()
        while time.time() - start < 0.5:
             self.update()
        
        self.tare()
        logger.info(f"Auto-Tarowanie zakończone. Offset: {self.tare_offset:.2f} kg")

    def tare(self):
        """ Sets the current weight as the zero point. """
        self.tare_offset = self.calc_total_weight_raw()

    def get_weight_for_sensor(self, index, raw_input):
        c0, c17, c34 = self.calib[index]
        range1 = c17 - c0
        range2 = c34 - c17
        if range1 == 0: range1 = 1700
        if range2 == 0: range2 = 1700
        
        if raw_input < range1:
            return 17.0 * raw_input / range1
        else:
            return 17.0 + 17.0 * (raw_input - range1) / range2

    def calc_total_weight_raw(self):
        """ internal calculation without tare """
        total = 0.0
        for i in range(4):
            total += self.get_weight_for_sensor(i, self.raw_values[i])
        return total

    def update(self):
        """ Call this method in your main loop. 
            It reads all pending events non-blocking. 
        """
        if not self.device:
            return

        # Read all available events
        while True:
            r, w, x = select.select([self.device.fd], [], [], 0.0)
            if not r:
                break
                
            try:
                for event in self.device.read():
                    if event.type == evdev.ecodes.EV_ABS:
                        if event.code in self.code_to_index:
                            idx = self.code_to_index[event.code]
                            self.raw_values[idx] = event.value
                            self.last_event_time = time.time()
            except BlockingIOError:
                break
            except Exception as e:
                logger.error(f"Błąd odczytu: {e}")
                break
        
        # Recalculate weight
        raw_w = self.calc_total_weight_raw()
        self.weight = raw_w - self.tare_offset


# -------------------------------------------------------------
# Example usage (CLI)
# -------------------------------------------------------------
if __name__ == '__main__':
    if not os.access('/dev/input/event0', os.R_OK):
         logger.warning("Brak uprawnień. Uruchom przez sudo!")
    
    board = WiiboardNative()
    
    if board.connect():
        print("\n-----------------------------------------------------------------")
        print(">>> ✅ Waga połączona! Uruchamiam tryb demo.")
        print(">>> Naciśnij 't' aby wytarować.")
        print(">>> Ctrl+C aby zakończyć.")
        print("-----------------------------------------------------------------")
        
        try:
            while True:
                # 1. Update board state
                board.update()
                
                # 2. Handle user input (CLI specific)
                if select.select([sys.stdin], [], [], 0.0)[0]:
                    line = sys.stdin.readline()
                    if 't' in line:
                        board.tare()
                        print(f"\n>>> ⚖️  Wytarowano.")

                # 3. Render
                if time.time() * 10 % 1 < 0.1: # Print ~10Hz
                    rv = board.raw_values
                    sys.stdout.write(f"\rWaga: {board.weight:6.2f} kg  [Raw: {rv[0]} {rv[1]} {rv[2]} {rv[3]}]")
                    sys.stdout.flush()
                
                time.sleep(0.01)
                
        except KeyboardInterrupt:
            print("\nZakończono.")
    else:
        logger.error("Nie znaleziono wagi. Upewnij się, że jest włączona (Power Button) i sparowana.")
