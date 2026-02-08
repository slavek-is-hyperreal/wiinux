#!/usr/bin/env python3
"""
Wii Accessories Library (v1.8) - Native Linux Version
Supports Wii Balance Board and Wiimote (IR Camera + Pulse Monitor + CSV RLE).

Improvements:
- Coordinate-Locked Decoding (ignore jumping IR points).
- Stability Factor (SF) metric - identifies "Real Signal" vs "Movement Noise".
- Real-time Coordinate Monitor (Online Monitor).
"""

import time
import logging
import evdev
from evdev import ecodes, ff
import glob
import select
import threading
import sys
import os
import argparse
import math

# Logger setup
logging.basicConfig(level=logging.INFO, format='[%(asctime)s][%(levelname)s] %(message)s')
logger = logging.getLogger("wii_accessories")

# --- Utility: Morse Decoder with Integrator ---

class MorseDecoder:
    def __init__(self, bit_duration=0.1, callback=None):
        self.bit_duration = bit_duration
        self.callback = callback
        self.buffer = []
        self.lock = threading.Lock()
        
        self.last_update_time = time.time()
        self.accumulated_active_time = 0.0
        self.current_bit_progress = 0.0
        self.is_currently_active = False

    def feed(self, detected):
        now = time.time()
        dt = now - self.last_update_time
        self.last_update_time = now

        if self.is_currently_active:
            self.accumulated_active_time += dt
        
        self.current_bit_progress += dt
        self.is_currently_active = detected

        if self.current_bit_progress >= self.bit_duration:
            # Sensitive threshold (5%) to catch fast remotes
            bit = 1 if (self.accumulated_active_time / self.current_bit_progress) > 0.05 else 0
            
            with self.lock:
                self.buffer.append(bit)
                self._check_buffer()
            
            self.current_bit_progress = 0
            self.accumulated_active_time = 0

    def _check_buffer(self):
        if len(self.buffer) > 0:
            stream = "".join(map(str, self.buffer[-20:]))
            sys.stdout.write(f"\r[VLC Trace: ...{stream}]    ")
            sys.stdout.flush()

        if len(self.buffer) >= 10:
            while len(self.buffer) >= 10:
                if self.buffer[0] == 1 and self.buffer[9] == 0:
                    data_bits = self.buffer[1:9]
                    val = 0
                    for i, b in enumerate(data_bits):
                        val |= (b << (7 - i))
                    if self.callback: self.callback(val)
                    self.buffer = self.buffer[10:]
                    break
                else:
                    self.buffer.pop(0)

# --- Utility: Signal Stability Monitor ---

class StabilityMonitor:
    """
    Tracks if coordinates are stable or jumping wildly.
    Jumping points = Noise/Movement. Stable points = Signal.
    """
    def __init__(self, radius=50):
        self.radius = radius
        self.anchor_point = None
        self.last_seen_time = 0
        self.stability_factor = 0.0 # 0.0 to 1.0
        self._history = [] # Bool: was it stable?

    def feed(self, p):
        now = time.time()
        is_stable = False
        
        if p is None:
            if now - self.last_seen_time > 0.5:
                self.anchor_point = None
        else:
            if self.anchor_point is None:
                self.anchor_point = p
                is_stable = True
            else:
                dist = math.sqrt((p[0]-self.anchor_point[0])**2 + (p[1]-self.anchor_point[1])**2)
                if dist < self.radius:
                    is_stable = True
                else:
                    # Point jumped! Update anchor but mark as jitter
                    self.anchor_point = p
            self.last_seen_time = now

        self._history.append(is_stable)
        if len(self._history) > 100: self._history.pop(0)
        self.stability_factor = sum(self._history) / len(self._history)
        return is_stable

# --- Utility: IR Pulse Monitor ---

class PulseMonitor:
    def __init__(self):
        self.last_state = False
        self.last_change_time = time.time()
        self.is_valid = False # Only print if SF is high

    def feed(self, detected, is_stable):
        now = time.time()
        trigger = detected and is_stable
        if trigger != self.last_state:
            duration_ms = (now - self.last_change_time) * 1000
            label = "HOT " if self.last_state else "COLD"
            if duration_ms > 2: 
                # Print only pulses, avoid status line mess
                sys.stdout.write(f"\n[Pulse: {label} {duration_ms:4.0f}ms]\n")
            self.last_state = trigger
            self.last_change_time = now

# --- Wii Remote (IR Eye) Native ---

