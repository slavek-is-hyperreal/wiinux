#! /usr/bin/env python3
import time
import os
import sys

# Import our new library
try:
    from wiiboard_native import WiiboardNative
except ImportError:
    print("Błąd: Nie znaleziono wiiboard_native.py w tym katalogu.")
    sys.exit(1)

def clear_screen():
    print("\033[2J\033[H", end="")

def draw_bar(val, width=20, char='='):
    # Rysuje pasek: [======|      ] dla -1..1
    # val oczekiwane w zakresie -1.0 .. 1.0 (mniej więcej)
    
    # Clamp -1..1
    val = max(-1.0, min(1.0, val))
    
    center = width // 2
    pos = int(val * center)
    
    bar = [' '] * width
    
    if pos > 0:
        for i in range(center, center + pos):
            bar[i] = char
    elif pos < 0:
        for i in range(center + pos, center):
            bar[i] = char
            
    bar[center] = '|'
    return "[" + "".join(bar) + "]"

def main():
    if not os.access('/dev/input/event0', os.R_OK):
        print("Brak uprawnień! Uruchom: sudo ./venv/bin/python example_game.py")
        return

    print(">>> Inicjalizacja biblioteki WiiboardNative...")
    board = WiiboardNative()
    
    if not board.connect():
        print("Nie znaleziono wagi! Wciśnij POWER na wadze i spróbuj ponownie.")
        return

    print(">>> Waga połączona! Wejdź na nią.")
    print(">>> (Graj balansem ciała lewo/prawo i przód/tył)")
    time.sleep(2)

    try:
        while True:
            # 1. Update stanu wagi (Non-blocking)
            board.update()
            
            # 2. Logika gry (proste wyliczenie środka ciężkości)
            # Sensors: 0:TR, 1:BR, 2:TL, 3:BL
            rv = board.raw_values
            
            total = sum(rv) + 1 # avoid div by zero
            
            # Center of Gravity X (-1 Left .. +1 Right)
            # Right sensors (0+1) - Left sensors (2+3)
            right_mass = rv[0] + rv[1]
            left_mass = rv[2] + rv[3]
            cog_x = (right_mass - left_mass) / total
            
            # Center of Gravity Y (-1 Front .. +1 Back) (Lub odwrotnie, zależy jak stoisz)
            # Front sensors (0+2) - Back sensors (1+3)
            # Zazwyczaj: 0(TR), 2(TL) to przód (przy włączniku?) - do sprawdzenia empirycznie
            front_mass = rv[0] + rv[2]
            back_mass = rv[1] + rv[3]
            cog_y = (front_mass - back_mass) / total

            # 3. Rysowanie (ASCII GUI)
            clear_screen()
            print("=== WII BALANCE BOARD GAME DEMO ===")
            print(f"Total Weight: {board.weight:.2f} kg")
            print("")
            print(f"Balans L/P: {draw_bar(cog_x * 5)} ({cog_x:.2f})") # x5 sensitivity
            print(f"Balans T/P: {draw_bar(cog_y * 5)} ({cog_y:.2f})")
            print("")
            print("TR: %4d  TL: %4d" % (rv[0], rv[2]))
            print("BR: %4d  BL: %4d" % (rv[1], rv[3]))
            print("")
            print("Ctrl+C aby wyjść")
            
            time.sleep(0.05) # 20 FPS

    except KeyboardInterrupt:
        print("\nGame Over.")

if __name__ == "__main__":
    main()
