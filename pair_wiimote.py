#!/usr/bin/env python3
import subprocess
import time
import re
import sys
import os

def run_pairing():
    if os.geteuid() != 0:
        print(">>> ⚠️  Uruchom ten skrypt jako root (sudo), aby bluetoothctl działał poprawnie.")
        sys.exit(1)

    print(">>> 🟢 Uruchamiam bluetoothctl...")
    
    proc = subprocess.Popen(
        ['bluetoothctl'], 
        stdin=subprocess.PIPE, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    def send_command(cmd):
        proc.stdin.write(cmd + "\n")
        proc.stdin.flush()

    send_command("power on")
    time.sleep(0.5)
    send_command("agent on")
    time.sleep(0.5)
    send_command("scan on")

    print("\n-----------------------------------------------------------------")
    print(">>> 🔴 TERAZ! Wciśnij CZERWONY PRZYCISK SYNC (pod klapką baterii).")
    print(">>> Czekam na wykrycie Wiimote (Nintendo RVL-CNT-01)...")
    print("-----------------------------------------------------------------\n")

    target_mac = None

    try:
        start_scan = time.time()
        while time.time() - start_scan < 30: # 30 seconds timeout
            line = proc.stdout.readline()
            if not line: break
            
            # Nintendo RVL-CNT-01 is Wiimote, RVL-WBC-01 is Balance Board
            if "Nintendo RVL-CNT-01" in line or "Nintendo RVL-WBC-01" in line:
                match = re.search(r"Device ([0-9A-F:]{17})", line, re.IGNORECASE)
                if match:
                    target_mac = match.group(1)
                    print(f"\n>>> ✅ ZNALEZIONO URZĄDZENIE: {target_mac}")
                    break
    except KeyboardInterrupt:
        print("\nPrzerwano.")
        proc.terminate()
        return

    if target_mac:
        print(f">>> 🔗 Próba parowania z {target_mac}...")
        send_command(f"pair {target_mac}")
        
        # Wiimote pairing often requires no PIN or special handling in bluez
        time.sleep(5) 
        
        print(f">>> 🛡️ Dodawanie do zaufanych (Trust)...")
        send_command(f"trust {target_mac}")
        time.sleep(1)

        print(f">>> 🔌 Łączenie (Connect)...")
        send_command(f"connect {target_mac}")
        time.sleep(2)
        
        print(f"\n>>> ✅ Gotowe! MAC: {target_mac}")
        print(f">>> Teraz możesz uruchomić: sudo ./venv/bin/python wiinux_eye.py {target_mac} --test")

    else:
        print(">>> ❌ Nie znaleziono urządzenia. Upewnij się, że diody na Wiimote migają po wciśnięciu SYNC.")

    send_command("scan off")
    send_command("quit")
    proc.terminate()

if __name__ == '__main__':
    run_pairing()