class WiiEyeNative:
    def __init__(self, bit_duration=0.1, raw_mode=False):
        self.dev_buttons = None
        self.dev_ir = None
        self.running = False
        self.raw_mode = raw_mode
        self.points = [None] * 4 
        self.points_persistence = [0.0] * 4 # Timestamps for clearing
        self.button_b = False
        
        self.decoder = MorseDecoder(bit_duration=bit_duration, callback=self._on_id_found)
        self.stability = StabilityMonitor(radius=60)
        self.pulsemon = PulseMonitor()
        
        self.on_id_detected = None
        self._ff_effect_id = None
        self._rumble_active = False
        self._rumble_stop_time = 0
        # Recording features
        self.recording_buffer = []
        self.raw_event_buffer = [] 
        self.is_recording = False
        self.last_idle_start = 0

    def connect(self):
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        for dev in devices:
            if "Nintendo Wii Remote" in dev.name:
                if "IR" in dev.name: self.dev_ir = dev
                elif "Accelerometer" not in dev.name: self.dev_buttons = dev
        
        if not self.dev_buttons or not self.dev_ir: return False
        try: self._setup_rumble()
        except Exception as e: logger.warning(f"Rumble init failed: {e}")
        self.running = True
        return True

    def _setup_rumble(self):
        rumble = ff.Rumble(strong_magnitude=0xffff, weak_magnitude=0xffff)
        effect = ff.Effect(
            type=ecodes.FF_RUMBLE, id=-1, direction=0,
            trigger=ff.Trigger(0, 0),
            replay=ff.Replay(duration=150, delay=0),
            u=ff.EffectType(ff_rumble_effect=rumble)
        )
        self._ff_effect_id = self.dev_buttons.upload_effect(effect)

    def pulse_rumble(self):
        if self._ff_effect_id is not None:
            if not self._rumble_active:
                try:
                    self.dev_buttons.write(ecodes.EV_FF, self._ff_effect_id, 1)
                    self._rumble_active = True
                    self._rumble_stop_time = time.time() + 0.2
                except: pass

    def _on_id_found(self, val):
        # We only log DECODED if stability is decent
        if self.stability.stability_factor > 0.1:
            logger.info(f"!!! DECODED: 0x{val:02X} (SF:{self.stability.stability_factor:.2f}) !!!")
            if self.on_id_detected: self.on_id_detected(val)
            self.pulse_rumble()

    def update(self):
        if self._rumble_active and time.time() > self._rumble_stop_time:
            if self._ff_effect_id is not None:
                try: self.dev_buttons.write(ecodes.EV_FF, self._ff_effect_id, 0)
                except: pass
            self._rumble_active = False

        devices = {self.dev_buttons.fd: self.dev_buttons, self.dev_ir.fd: self.dev_ir}
        r, w, x = select.select(devices.keys(), [], [], 0.0)
        for fd in r:
            try:
                for event in devices[fd].read():
                    if fd == self.dev_buttons.fd:
                        if event.type == ecodes.EV_KEY and event.code == ecodes.BTN_EAST:
                            new_val = bool(event.value)
                            if new_val and not self.button_b:
                                self.is_recording = True
                                self.recording_buffer = []
                                self.raw_event_buffer = []
                                self.last_idle_start = 0
                                logger.info("REC Start")
                            elif not new_val and self.button_b:
                                self.is_recording = False
                                self._save_to_csv()
                            self.button_b = new_val
                    elif fd == self.dev_ir.fd:
                        if (self.is_recording or self.raw_mode) and event.type == ecodes.EV_ABS:
                            self.raw_event_buffer.append([event.timestamp(), event.code, event.value])
                            if self.raw_mode:
                                sys.stdout.write(f"\n[RAW IR] t:{event.timestamp():.3f} code:{event.code:2d} val:{event.value:4d}")
                                sys.stdout.flush()
                        
                        if event.type == ecodes.EV_ABS and 16 <= event.code <= 23:
                            idx, axis = (event.code - 16) // 2, (event.code - 16) % 2
                            cur = list(self.points[idx] or [1023, 1023])
                            cur[axis] = event.value
                            if cur == [1023, 1023]:
                                self.points[idx] = None
                            else:
                                if self.points[idx] is None:
                                    # First burst in this cycle
                                    if self.raw_mode:
                                        sys.stdout.write(f"\n[IR BURST] P{idx}:({cur[0]:4d},{cur[1]:4d})")
                                        sys.stdout.flush()
                                self.points[idx] = cur
                                self.points_persistence[idx] = time.time() + 0.15 # 150ms visibility
            except: pass
        
        # Persistence Logic: Show points even after they flicker out
        now = time.time()
        display_points = []
        for i in range(4):
            if self.points[i] and now > self.points_persistence[i]:
                self.points[i] = None
            display_points.append(self.points[i])

        p0 = display_points[0]
        is_stable = self.stability.feed(p0)
        
        if self.button_b:
            active = p0 is not None
            # Feed decoder ONLY if point is relatively stable
            self.decoder.feed(active and is_stable)
            self.pulsemon.feed(active, is_stable)

        # RLE Recording
        if self.is_recording:
            now = time.time()
            if any(p is not None for p in self.points):
                row = [now, 0]
                for p in self.points: row.extend(p if p else [None, None])
                self.recording_buffer.append(row)
                self.last_idle_start = 0
            else:
                if self.last_idle_start == 0:
                    self.last_idle_start = now
                else:
                    dur = (now - self.last_idle_start) * 1000
                    if self.recording_buffer and (self.recording_buffer[-1][1] > 0 or all(x is None for x in self.recording_buffer[-1][2:])):
                        self.recording_buffer[-1][1] = dur
                    else:
                        row = [now, dur] + [None]*8
                        self.recording_buffer.append(row)

    def _save_to_csv(self):
        if not self.recording_buffer and not self.raw_event_buffer: return
        ts = int(time.time())
        import csv
        if self.recording_buffer:
            fn = f"wiieye_status_{ts}.csv"
            with open(fn, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['ts', 'dur', 'p0x', 'p0y', 'p1x', 'p1y', 'p2x', 'p2y', 'p3x', 'p3y'])
                writer.writerows(self.recording_buffer)
            logger.info(f"Saved: {fn}")
        if self.raw_event_buffer:
            fn = f"wiieye_raw_{ts}.csv"
            with open(fn, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['ts', 'code', 'val'])
                writer.writerows(self.raw_event_buffer)
            logger.info(f"Saved RAW: {fn}")

