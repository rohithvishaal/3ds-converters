"""
3DS ROM Converter with GUI
A modern, async-based tool to convert CIA into CCI and decrypt them for use with citra.

Original Credits:
- 54634564 - decrypt.exe
- profi200 - makerom.exe, ctrtool.exe
- matif - Batch CIA 3DS Decryptor.bat
- @rohithvishaal - Original automation script

Rewritten with modern Python standards, async support, and GUI.
"""

import asyncio
import shutil
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Callable
from enum import Enum
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import tkinter.font as tkfont

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConversionType(Enum):
    """Supported conversion types."""
    CCI_TO_CIA = "CCI to CIA"
    CIA_TO_CCI = "CIA to CCI"
    CCI_DECRYPT = "CCI Decrypt"
    CIA_TO_DECRYPTED = "CIA to Decrypted CCI"


@dataclass
class ConversionConfig:
    """Configuration for a conversion operation."""
    rom_name: str
    rom_folder: Path
    conversion_type: ConversionType
    output_folder: Path = None  # Where to save converted files
    output_callback: Optional[Callable] = None


class ROMConverter:
    """Handles all ROM conversion operations asynchronously."""
    
    def __init__(self, rom_folder: str = "ROMs"):
        self.rom_folder = Path(rom_folder)
        self.output_folder = self.rom_folder  # Default to rom_folder
        self.script_dir = Path(__file__).resolve().parent
        self.makerom_exe = self.script_dir / "bin" / "makerom.exe"
        self.ensure_folders()
        
    def ensure_folders(self) -> None:
        """Ensure ROM folder exists."""
        self.rom_folder.mkdir(exist_ok=True)
        if self.output_folder != self.rom_folder:
            self.output_folder.mkdir(exist_ok=True)
        logger.info(f"ROM folder ready: {self.rom_folder.absolute()}")
    
    def find_rom_ext(self, rom_name: str) -> Optional[str]:
        """Find the extension of the ROM file (.cci or .cia)."""
        for ext in [".cci", ".cia"]:
            if (self.rom_folder / f"{rom_name}{ext}").exists():
                return ext
        return None
    
    def get_rom_path(self, filename: str) -> Path:
        """Get full path to ROM file."""
        return self.rom_folder / filename
    
    async def run_command(self, args: list, cwd: Optional[Path] = None) -> tuple[int, str, str]:
        """
        Run an external command asynchronously.

        Uses exec (not shell) so paths with spaces/special characters never need manual
        quoting and no extra cmd.exe/sh process has to be spawned just to parse a string.

        Args:
            args: Command and arguments as a list, e.g. [str(makerom_exe), "-ciatocci", str(in_file)]
            cwd: Working directory to run the command in (controls where output files land)

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        str_args = [str(a) for a in args]
        logger.info(f"Executing: {' '.join(str_args)}")
        try:
            process = await asyncio.create_subprocess_exec(
                *str_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(cwd) if cwd else None,
            )
            stdout, stderr = await process.communicate()
            return (
                process.returncode,
                stdout.decode('utf-8', errors='replace'),
                stderr.decode('utf-8', errors='replace')
            )
        except Exception as e:
            logger.error(f"Error running command: {e}")
            return (-1, "", str(e))
    
    async def move_converted_file(self, rom_name: str, original_ext: str, output_folder: Optional[Path] = None) -> bool:
        """
        Move converted file to output folder.
        
        Args:
            rom_name: Name of the ROM (without extension)
            original_ext: Original extension (.cci or .cia)
            output_folder: Where to save the file (defaults to rom_folder)
            
        Returns:
            True if move was successful, False otherwise
        """
        if output_folder is None:
            output_folder = self.output_folder
            
        target_ext = ".cia" if original_ext == ".cci" else ".cci"
        output_file = f"{rom_name}{target_ext}"
        normalized_rom_name = rom_name.lower().replace("-decrypted", "")
        name_variants = {
            rom_name,
            rom_name.replace("-decrypted", ""),
            rom_name.replace(".cia", "").replace(".cci", ""),
            rom_name.replace("-decrypted", "").replace(".cia", "").replace(".cci", ""),
        }

        search_dirs = [
            self.rom_folder,
            output_folder,
        ]

        for folder in search_dirs:
            candidate = folder / output_file
            if candidate.exists():
                try:
                    dest_path = output_folder / output_file
                    output_folder.mkdir(parents=True, exist_ok=True)
                    if candidate.resolve() == dest_path.resolve():
                        logger.info(f"Converted file already present at destination: {dest_path}")
                        return True
                    if dest_path.exists():
                        logger.info(f"Removing existing destination before move: {dest_path}")
                        dest_path.unlink()
                    shutil.move(str(candidate), str(dest_path))
                    logger.info(f"Moved {output_file} to {output_folder} folder.")
                    return True
                except Exception as e:
                    logger.error(f"Error moving file: {e}")
                    return False

        candidates = []
        for folder in search_dirs:
            if not folder.exists():
                continue
            for match in folder.glob(f"*{target_ext}"):
                if not match.is_file():
                    continue
                match_name = match.stem.lower()
                if any(match_name == variant.lower() for variant in name_variants):
                    candidates.append(match)
                elif normalized_rom_name and normalized_rom_name in match_name:
                    candidates.append(match)

        if candidates:
            candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            chosen = candidates[0]
            try:
                dest_path = output_folder / chosen.name
                output_folder.mkdir(parents=True, exist_ok=True)
                if dest_path.exists():
                    dest_path.unlink()
                shutil.move(str(chosen), str(dest_path))
                logger.info(f"Moved converted file {chosen.name} to {output_folder}.")
                return True
            except Exception as e:
                logger.error(f"Error moving file: {e}")
                return False
        
        logger.warning(f"{output_file} not found to move to {output_folder}.")
        return False

    def get_batch_script_path(self) -> Optional[Path]:
        """Locate the batch decryptor script used by the GUI."""
        script_dir = Path(__file__).resolve().parent
        for candidate in [
            script_dir / "Batch CIA 3DS Decryptor Redux.bat",
        ]:
            if candidate.exists():
                return candidate
        return None

    def find_decrypted_output(self, rom_name: str, output_folder: Path, convert_to_cci: bool = False) -> Optional[Path]:
        """Find the decrypted output produced by the batch script."""
        patterns = [f"{rom_name}*-decrypted.cci", f"{rom_name}*-decrypted.cia", f"{rom_name}.3ds", f"{rom_name}*.3ds"]
        if convert_to_cci:
            patterns = [f"{rom_name}*-decrypted.cci", f"{rom_name}*.cci", f"{rom_name}.3ds"]
        else:
            patterns = [f"{rom_name}*-decrypted.cia", f"{rom_name}*.cia"]

        search_dirs = [output_folder, self.rom_folder]
        for folder in search_dirs:
            if not folder.exists():
                continue
            for pattern in patterns:
                matches = sorted(folder.glob(pattern))
                if matches:
                    return matches[0]
        return None

    def prepare_batch_runtime(self, target_dir: Path) -> Optional[Path]:
        """
        Copy the batch decryptor script and its bin/ dependencies into target_dir so it can
        run directly against ROM files that already live there.

        This is the key perf fix: previously every ROM file in the folder was copied into
        the script's own directory before each run (and batch mode did this once per file,
        i.e. up to N times for N ROMs). ROM files can be hundreds of MB to several GB, while
        bin/ is a handful of small executables, so copying the tool in instead of the ROMs
        out avoids that I/O entirely.
        """
        source_script = self.get_batch_script_path()
        if source_script is None:
            logger.error("Batch decryptor script not found")
            return None

        source_dir = source_script.parent
        source_bin = source_dir / "bin"
        target_bin = target_dir / "bin"
        target_script = target_dir / source_script.name

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            if source_bin.exists():
                if target_bin.exists():
                    shutil.rmtree(target_bin)
                shutil.copytree(source_bin, target_bin)
            shutil.copy2(source_script, target_script)
        except Exception as e:
            logger.error(f"Failed to prepare batch runtime in {target_dir}: {e}")
            return None

        return target_script

    def cleanup_batch_runtime(self, target_dir: Path) -> None:
        """Remove the copied batch script, its bin/ folder, and its log/ folder from target_dir."""
        source_script = self.get_batch_script_path()
        names_to_remove = ["bin", "log"]
        if source_script is not None:
            names_to_remove.append(source_script.name)

        for name in names_to_remove:
            candidate = target_dir / name
            try:
                if candidate.is_dir():
                    shutil.rmtree(candidate)
                elif candidate.is_file():
                    candidate.unlink()
            except Exception as e:
                logger.warning(f"Could not remove batch runtime item {candidate}: {e}")

    async def run_batch_decrypt(
        self,
        output_folder: Optional[Path] = None,
        convert_to_cci: bool = False,
        move_outputs: bool = True,
        rom_name_filter: Optional[str] = None,
        exclude_paths: Optional[set] = None,
    ) -> tuple[bool, str]:
        """
        Run the batch decryptor directly inside the ROM folder and collect any output files.

        Runs in-place against self.rom_folder rather than copying ROM files elsewhere; only
        the batch script + bin/ are copied in (and cleaned up again) each run. rom_name_filter
        and exclude_paths keep this safe when other unrelated ROMs share the same folder: only
        newly produced "-decrypted" files matching rom_name_filter are treated as output, and
        the original source file is never mistaken for output.
        """
        if output_folder is None:
            output_folder = self.output_folder
        excluded = {p.resolve() for p in (exclude_paths or set())}

        working_dir = self.rom_folder
        batch_script = self.prepare_batch_runtime(working_dir)
        if batch_script is None:
            msg = "Batch decryptor script not found or could not be prepared"
            return (False, msg)

        input_data = b"y\n" if convert_to_cci else b"n\n"
        logger.info("Running batch decryption flow directly in the ROM folder (no ROM copy needed)...")
        try:
            process = await asyncio.create_subprocess_exec(
                "cmd", "/c", str(batch_script),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(working_dir),
            )
            stdout, stderr = await process.communicate(input_data)
            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")
        finally:
            self.cleanup_batch_runtime(working_dir)

        if stdout_text:
            logger.info(stdout_text)
        if stderr_text:
            logger.warning(stderr_text)

        # Only newly-produced "-decrypted" files count as output; this never picks up the
        # original source ROM or unrelated ROMs sitting in the same folder.
        candidates = []
        for candidate in sorted(working_dir.glob("*")):
            if not candidate.is_file() or candidate.resolve() in excluded:
                continue
            if candidate.suffix.lower() not in {".cia", ".cci", ".3ds"}:
                continue
            name_lower = candidate.name.lower()
            if "decrypted" not in name_lower:
                continue
            if rom_name_filter and rom_name_filter.lower() not in name_lower:
                continue
            candidates.append(candidate)

        if not candidates:
            return (False, "No decrypted output files were produced")

        same_dir = output_folder.resolve() == working_dir.resolve()
        if not move_outputs or same_dir:
            logger.info(f"Decrypted output left in place: {working_dir}")
            return (True, f"Batch decryption completed; outputs are in {working_dir}")

        output_folder.mkdir(parents=True, exist_ok=True)
        moved = []
        for candidate in candidates:
            try:
                dest_path = output_folder / candidate.name
                if dest_path.exists():
                    dest_path.unlink()
                shutil.move(str(candidate), str(dest_path))
                moved.append(dest_path)
            except Exception as e:
                logger.error(f"Error moving decrypted output {candidate.name}: {e}")

        if moved:
            logger.info(f"Moved {len(moved)} decrypted output file(s) to {output_folder}")
            return (True, f"Batch decryption completed and outputs were moved to {output_folder}")
        return (False, "No decrypted output files were produced")

    async def decrypt_rom_file(self, rom_name: str, output_folder: Optional[Path] = None, convert_to_cci: bool = False, move_outputs: bool = True) -> tuple[bool, str, Optional[Path]]:
        """Decrypt a ROM file using the batch script before conversion."""
        if output_folder is None:
            output_folder = self.output_folder

        original_ext = self.find_rom_ext(rom_name)
        if original_ext is None:
            msg = f"Error: '{rom_name}' not found"
            logger.error(msg)
            return (False, msg, None)

        source_file = self.get_rom_path(f"{rom_name}{original_ext}")
        if not source_file.exists():
            msg = f"Error: '{source_file.name}' not found"
            logger.error(msg)
            return (False, msg, None)

        logger.info(f"Preparing batch decryption for {source_file.name}")
        success, msg = await self.run_batch_decrypt(
            output_folder,
            convert_to_cci=convert_to_cci,
            move_outputs=move_outputs,
            rom_name_filter=rom_name,
            exclude_paths={source_file},
        )
        if not success:
            return (False, msg, None)

        output_path = self.find_decrypted_output(rom_name, output_folder, convert_to_cci=convert_to_cci)
        if output_path is None:
            return (False, "Batch decryption completed but no matching output file was found", None)
        return (True, msg, output_path)

    async def get_retry_input(self, rom_name: str, output_folder: Path, original_input: Path) -> Path:
        """Try the batch-based decrypt flow and return a decrypted intermediate if available."""
        for convert_to_cci in (True, False):
            decrypt_success, decrypt_msg, decrypted_path = await self.decrypt_rom_file(
                rom_name,
                output_folder,
                convert_to_cci=convert_to_cci,
                move_outputs=False,
            )
            if decrypt_success and decrypted_path is not None and decrypted_path.exists():
                logger.info(f"Using decrypted retry input from batch flow: {decrypted_path}")
                return decrypted_path
            if not decrypt_success:
                logger.warning(f"Decrypt-first retry attempt failed: {decrypt_msg}")

        logger.info(f"No decrypted retry input found; falling back to original input: {original_input}")
        return original_input
    
    async def _convert_with_makerom(self, rom_name: str, source_ext: str, makerom_flag: str, output_folder: Optional[Path] = None) -> tuple[bool, str]:
        """
        Shared conversion logic for both cci_to_cia and cia_to_cci: run makerom, and if it
        fails on the plain encrypted input, retry using a decrypted intermediate from the
        batch flow. Extracted once so a fix here (like the .cci-fed-back-into-makerom bug)
        automatically applies to both directions instead of needing to be fixed twice.
        """
        if output_folder is None:
            output_folder = self.output_folder

        conv_name = "CIA to CCI" if makerom_flag == "-ciatocci" else "CCI to CIA"
        target_ext = ".cci" if makerom_flag == "-ciatocci" else ".cia"

        original_ext = self.find_rom_ext(rom_name)
        if original_ext != source_ext:
            msg = f"Error: '{rom_name}{source_ext}' not found"
            logger.error(msg)
            return (False, msg)

        in_file = self.get_rom_path(f"{rom_name}{source_ext}")
        logger.info(f"Beginning {conv_name} conversion!")
        return_code, stdout, stderr = await self.run_command(
            [self.makerom_exe, makerom_flag, in_file], cwd=in_file.parent
        )

        if return_code != 0:
            logger.warning(f"Initial {conv_name} conversion failed; attempting decrypt-first retry...")
            retry_input = await self.get_retry_input(rom_name, output_folder, in_file)
            if retry_input != in_file:
                logger.info(f"Using decrypted input for retry: {retry_input}")

            if retry_input.suffix.lower() == target_ext:
                # The decrypt-first batch flow (convert_to_cci=True) asks the batch script
                # to decrypt AND pack the target format itself, so retry_input here is
                # already the finished file -- not an intermediate for makerom to consume.
                # Feeding it back into makerom would be invalid (that was the original bug);
                # there's nothing left for makerom to do, so just use it directly.
                logger.info(f"Decrypt retry already produced a finished {target_ext} file; using it directly instead of calling makerom again.")
                dest_path = output_folder / f"{rom_name}{target_ext}"
                try:
                    output_folder.mkdir(parents=True, exist_ok=True)
                    if dest_path.exists():
                        dest_path.unlink()
                    if retry_input.resolve() != dest_path.resolve():
                        shutil.move(str(retry_input), str(dest_path))
                    msg = f"{conv_name} conversion completed successfully (via decrypt-first flow)!"
                    logger.info(msg)
                    return (True, msg)
                except Exception as e:
                    msg = f"Decrypted {target_ext} file produced but failed to move into place: {e}"
                    logger.error(msg)
                    return (False, msg)

            return_code, stdout, stderr = await self.run_command(
                [self.makerom_exe, makerom_flag, retry_input], cwd=retry_input.parent
            )
            if return_code != 0:
                msg = f"Conversion failed after decrypt retry: {stderr or 'No detailed error output was produced.'}"
                logger.error(msg)
                return (False, msg)

        success = await self.move_converted_file(rom_name, original_ext, output_folder)
        msg = f"{conv_name} conversion completed successfully!" if success else "Conversion completed but file move failed"
        logger.info(msg)
        return (success, msg)

    async def cci_to_cia(self, rom_name: str, output_folder: Optional[Path] = None) -> tuple[bool, str]:
        """Convert CCI to CIA, retrying after decryption if the initial conversion fails."""
        return await self._convert_with_makerom(rom_name, ".cci", "-ccitocia", output_folder)

    async def cia_to_cci(self, rom_name: str, output_folder: Optional[Path] = None) -> tuple[bool, str]:
        """Convert CIA to CCI, retrying after decryption if the initial conversion fails."""
        return await self._convert_with_makerom(rom_name, ".cia", "-ciatocci", output_folder)
    
    async def cci_decrypt(self) -> tuple[bool, str]:
        """Decrypt all CCI files using the same batch flow as the .bat script."""
        logger.info("Starting CCI decryption process...")
        
        cci_files = list(self.rom_folder.glob("*.cci"))
        if not cci_files:
            msg = "No CCI files found for decryption"
            logger.warning(msg)
            return (False, msg)
        
        success, msg = await self.run_batch_decrypt(self.rom_folder, convert_to_cci=False)
        if success:
            logger.info(msg)
            return (True, msg)
        logger.warning(msg)
        return (False, msg)
    
    async def cia_to_decrypted(self, rom_name: str, output_folder: Optional[Path] = None) -> tuple[bool, str]:
        """Convert CIA to decrypted CCI by following the batch script's decrypt-first flow."""
        if output_folder is None:
            output_folder = self.output_folder
            
        original_ext = self.find_rom_ext(rom_name)
        if original_ext != ".cia":
            msg = f"Error: '{rom_name}.cia' not found"
            logger.error(msg)
            return (False, msg)
        
        logger.info("Beginning batch-based CIA decrypt and conversion flow...")
        decrypt_success, decrypt_msg, decrypted_path = await self.decrypt_rom_file(rom_name, output_folder, convert_to_cci=True, move_outputs=True)
        if decrypt_success and decrypted_path is not None and decrypted_path.exists():
            msg = f"CIA to decrypted output completed: {decrypted_path.name}"
            logger.info(msg)
            return (True, msg)

        msg = f"Decryption output not found after batch processing: {decrypt_msg}"
        logger.warning(msg)
        return (False, msg)
    
    async def cci_to_cia_batch(self, rom_names: list[str]) -> tuple[bool, str]:
        """Convert multiple CCI files to CIA."""
        results = []
        for rom_name in rom_names:
            success, msg = await self.cci_to_cia(rom_name)
            results.append((rom_name, success, msg))
        
        successful = sum(1 for _, success, _ in results if success)
        msg = f"Batch CCI to CIA: {successful}/{len(rom_names)} completed"
        logger.info(msg)
        return (successful > 0, msg)
    
    async def cia_to_cci_batch(self, rom_names: list[str]) -> tuple[bool, str]:
        """Convert multiple CIA files to CCI."""
        results = []
        for rom_name in rom_names:
            success, msg = await self.cia_to_cci(rom_name)
            results.append((rom_name, success, msg))
        
        successful = sum(1 for _, success, _ in results if success)
        msg = f"Batch CIA to CCI: {successful}/{len(rom_names)} completed"
        logger.info(msg)
        return (successful > 0, msg)
    
    def get_roms_in_folder(self, folder: Path, extension: str) -> list[str]:
        """Get all ROM names with specific extension in folder."""
        roms = []
        for file in folder.glob(f"*{extension}"):
            roms.append(file.stem)
        return roms
    
    async def convert(self, config: ConversionConfig) -> tuple[bool, str]:
        """Execute conversion based on config."""
        try:
            output_folder = config.output_folder or self.output_folder
            
            if config.conversion_type == ConversionType.CCI_TO_CIA:
                return await self.cci_to_cia(config.rom_name, output_folder)
            elif config.conversion_type == ConversionType.CIA_TO_CCI:
                return await self.cia_to_cci(config.rom_name, output_folder)
            elif config.conversion_type == ConversionType.CCI_DECRYPT:
                return await self.cci_decrypt()
            elif config.conversion_type == ConversionType.CIA_TO_DECRYPTED:
                return await self.cia_to_decrypted(config.rom_name, output_folder)
        except Exception as e:
            msg = f"Unexpected error: {e}"
            logger.error(msg)
            return (False, msg)


