import os
import shutil

ROM_FOLDER = "ROMs"

def ensure_folders():
    os.makedirs(ROM_FOLDER, exist_ok=True)

def get_rom_path(filename):
    return os.path.join(ROM_FOLDER, filename)

def print_banner():
    print("="*50)
    print('''  .--, -``-.                             ''')
    print(''' /   /     '.      ,---,      .--.--.    ''')
    print('''/ ../        ;   .'  .' `\   /  /    '.  ''')
    print('''\ ``\  .`-    ',---.'     \ |  :  /`. /  ''')
    print(''' \___\/   \   :|   |  .`\  |;  |  |--`   ''')
    print('''      \   :   |:   : |  '  ||  :  ;_     ''')
    print('''      /  /   / |   ' '  ;  : \  \    `.  ''')
    print('''      \  \   \ '   | ;  .  |  `----.   \ ''')
    print('''  ___ /   :   ||   | :  |  '  __ \  \  | ''')
    print(''' /   /\   /   :'   : | /  ;  /  /`--'  / ''')
    print('''/ ,,/  ',-    .|   | '` ,/  '--'.     /  ''')
    print('''\ ''\        ; ;   :  .'      `--'---'   ''')
    print(''' \   \     .'  |   ,.'                   ''')
    print('''  `--`-,,-'    '---'                     ''')
    print("="*50)
    print("\n\n")
    print("A tool to convert CIA into CCI and also to decrypt them and make them playable in citra!")
    print("54634564 - decrypt.exe")
    print("profi200 - makerom.exe, ctrtool.exe")
    print("matif - Batch CIA 3DS Decryptor.bat")
    print("@rohithvishaal - I just wrote this automation script....")
    print("legends are the first three!!!")
    print("-"*50)
    print(f"All ROMs must be placed in the '{ROM_FOLDER}' folder.\nConverted ROMs will also be placed there.\nAvoid filenames with spaces\n")

def print_menu():
    print("-"*50)
    print("MENU:")
    print("0)CCI to CIA converter")
    print("1)CIA to CCI converter")
    print("2)CCI decrypter")
    print("3)CIA to CCI decrypted")
    print("q)Quit")
    print("-"*50)

def find_rom_ext(romName):
    """Return the extension of the file in ROM_FOLDER matching romName (.cci or .cia), or None."""
    for ext in [".cci", ".cia"]:
        if os.path.exists(get_rom_path(f"{romName}{ext}")):
            return ext
    return None

def move_converted_file(romName, original_ext):
    """Move the converted file (the one with the other extension) to ROM_FOLDER."""
    target_ext = ".cia" if original_ext == ".cci" else ".cci"
    output_file = f"{romName}{target_ext}"
    # Search in current dir and in ROM_FOLDER
    for folder in [".", ROM_FOLDER]:
        candidate = os.path.join(folder, output_file)
        if os.path.exists(candidate):
            shutil.move(candidate, get_rom_path(output_file))
            print(f"Moved {output_file} to {ROM_FOLDER} folder.")
            return
    print(f"Warning: {output_file} not found to move to {ROM_FOLDER}.")

def cci_to_cia():
    romName = input("Enter rom name (you can exclude the .cci part): ").strip()
    original_ext = find_rom_ext(romName)
    if original_ext != ".cci":
        print(f"Error: '{romName}.cci' not found in '{ROM_FOLDER}'.")
        return
    in_file = get_rom_path(f"{romName}.cci")
    print("You can open cmd in your folder and type makerom.exe to see all available options")
    command = f"makerom -ccitocia \"{in_file}\""
    print("Executing:", command)
    print("Beginning Conversion!")
    os.system(command)
    move_converted_file(romName, original_ext)
    print("Conversion Complete!")

def cia_to_cci():
    romName = input("Enter rom name (you can exclude the .cia part): ").strip()
    original_ext = find_rom_ext(romName)
    if original_ext != ".cia":
        print(f"Error: '{romName}.cia' not found in '{ROM_FOLDER}'.")
        return
    in_file = get_rom_path(f"{romName}.cia")
    print("You can open cmd in your folder and type makerom.exe to see all available options")
    command = f"makerom -ciatocci \"{in_file}\""
    print("Executing:", command)
    print("Beginning Conversion to .cci!")
    os.system(command)
    move_converted_file(romName, original_ext)
    print("Conversion Complete!")

def cci_decrypter():
    print(f"Place your ROM file in the '{ROM_FOLDER}' folder")
    print("This takes some time, don't think your screen is frozen :)")
    input("Press Enter to continue!")
    # Copy all .cci files from ROM_FOLDER to working dir, run batch, then move results to ROM_FOLDER
    for file in os.listdir(ROM_FOLDER):
        if file.lower().endswith(".cci"):
            shutil.copy(get_rom_path(file), file)
    os.system('"Batch CIA 3DS Decryptor".bat')
    # Move all .3ds files to ROM_FOLDER
    for file in os.listdir():
        if file.lower().endswith(".3ds"):
            shutil.move(file, get_rom_path(file))
            print(f"Moved {file} to {ROM_FOLDER} folder.")

def cia_to_cci_decrypted():
    print("Do this if your rom is encrypted only!")
    print("To check whether your rom is encrypted just load the .cci file in citra")
    romName = input("Enter rom name (you can exclude the .cia part): ").strip()
    original_ext = find_rom_ext(romName)
    if original_ext != ".cia":
        print(f"Error: '{romName}.cia' not found in '{ROM_FOLDER}'.")
        return
    in_file = get_rom_path(f"{romName}.cia")
    command = f"makerom -ciatocci \"{in_file}\""
    print("Executing:", command)
    print("Beginning Conversion!")
    os.system(command)
    # Move output CCI to working dir for decryption
    out_file = f"{romName}.cci"
    if os.path.exists(out_file):
        print(f"Found {out_file} for decryption.")
    elif os.path.exists(get_rom_path(out_file)):
        shutil.move(get_rom_path(out_file), out_file)
        print(f"Moved {out_file} to working directory for decryption.")
    else:
        print(f"Warning: {out_file} not found for decryption.")
    print("Conversion Complete!\nBeginning Decrypting process\n")
    print("This takes some time, don't think your screen is frozen :)")
    os.system('"Batch CIA 3DS Decryptor".bat')
    # Move .3ds file to ROM_FOLDER
    out_3ds = f"{romName}.3ds"
    if os.path.exists(out_3ds):
        shutil.move(out_3ds, get_rom_path(out_3ds))
        print(f"Moved {out_3ds} to {ROM_FOLDER} folder.")

def main():
    ensure_folders()
    print_banner()
    while True:
        print_menu()
        choice = input("Enter Choice: ").strip().lower()
        print("\n" + "-"*50)
        try:
            if choice == "0":
                cci_to_cia()
                break
            elif choice == "1":
                cia_to_cci()
                break
            elif choice == "2":
                cci_decrypter()
                break
            elif choice == "3":
                cia_to_cci_decrypted()
                break
            elif choice == "q":
                print("Goodbye!")
                break
            else:
                print("Please enter a valid choice (0, 1, 2, 3, or q).")
        except Exception as e:
            print("Something went wrong!")
            print("Error:", e)
            print("Possible reasons:")
            print("1) Did you enter a valid name of the rom?")
            print(f"2) Is the rom in the '{ROM_FOLDER}' folder (it needs to be)?")
            print("3) A corrupted rom file.")
            print("Try again or press Ctrl+C to quit.\n")

if __name__ == "__main__":
    main()