# --- Wii Balance Board Native ---

class WiiboardNative:
    def __init__(self):
        self.device = None
        self.code_to_index = {16: 0, 17: 1, 18: 2, 19: 3}
        self.raw_values = [0] * 4
        self.calib = [] 
        self.tare_offset = 0.0
        self.weight = 0.0

    def connect(self):
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        for dev in devices:
            if "Nintendo" in dev.name and "Balance Board" in dev.name:
                self.device = dev
                if self.load_calibration():
                    self._auto_tare_sequence()
                    return True
        return False

    def load_calibration(self):
        paths = glob.glob("/sys/bus/hid/drivers/wiimote/*/bboard_calib")
        if not paths: return False
        try:
            with open(paths[0], 'r') as f:
                parts = f.read().strip().split(':')
                vals = [int(p, 16) for p in parts]
                self.calib = []
                for s in range(4): self.calib.append([vals[s], vals[s + 4], vals[s + 8]])
                return True
        except: return False

    def _auto_tare_sequence(self):
        start = time.time()
        while True:
            self.update()
            if time.time() - start > 0.5: break
        self.tare()

    def tare(self):
        self.tare_offset = sum([self.get_weight_for_sensor(i, self.raw_values[i]) for i in range(4)])

    def get_weight_for_sensor(self, index, raw_input):
        c0, c17, c34 = self.calib[index]
        range1, range2 = c17 - c0, c34 - c17
        if range1 <= 0: range1 = 1700
        if range2 <= 0: range2 = 1700
        if raw_input < range1: return 17.0 * raw_input / range1
        else: return 17.0 + 17.0 * (raw_input - range1) / range2

    def update(self):
        if not self.device: return
        while True:
            r, w, x = select.select([self.device.fd], [], [], 0.0)
            if not r: break
            try:
                for event in self.device.read():
                    if event.type == ecodes.EV_ABS and event.code in self.code_to_index:
                        self.raw_values[self.code_to_index[event.code]] = event.value
            except: break
        self.weight = sum([self.get_weight_for_sensor(i, self.raw_values[i]) for i in range(4)]) - self.tare_offset

# --- Interactive Diagnostic ---

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bit-duration", type=float, default=0.1)
    parser.add_argument("--raw", action="store_true", help="Stream absolute raw events")
    args, unknown = parser.parse_known_args()

    print(f"\n--- Wii Accessories Diagnostic v1.9 {'[RAW MODE]' if args.raw else ''} ---")
    print("1. Wii Balance Board")
    print("2. Wiimote IR (Stability + Monitor)")
    choice = input("Choice (1/2): ")

    if choice == '1':
        board = WiiboardNative()
        if board.connect():
            try:
                while True: board.update(); print(f"\rWeight: {board.weight:6.2f} kg", end=""); time.sleep(0.01)
            except KeyboardInterrupt: pass
    elif choice == '2':
        eye = WiiEyeNative(bit_duration=args.bit_duration, raw_mode=args.raw)
        if eye.connect():
            print(f"B-Hold mode. Bit: {args.bit_duration*1000:.0f}ms. CTRL+C to quit.")
            if args.raw: print("RAW STREAM ACTIVE. Every kernel event will be printed.")
            try:
                last_ui = 0
                while True:
                    eye.update()
                    if time.time() - last_ui > 0.05:
                        p0 = eye.points[0]
                        p_str = f"P0:({p0[0]:4d},{p0[1]:4d})" if p0 else "P0:----      "
                        sf = eye.stability.stability_factor
                        status = "FIXED" if sf > 0.8 else "JITTER" if sf > 0.2 else "LOST  "
                        if not eye.button_b:
                            sys.stdout.write(f"\rMonitor: {p_str} | Quality: {status} (SF:{sf:.2f})    ")
                            sys.stdout.flush()
                        last_ui = time.time()
                    time.sleep(0.005)
            except KeyboardInterrupt: pass
    else: print("Error.")

if __name__ == "__main__":
    main()
