## Organizing_the_computer_desktop

**桌面整理小工具 (Win10/Win11)**

A lightweight desktop organization assistant written in Python. Features include:

- **One-Click Organization**: Automatically sorts desktop files into subfolders like "Documents", "Images", "Videos", "Music", "Archives", and "Installers" based on file type.
- **GUI (Graphical User Interface)**: Built with Tkinter, featuring a clean, Windows 11-inspired interface.
- **CLI Mode**: Supports organizing specific directories directly from the command line.

---

## Usage

### 1. Prerequisites

- **Operating System**: Windows 10 / Windows 11
- **Python Version**: Python 3.9 or higher recommended
- **Dependencies**: No third-party libraries required; uses only Python standard libraries (including Tkinter).

### 2. Installation / Setup

1. Ensure Python is installed and that `python` or `python3` is available in your terminal.
2. Clone or download this repository to your local machine.

```bash
git clone 
cd Organizing_the_computer_desktop
```

---

## GUI Usage (Recommended)

Run the following command in the project root directory:

```bash
python main.py
```

**Feature Overview:**

- **Target Directory (Default Desktop)**: Automatically detects the current user's desktop path upon launch.
- **Select Folder...**: Allows manual selection of any directory to organize.
- **Start Organizing**: Moves files in the selected directory to corresponding subfolders based on built-in rules.
- **View Rules**: Displays a popup with the current classification rules and file extension lists.
- **Operation Log**: Displays the processing result for each file in the log area below.

> **Note:** The program only organizes files in the current directory and does not recursively process subfolders.

---

## CLI Mode Usage

You can also organize directories via the command line, which is suitable for scripting or scheduled tasks.

### 1) Organize the Default Desktop

```bash
python main.py --cli
```

### 2) Organize a Specific Directory

```bash
python main.py --cli "D:\Some\Folder\Path"
```

---

## Default Classification Rules

The current built-in classifications and extensions include (modifiable in `DEFAULT_RULES` within `main.py`):

- **Documents**: `.doc`, `.docx`, `.pdf`, `.txt`, `.ppt`, `.pptx`, `.xls`, `.xlsx`
- **Images**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.svg`, `.webp`
- **Videos**: `.mp4`, `.avi`, `.mkv`, `.mov`, `.flv`
- **Music**: `.mp3`, `.wav`, `.flac`, `.aac`, `.ogg`
- **Archives**: `.zip`, `.rar`, `.7z`, `.tar`, `.gz`
- **Installers**: `.exe`, `.msi`

**Logic Explanation:**

- Only files in the **current directory** are organized; subdirectories are ignored.
- Files already located in their corresponding category folders are **skipped**.
- If a file with the same name exists in the target folder, a numeric suffix (e.g., `_1`, `_2`) is appended to the filename to prevent overwriting.
- Files that do not match any rule are **kept in the original directory** (and marked in the log).

---

## Future Improvements

- Support for custom classification rules (via config files or UI).
- Support for sorting by date, file size, and other dimensions.
- "Undo" functionality to revert the organization.
