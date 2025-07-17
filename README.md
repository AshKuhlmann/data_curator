# Data Curator

Data Curator is a visual tool for cleaning up your folders one file at a time. It remembers what you have already reviewed and supports common file types such as images, text, PDF documents and more. Files can be kept permanently, kept temporarily with an expiry date, renamed, opened in your file browser, skipped for later or deleted. The state of your decisions is saved locally so you can resume where you left off.

## Key Features

- **Visual file curation**: Review items individually with a large preview pane.
- **Intelligent scanning**: Previously curated files are skipped so you only see new or postponed items.
- **Rich previews**: Supports images, text files, PDFs, CSV tables and syntax highlighted code.
- **Powerful actions**: Keep forever, keep temporarily, rename, open location, decide later or delete.
- **Undo support**: Reverse your last action if you make a mistake.
- **Expiry notifications**: The app notifies you when temporary files expire.
- **Cross platform**: Works on Windows, macOS and Linux.

## Installation

### Using a released executable

Visit the project Releases page and download the executable for your operating system. No additional installation is required—just run the downloaded file.

### Running from source

```bash
# 1. Clone the repository
git clone https://github.com/your-username/data-curator.git
cd data-curator

# 2. Create and activate a virtual environment
python -m venv venv
# On Windows: venv\Scripts\activate
# On macOS/Linux: source venv/bin/activate

# 3. Install the required dependencies
pip install -r requirements.txt

# 4. Run the application
python data_curator_app.py
```

## How to Use

1. Launch **Data Curator**.
2. Click **Select Repository** and choose the folder you want to tidy.
3. Use the action buttons at the bottom of the window to process each file.
4. Continue until the review list is empty. Your progress is saved automatically.

## Contributing

Contributions are welcome! Please open an issue to discuss your ideas. If you would like to submit code:

1. Fork the repository and create a branch for your feature.
2. Commit your changes and push the branch.
3. Open a pull request.

## License

This project is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for details.

## Building an Executable

To generate a standalone executable with PyInstaller:

1. Add PyInstaller as a development dependency:

```bash
poetry add pyinstaller --group dev
```

2. Run the packaging command from the project root:

```bash
poetry run pyinstaller --onefile --windowed --name DataCurator data_curator_app/main.py
```

- `--onefile` creates a single executable file.
- `--windowed` prevents a console window from appearing.
- `--name DataCurator` sets the name of the final executable.
- `data_curator_app/main.py` is the entry point of the application.

The resulting file will be located in the `dist` folder and can be shared with others.