class ConverterGUI:
    """Modern GUI for the 3DS ROM Converter."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.converter = ROMConverter()
        self.selected_rom_file: Optional[Path] = None  # Store full path to browsed ROM
        self.setup_ui()
        self.running = False

    def _post(self, fn, *args, **kwargs) -> None:
        """
        Schedule a Tkinter-mutating callable to run on the main thread.

        Conversions run in a background thread (see run_conversion etc.), but Tkinter is
        not thread-safe. Every widget update, status/messagebox call, and log append that
        happens during a conversion must go through this instead of being called directly,
        or the UI can intermittently freeze/corrupt.
        """
        self.root.after(0, lambda: fn(*args, **kwargs))
        
    def setup_ui(self) -> None:
        """Setup the GUI interface."""
        self.root.title("3DS ROM Converter Pro")
        self.root.geometry("1000x900")
        self.root.resizable(True, True)
        self.root.minsize(800, 700)  # Minimum window size
        
        # Style configuration
        style = ttk.Style()
        style.theme_use('clam')

        # Derive fonts from the platform's own default rather than hardcoding "Arial",
        # which isn't guaranteed to be installed on Linux/macOS.
        default_font = tkfont.nametofont("TkDefaultFont")
        self.title_font = default_font.copy()
        self.title_font.configure(size=16, weight="bold")
        self.label_font = default_font.copy()
        self.label_font.configure(size=10)
        self.bold_label_font = default_font.copy()
        self.bold_label_font.configure(size=9, weight="bold")
        self.small_font = default_font.copy()
        self.small_font.configure(size=9)
        
        # Main container with proper weight distribution
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # Configure row weights for proper scaling
        main_frame.rowconfigure(0, weight=0)  # Title
        main_frame.rowconfigure(1, weight=0)  # Input mode
        main_frame.rowconfigure(2, weight=0)  # Single/Folder frame
        main_frame.rowconfigure(3, weight=0)  # Output destination
        main_frame.rowconfigure(4, weight=0)  # Buttons
        main_frame.rowconfigure(5, weight=0)  # Log label
        main_frame.rowconfigure(6, weight=1)  # Log area (expandable)
        main_frame.rowconfigure(7, weight=0)  # Status bar
        main_frame.rowconfigure(8, weight=0)  # Progress bar
        
        # Title
        title_label = ttk.Label(main_frame, text="3DS ROM Converter Pro", 
                               font=self.title_font)
        title_label.grid(row=0, column=0, columnspan=3, pady=10)
        
        # === Input Mode Selection ===
        input_frame = ttk.LabelFrame(main_frame, text="Input Selection", padding="8")
        input_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        input_frame.columnconfigure(0, weight=1)
        
        self.input_mode_var = tk.StringVar(value="single")
        ttk.Radiobutton(input_frame, text="Single ROM File", variable=self.input_mode_var, 
                       value="single", command=self.on_input_mode_changed).pack(anchor=tk.W, padx=5)
        ttk.Radiobutton(input_frame, text="Entire Folder", variable=self.input_mode_var, 
                       value="folder", command=self.on_input_mode_changed).pack(anchor=tk.W, padx=5)
        
        # === Single ROM Mode ===
        single_frame = ttk.LabelFrame(main_frame, text="Single ROM Mode", padding="8")
        single_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        single_frame.columnconfigure(1, weight=1)
        
        # ROM name input
        ttk.Label(single_frame, text="ROM Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.rom_name_var = tk.StringVar()
        rom_name_entry = ttk.Entry(single_frame, textvariable=self.rom_name_var, width=40)
        rom_name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        ttk.Button(single_frame, text="Browse ROM File", 
                  command=self.on_browse_rom_file).grid(row=0, column=2, padx=5)
        
        # Conversion type
        ttk.Label(single_frame, text="Conversion Type:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.conversion_var = tk.StringVar()
        conversion_combo = ttk.Combobox(single_frame, textvariable=self.conversion_var,
                                       values=[ct.value for ct in ConversionType],
                                       state="readonly", width=37)
        conversion_combo.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5, padx=5)
        conversion_combo.current(0)
        
        self.single_frame = single_frame
        
        # === Folder Mode ===
        folder_frame = ttk.LabelFrame(main_frame, text="Folder Batch Mode", padding="8")
        folder_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        folder_frame.columnconfigure(1, weight=1)
        
        # Source folder
        ttk.Label(folder_frame, text="Source Folder:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.source_folder_var = tk.StringVar()
        ttk.Entry(folder_frame, textvariable=self.source_folder_var, width=40,
                 state='readonly').grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        ttk.Button(folder_frame, text="Browse Folder", 
                  command=self.on_browse_source_folder).grid(row=0, column=2, padx=5)
        
        # File statistics and conversion options
        stats_frame = ttk.LabelFrame(folder_frame, text="Available Files & Conversion Options", padding="5")
        stats_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        stats_frame.columnconfigure(0, weight=1)
        
        # File counts
        self.cci_count_label = ttk.Label(stats_frame, text="CCI files: 0", font=self.label_font)
        self.cci_count_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        
        self.cia_count_label = ttk.Label(stats_frame, text="CIA files: 0", font=self.label_font)
        self.cia_count_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=3)
        
        # Conversion options frame
        options_frame = ttk.Frame(stats_frame)
        options_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        options_frame.columnconfigure(0, weight=1)
        
        ttk.Label(options_frame, text="Convert:", font=self.bold_label_font).pack(anchor=tk.W, padx=5)
        
        # CCI → CIA option
        self.convert_cci_to_cia_frame = ttk.Frame(options_frame)
        self.convert_cci_to_cia_frame.pack(anchor=tk.W, padx=20, pady=2)
        
        self.convert_cci_to_cia_var = tk.BooleanVar(value=False)
        self.convert_cci_to_cia_check = ttk.Checkbutton(self.convert_cci_to_cia_frame, 
                                                        text="CCI → CIA",
                                                        variable=self.convert_cci_to_cia_var,
                                                        state=tk.DISABLED)
        self.convert_cci_to_cia_check.pack(anchor=tk.W)
        
        # CIA → CCI option
        self.convert_cia_to_cci_frame = ttk.Frame(options_frame)
        self.convert_cia_to_cci_frame.pack(anchor=tk.W, padx=20, pady=2)
        
        self.convert_cia_to_cci_var = tk.BooleanVar(value=False)
        self.convert_cia_to_cci_check = ttk.Checkbutton(self.convert_cia_to_cci_frame,
                                                        text="CIA → CCI",
                                                        variable=self.convert_cia_to_cci_var,
                                                        state=tk.DISABLED)
        self.convert_cia_to_cci_check.pack(anchor=tk.W)
        
        # CCI Decrypt option
        self.decrypt_cci_frame = ttk.Frame(options_frame)
        self.decrypt_cci_frame.pack(anchor=tk.W, padx=20, pady=2)
        
        self.decrypt_cci_var = tk.BooleanVar(value=False)
        self.decrypt_cci_check = ttk.Checkbutton(self.decrypt_cci_frame,
                                                 text="CCI Decrypt",
                                                 variable=self.decrypt_cci_var,
                                                 state=tk.DISABLED)
        self.decrypt_cci_check.pack(anchor=tk.W)
        
        # CIA to Decrypted CCI option
        self.cia_to_decrypted_frame = ttk.Frame(options_frame)
        self.cia_to_decrypted_frame.pack(anchor=tk.W, padx=20, pady=2)
        
        self.cia_to_decrypted_var = tk.BooleanVar(value=False)
        self.cia_to_decrypted_check = ttk.Checkbutton(self.cia_to_decrypted_frame,
                                                      text="CIA → Decrypted CCI",
                                                      variable=self.cia_to_decrypted_var,
                                                      state=tk.DISABLED)
        self.cia_to_decrypted_check.pack(anchor=tk.W)
        
        self.folder_frame = folder_frame
        
        # === Output Destination ===
        output_frame = ttk.LabelFrame(main_frame, text="Output Destination", padding="8")
        output_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        output_frame.columnconfigure(1, weight=1)
        
        ttk.Label(output_frame, text="Output Folder:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.output_folder_var = tk.StringVar()
        output_entry = ttk.Entry(output_frame, textvariable=self.output_folder_var, width=40)
        output_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        ttk.Button(output_frame, text="Browse Output", 
                  command=self.on_browse_output_folder).grid(row=0, column=2, padx=5)
        
        # Set default output folder
        self.output_folder_var.set(str(self.converter.rom_folder))
        
        # === Buttons frame ===
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        self.convert_btn = ttk.Button(button_frame, text="Start Conversion", 
                                     command=self.on_convert_clicked)
        self.convert_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Clear", 
                  command=self.on_clear_clicked).pack(side=tk.LEFT, padx=5)
        
        # === Log output ===
        ttk.Label(main_frame, text="Log Output:").grid(row=5, column=0, sticky=tk.W, pady=(10, 0))
        
        log_frame = ttk.Frame(main_frame)
        log_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=100,
                                                  state=tk.NORMAL, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # === Status bar ===
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, 
                              relief=tk.SUNKEN, font=self.small_font)
        status_bar.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # === Progress bar ===
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # Initialize UI state
        self.on_input_mode_changed()
        
        # Redirect logger to GUI
        self.setup_log_handler()
    
    def setup_log_handler(self) -> None:
        """Setup logging to display in the GUI, safely from any thread."""
        MAX_LOG_LINES = 2000

        self.log_text.tag_configure("ERROR", foreground="#c0392b")
        self.log_text.tag_configure("WARNING", foreground="#b9770e")
        self.log_text.tag_configure("INFO", foreground="#2c3e50")

        root = self.root
        text_widget = self.log_text

        class GUIHandler(logging.Handler):
            def emit(self, record):
                msg = self.format(record)
                tag = record.levelname if record.levelname in {"ERROR", "WARNING"} else "INFO"

                def append():
                    text_widget.insert(tk.END, msg + "\n", tag)
                    line_count = int(text_widget.index('end-1c').split('.')[0])
                    if line_count > MAX_LOG_LINES:
                        text_widget.delete("1.0", f"{line_count - MAX_LOG_LINES}.0")
                    text_widget.see(tk.END)

                # Logging can happen from the background conversion thread; Tkinter widgets
                # may only be touched from the main thread, so schedule the update instead
                # of mutating text_widget directly here.
                root.after(0, append)

        gui_handler = GUIHandler()
        gui_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(gui_handler)
    
    def on_input_mode_changed(self) -> None:
        """Handle input mode radio button change."""
        mode = self.input_mode_var.get()
        if mode == "single":
            self.single_frame.grid()
            self.folder_frame.grid_remove()
        else:
            self.single_frame.grid_remove()
            self.folder_frame.grid()
    
    def on_browse_rom_file(self) -> None:
        """Browse for a single ROM file."""
        source_folder = self.output_folder_var.get() or str(self.converter.rom_folder)
        file = filedialog.askopenfilename(
            title="Select ROM File",
            initialdir=source_folder,
            filetypes=[("ROM Files", "*.cia *.cci"), ("All Files", "*.*")]
        )
        if file:
            rom_path = Path(file)
            self.selected_rom_file = rom_path  # ← Store FULL path with directory
            self.rom_name_var.set(rom_path.name)  # ← Display WITH extension
            self.status_var.set(f"Selected: {rom_path.name}")
            logger.info(f"Selected ROM file: {rom_path.name} from {rom_path.parent}")
    
    def on_browse_source_folder(self) -> None:
        """Browse for source folder for batch conversion."""
        folder = filedialog.askdirectory(
            title="Select Folder Containing ROMs",
            initialdir=self.output_folder_var.get() or str(self.converter.rom_folder)
        )
        if folder:
            self.source_folder_var.set(folder)
            self.scan_and_display_folder_contents(folder)
    
    def scan_and_display_folder_contents(self, folder: str) -> None:
        """Scan folder and display file counts and conversion options."""
        folder_path = Path(folder)
        
        # Count files
        cci_files = list(folder_path.glob("*.cci"))
        cia_files = list(folder_path.glob("*.cia"))
        
        cci_count = len(cci_files)
        cia_count = len(cia_files)
        
        # Update counts display
        self.cci_count_label.config(text=f"CCI files: {cci_count}")
        self.cia_count_label.config(text=f"CIA files: {cia_count}")
        
        # Enable/disable conversion options based on file presence
        # CCI → CIA (needs .cci files)
        if cci_count > 0:
            self.convert_cci_to_cia_check.config(state=tk.NORMAL)
            self.convert_cci_to_cia_var.set(True)
        else:
            self.convert_cci_to_cia_check.config(state=tk.DISABLED)
            self.convert_cci_to_cia_var.set(False)
        
        # CIA → CCI (needs .cia files)
        if cia_count > 0:
            self.convert_cia_to_cci_check.config(state=tk.NORMAL)
            self.convert_cia_to_cci_var.set(True)
        else:
            self.convert_cia_to_cci_check.config(state=tk.DISABLED)
            self.convert_cia_to_cci_var.set(False)
        
        # CCI Decrypt (needs .cci files)
        if cci_count > 0:
            self.decrypt_cci_check.config(state=tk.NORMAL)
        else:
            self.decrypt_cci_check.config(state=tk.DISABLED)
            self.decrypt_cci_var.set(False)
        
        # CIA → Decrypted CCI (needs .cia files)
        if cia_count > 0:
            self.cia_to_decrypted_check.config(state=tk.NORMAL)
        else:
            self.cia_to_decrypted_check.config(state=tk.DISABLED)
            self.cia_to_decrypted_var.set(False)
        
        # Update status
        total_roms = cci_count + cia_count
        self.status_var.set(f"Selected folder: {Path(folder).name} ({total_roms} ROM files found)")
        logger.info(f"Selected folder: {folder} (CCI: {cci_count}, CIA: {cia_count})")
    
    def on_browse_output_folder(self) -> None:
        """Browse for output folder."""
        folder = filedialog.askdirectory(
            title="Select Output Folder for Converted ROMs",
            initialdir=self.output_folder_var.get() or str(self.converter.rom_folder)
        )
        if folder:
            self.output_folder_var.set(folder)
            self.status_var.set(f"Output folder: {Path(folder).name}")
            logger.info(f"Output folder set to: {folder}")
    
    def on_convert_clicked(self) -> None:
        """Handle convert button click."""
        if self.running:
            messagebox.showwarning("Running", "Conversion already in progress!")
            return
        
        mode = self.input_mode_var.get()
        output_folder = self.output_folder_var.get().strip()
        
        if not output_folder:
            messagebox.showerror("Error", "Please select an output folder!")
            return
        
        if mode == "single":
            self.handle_single_conversion()
        else:
            self.handle_folder_conversion()
    
    def handle_single_conversion(self) -> None:
        """Handle single ROM conversion."""
        conversion_type_str = self.conversion_var.get()
        
        # If user selected file via browser, use that file
        if self.selected_rom_file and self.selected_rom_file.exists():
            rom_name = self.selected_rom_file.stem  # Get just the filename without extension
            rom_folder = self.selected_rom_file.parent  # Use the file's directory
            logger.info(f"Using selected file: {self.selected_rom_file.name} from {rom_folder}")
        else:
            # Otherwise use manual input
            rom_name = self.rom_name_var.get().strip()
            if not rom_name:
                messagebox.showerror("Input Error", "Please select a ROM file or enter a ROM name!")
                return
            rom_folder = Path(self.output_folder_var.get())
        
        if not conversion_type_str:
            messagebox.showerror("Input Error", "Please select a conversion type!")
            return
        
        conversion_type = next(ct for ct in ConversionType if ct.value == conversion_type_str)
        
        thread = threading.Thread(
            target=self.run_conversion,
            args=(rom_name, conversion_type, rom_folder),
            daemon=True
        )
        thread.start()
    
    def handle_folder_conversion(self) -> None:
        """Handle batch folder conversion."""
        source_folder = self.source_folder_var.get().strip()
        
        if not source_folder:
            messagebox.showerror("Input Error", "Please select a source folder!")
            return
        
        source_path = Path(source_folder)
        if not source_path.exists():
            messagebox.showerror("Error", "Source folder does not exist!")
            return
        
        # Check which conversions user selected
        convert_cci_to_cia = self.convert_cci_to_cia_var.get()
        convert_cia_to_cci = self.convert_cia_to_cci_var.get()
        decrypt_cci = self.decrypt_cci_var.get()
        cia_to_decrypted = self.cia_to_decrypted_var.get()
        
        if not any([convert_cci_to_cia, convert_cia_to_cci, decrypt_cci, cia_to_decrypted]):
            messagebox.showwarning("No Selection", "Please select at least one conversion type!")
            return
        
        # Build list of conversions to perform
        conversions = []
        
        if convert_cci_to_cia:
            cci_files = list(source_path.glob("*.cci"))
            if cci_files:
                rom_names = [f.stem for f in cci_files]
                conversions.append((ConversionType.CCI_TO_CIA, rom_names, len(cci_files)))
        
        if convert_cia_to_cci:
            cia_files = list(source_path.glob("*.cia"))
            if cia_files:
                rom_names = [f.stem for f in cia_files]
                conversions.append((ConversionType.CIA_TO_CCI, rom_names, len(cia_files)))
        
        if decrypt_cci:
            cci_files = list(source_path.glob("*.cci"))
            if cci_files:
                rom_names = [f.stem for f in cci_files]
                conversions.append((ConversionType.CCI_DECRYPT, rom_names, len(cci_files)))
        
        if cia_to_decrypted:
            cia_files = list(source_path.glob("*.cia"))
            if cia_files:
                rom_names = [f.stem for f in cia_files]
                conversions.append((ConversionType.CIA_TO_DECRYPTED, rom_names, len(cia_files)))
        
        if not conversions:
            messagebox.showwarning("No Files", "Selected conversion types have no matching files!")
            return
        
        thread = threading.Thread(
            target=self.run_multi_conversion,
            args=(source_path, conversions),
            daemon=True
        )
        thread.start()
    
    def run_conversion(self, rom_name: str, conversion_type: ConversionType, rom_folder: Path) -> None:
        """Run conversion in background thread."""
        self.running = True
        self._post(self.convert_btn.config, state=tk.DISABLED)
        self._post(self.progress.config, mode='indeterminate')
        self._post(self.progress.start)
        
        try:
            output_folder = Path(self.output_folder_var.get())
            
            original_rom_folder = self.converter.rom_folder
            self.converter.rom_folder = rom_folder
            
            config = ConversionConfig(
                rom_name=rom_name,
                rom_folder=rom_folder,
                conversion_type=conversion_type,
                output_folder=output_folder  # ← Pass output folder to config
            )
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success, message = loop.run_until_complete(self.converter.convert(config))
            loop.close()
            
            self.converter.rom_folder = original_rom_folder
            
            self._post(self.status_var.set, f"{'✓ Success' if success else '✗ Failed'}: {message}")
            
            if success:
                self._post(messagebox.showinfo, "Success", message)
            else:
                self._post(messagebox.showerror, "Error", message)
                
        except Exception as e:
            self._post(self.status_var.set, f"Error: {str(e)}")
            self._post(messagebox.showerror, "Error", f"An error occurred:\n{str(e)}")
        finally:
            self.running = False
            self._post(self.convert_btn.config, state=tk.NORMAL)
            self._post(self.progress.stop)
    
    def run_folder_conversion(self, source_folder: Path, rom_names: list[str], 
                            conversion_type: ConversionType) -> None:
        """Run batch folder conversion in background thread."""
        self.running = True
        self._post(self.convert_btn.config, state=tk.DISABLED)
        total = len(rom_names)
        self._post(self.progress.config, mode='determinate', maximum=max(total, 1), value=0)
        
        try:
            output_folder = Path(self.output_folder_var.get())
            
            # Temporarily change ROM folder
            original_rom_folder = self.converter.rom_folder
            self.converter.rom_folder = source_folder
            
            logger.info(f"Starting batch conversion of {len(rom_names)} files...")
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run conversions
            successful = 0
            for i, rom_name in enumerate(rom_names, 1):
                logger.info(f"Processing {i}/{len(rom_names)}: {rom_name}")
                self._post(self.status_var.set, f"Converting {i}/{total}: {rom_name}")
                
                config = ConversionConfig(
                    rom_name=rom_name,
                    rom_folder=source_folder,
                    conversion_type=conversion_type,
                    output_folder=output_folder  # ← Pass output folder to config
                )
                
                success, message = loop.run_until_complete(self.converter.convert(config))
                if success:
                    successful += 1
                self._post(self.progress.config, value=i)
            
            loop.close()
            
            # Restore original ROM folder
            self.converter.rom_folder = original_rom_folder
            
            message = f"Batch conversion complete: {successful}/{len(rom_names)} successful"
            self._post(self.status_var.set, f"✓ {message}")
            self._post(messagebox.showinfo, "Success", message)
            
        except Exception as e:
            self._post(self.status_var.set, f"Error: {str(e)}")
            self._post(messagebox.showerror, "Error", f"An error occurred during batch conversion:\n{str(e)}")
        finally:
            self.running = False
            self._post(self.convert_btn.config, state=tk.NORMAL)
            self._post(self.progress.config, mode='indeterminate', value=0)
    
    def run_multi_conversion(self, source_folder: Path, conversions: list) -> None:
        """Run multiple conversion types in batch."""
        self.running = True
        self._post(self.convert_btn.config, state=tk.DISABLED)
        overall_total = sum(len(rom_names) for _, rom_names, _ in conversions)
        self._post(self.progress.config, mode='determinate', maximum=max(overall_total, 1), value=0)
        
        try:
            output_folder = Path(self.output_folder_var.get())
            
            # Temporarily change ROM folder
            original_rom_folder = self.converter.rom_folder
            self.converter.rom_folder = source_folder
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            total_successful = 0
            total_count = 0
            overall_progress = 0
            
            # Process each conversion type
            for conversion_type, rom_names, file_count in conversions:
                logger.info(f"\nStarting conversion: {conversion_type.value}")
                logger.info(f"Processing {len(rom_names)} files...")
                
                successful = 0
                for i, rom_name in enumerate(rom_names, 1):
                    logger.info(f"  {i}/{len(rom_names)}: {rom_name}")
                    self._post(self.status_var.set, f"{conversion_type.value}: {i}/{len(rom_names)} - {rom_name}")
                    
                    config = ConversionConfig(
                        rom_name=rom_name,
                        rom_folder=source_folder,
                        conversion_type=conversion_type,
                        output_folder=output_folder
                    )
                    
                    success, message = loop.run_until_complete(self.converter.convert(config))
                    if success:
                        successful += 1
                    overall_progress += 1
                    self._post(self.progress.config, value=overall_progress)
                
                logger.info(f"Completed {conversion_type.value}: {successful}/{len(rom_names)} successful\n")
                total_successful += successful
                total_count += len(rom_names)
            
            loop.close()
            
            # Restore original ROM folder
            self.converter.rom_folder = original_rom_folder
            
            message = f"All conversions complete: {total_successful}/{total_count} files processed successfully"
            self._post(self.status_var.set, f"✓ {message}")
            self._post(messagebox.showinfo, "Success", message)
            
        except Exception as e:
            self._post(self.status_var.set, f"Error: {str(e)}")
            self._post(messagebox.showerror, "Error", f"An error occurred during batch conversion:\n{str(e)}")
        finally:
            self.running = False
            self._post(self.convert_btn.config, state=tk.NORMAL)
            self._post(self.progress.config, mode='indeterminate', value=0)
    
    def on_clear_clicked(self) -> None:
        """Clear input fields."""
        self.rom_name_var.set("")
        self.source_folder_var.set("")
        self.selected_rom_file = None  # Clear selected file
        self.convert_cci_to_cia_var.set(False)
        self.convert_cia_to_cci_var.set(False)
        self.decrypt_cci_var.set(False)
        self.cia_to_decrypted_var.set(False)
        self.cci_count_label.config(text="CCI files: 0")
        self.cia_count_label.config(text="CIA files: 0")
        self.log_text.delete(1.0, tk.END)
        self.status_var.set("Ready")


def main():
    """Main entry point."""
    root = tk.Tk()
    ConverterGUI(root)
    
    # Welcome message
    welcome_msg = """
╔══════════════════════════════════════════════════════╗
║        3DS ROM Converter Pro - Modern Edition        ║
║  Convert CIA/CCI formats and decrypt ROMs for Citra ║
╚══════════════════════════════════════════════════════╝

Credits:
  • 54634564 - decrypt.exe
  • profi200 - makerom.exe, ctrtool.exe
  • matif - Batch CIA 3DS Decryptor.bat
  • @rohithvishaal - Original automation script

Features:
  ✓ Async/concurrent operations for speed
  ✓ Modern GUI interface
  ✓ Real-time logging
  ✓ Better error handling
  ✓ Drag-and-drop ready

Ready to convert ROMs!
"""
    
    logger.info(welcome_msg)
    root.mainloop()


if __name__ == "__main__":
    main()