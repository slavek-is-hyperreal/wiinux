#! /usr/bin/env python3
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
    
    # Uruchamiamy bluetoothctl jako proces podrzędny
    proc = subprocess.Popen(
        ['bluetoothctl'], 
        stdin=subprocess.PIPE, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1 # Line buffered
    )

    def send_command(cmd):
        print(f">>> Wysłano: {cmd}")
        proc.stdin.write(cmd + "\n")
        proc.stdin.flush()

    # Włączamy skanowanie
    send_command("scan on")

    print("\n-----------------------------------------------------------------")
    print(">>> 🔴 TERAZ! Wciśnij CZERWONY PRZYCISK SYNC (pod klapką baterii).")
    print(">>> Czekam na wykrycie wagi (Nintendo RVL-WBC-01)...")
    print("-----------------------------------------------------------------\n")

    target_mac = None

    # Pętla odczytu wyjścia
    try:
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            
            # Wypisujemy linię, żeby użytkownik widział co się dzieje (opcjonalnie)
            # print(line.strip())

            # Szukamy wzorca urządzenia
            # [NEW] Device 00:22:D7:..:..:.. Nintendo RVL-WBC-01
            # [CHG] Device 00:22:D7:..:..:.. Name: Nintendo RVL-WBC-01
            if "Nintendo RVL-WBC-01" in line:
                # Wyciągnij MAC
                match = re.search(r"Device ([0-9A-F:]{17})", line, re.IGNORECASE)
                if match:
                    target_mac = match.group(1)
                    print(f"\n>>> ✅ ZNALEZIONO WAGĘ: {target_mac}")
                    break
    except KeyboardInterrupt:
        print("\nPrzerwano.")
        proc.terminate()
        return

    if target_mac:
        print(f">>> 🔗 Próba parowania z {target_mac}...")
        
        # Sekwencja parowania
        send_command(f"pair {target_mac}")
        
        # Czekamy na potwierdzenie parowania w logach (uproszczone: czekamy chwilę)
        # W idealnym świecie czytalibyśmy dalej 'proc.stdout' w poszukiwaniu "Pairing successful"
        # Spróbujmy poczekać i czytać
        start_time = time.time()
        paired = False
        while time.time() - start_time < 10:
            line = proc.stdout.readline()
            if "Pairing successful" in line:
                print(">>> 🎉 SPAROWANO POMYŚLNIE!")
                paired = True
                break
            if "Failed to pair" in line:
                print(">>> ❌ Błąd parowania. Spróbuj ponownie (resetując wagę).")
                break
        
        if not paired:
            print(">>> ⚠️ Nie otrzymano potwierdzenia 'Pairing successful', ale próbuję dalej...")

        print(f">>> 🛡️ Dodawanie do zaufanych (Trust)...")
        send_command(f"trust {target_mac}")
        time.sleep(1)

        print(f">>> 🔌 Łączenie (Connect)...")
        send_command(f"connect {target_mac}")
        time.sleep(2)
        
        # Zapisz konfigurację dla innych skryptów
        print(f">>> 💾 Zapisywanie adresu do ~/.wiiboard_config ...")
        config_path = os.path.expanduser("~/.wiiboard_config")
        # Jeśli uruchomiono przez sudo, ~ może wskazywać na /root. 
        # Spróbujmy ustalić prawdziwego użytkownika jeśli użyto sudo
        if "SUDO_USER" in os.environ:
             config_path = os.path.expanduser(f"~{os.environ['SUDO_USER']}/.wiiboard_config")
        
        try:
            with open(config_path, 'w') as f:
                f.write(target_mac)
            print(">>> Zapisano.")
        except Exception as e:
            print(f">>> Błąd zapisu konfigu: {e}")

        print("\n>>> ✅ Gotowe! Teraz możesz ustawić wagę i używać skryptów.")
        print(">>> Aby połączyć się w przyszłości, użyj: sudo python wiiboard_server.py i przycisk POWER.")

    send_command("scan off")
    send_command("quit")
    proc.terminate()

if __name__ == '__main__':
    run_pairing()
