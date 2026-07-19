You might also be interested in [Hotcorners for windows](https://github.com/rohithvishaal/hotcorners-for-windows) (triggers actions you set when your mouse cursor reaches the corners of your screen)

# 3DS ROM Converter Pro - Modern Edition

A modern GUI-based tool for converting 3DS ROM files between CIA and CCI formats and for decrypting them for use with Citra.

![UI](screenshots/GUI.png)

## What this tool does

The current GUI workflow is implemented in [3ds_converter_gui.py](3ds_converter_gui.py). It provides a desktop interface for:

- CCI to CIA conversion
- CIA to CCI conversion
- CCI decryption
- CIA to decrypted CCI conversion

For the CCI-to-CIA and CIA-to-CCI flows, the script will first try the normal conversion and, if that fails, it will attempt a decrypt-first retry before trying again.

## Features

- Modern Tkinter-based GUI window
- Single ROM mode or full-folder batch mode
- Output folder selection
- Real-time log window
- Status bar and progress indicator
- Automatic detection of available CCI and CIA files in a selected folder
- Batch processing for multiple files and conversion types

## Requirements

- Python 3.9 or higher
- Windows operating system
- The helper files must be available in the project folder or the bin folder:
  - [bin/makerom.exe](bin/makerom.exe)
  - [bin/ctrtool.exe](bin/ctrtool.exe)
  - [bin/decrypt.exe](bin/decrypt.exe)
  - [bin/seeddb.bin](bin/seeddb.bin)
  - [Batch CIA 3DS Decryptor Redux.bat](Batch%20CIA%203DS%20Decryptor%20Redux.bat)

## Installation

### 1. Install Python
Download and install Python from python.org and make sure Python is added to PATH.

### 2. Verify Python is available
Run this in PowerShell:

```powershell
python --version
```

### 3. Place the required files in the project folder
The GUI expects the batch script and tools to be available so it can launch them when needed.

## Running the GUI

From the project folder, run:

```powershell
python 3ds_converter_gui.py
```

You can also launch it with:

```powershell
Launch_GUI.bat
```

## Using the GUI

### Input selection
Choose one of two modes:

- Single ROM File: convert one selected ROM file
- Entire Folder: process all compatible ROMs in a chosen folder

### Single ROM mode
1. Click Browse ROM File and select a .cia or .cci ROM.
2. Enter or confirm the ROM name.
3. Choose a conversion type from the dropdown.
4. Choose an output folder.
5. Click Start Conversion.

### Folder batch mode
1. Click Browse Folder and select a directory containing ROM files.
2. The GUI will show how many .cci and .cia files it found.
3. Enable one or more conversion options:
   - CCI → CIA
   - CIA → CCI
   - CCI Decrypt
   - CIA → Decrypted CCI
4. Choose an output folder.
5. Click Start Conversion.

### Output behavior
By default, converted files are written to the ROMs folder. You can choose another output location in the GUI.

## File layout

```text
3ds-converters/
├── 3ds_converter_gui.py
├── 3ds.py
├── Batch CIA 3DS Decryptor Redux.bat
├── Launch_GUI.bat
├── bin/
│   ├── makerom.exe
│   ├── ctrtool.exe
│   ├── decrypt.exe
│   └── seeddb.bin
├── ROMs/
└── screenshots/
```

## Fallback option if the GUI fails

If the GUI script does not complete successfully, you can fall back to the batch script directly.

1. Place the ROM files in the same folder as [Batch CIA 3DS Decryptor Redux.bat](Batch%20CIA%203DS%20Decryptor%20Redux.bat).
2. Double-click the batch file or run it from PowerShell:

```powershell
./Batch CIA 3DS Decryptor Redux.bat
```

3. Follow the prompts in the console window.

This is useful when you want a simpler, script-driven approach for decryption and conversion.

## Troubleshooting

### Python is not recognized
Install Python and make sure it is added to PATH.

### makerom.exe or ctrtool.exe not found
Make sure the files exist in the bin folder and that the batch script can access them.

### ROM not found
Check that the ROM file is present in the selected source folder or that the correct file extension is being used (.cia or .cci).

### Conversion seems slow
Some conversions can take several minutes. The GUI remains responsive while work is running.

### The batch script is easier to use in some cases
If the GUI fails repeatedly, try the batch script fallback described above and keep the ROMs in the same folder as the batch script.

## Credits

Original credits for the underlying tools and workflow:

- 54634564 - decrypt.exe
- profi200 - makerom.exe and ctrtool.exe
- matif - Batch CIA 3DS Decryptor batch flow
- @xxmichibxx - Batch CIA 3DS Decryptor Redux
- @rohithvishaal - original automation script
