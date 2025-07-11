Data CuratorData Curator is a smart, visual tool designed to help you organize, declutter, and take control of your digital files. Stop letting downloads, documents, and project folders descend into chaos. Review, decide, and act with an intuitive interface.A preview of the Data Curator interface in action.The ProblemWe all have them: the "Downloads" folder filled with files from months ago, the "Desktop" littered with temporary screenshots, the "Projects" directory with old assets. Sifting through this digital clutter is tedious. Data Curator turns this chore into a quick and even satisfying process.Key FeaturesVisual File Curation: Select a folder (your "repository") and Data Curator presents you with one file at a time, so you can focus and make decisions without being overwhelmed.Intelligent Scanning: The app cleverly remembers which files you've already curated, so you only review new or previously postponed items.Powerful Actions: For each file, you can:Keep (Forever): Mark the file as important and permanent.Keep (Temporary): Keep the file for a configurable period (e.g., 90 days). The app will notify you when it expires!Rename: Quickly give the file a more meaningful name.Open Location: Instantly open the file's containing folder in your system's file explorer.Decide Later: Skip the file for now. It will be presented to you again in a future session.Delete: Securely and permanently delete the file after a confirmation.Rich File Previews: No need to open every file to know what it is. Data Curator features a large preview pane with support for:Images: png, jpg, gif, bmp, etc.Text Files: txt, md, log, etc.PDF Documents: View PDFs directly within the app.Tabular Data: Renders .csv files in a clean, readable table.Source Code: Displays code with syntax highlighting for dozens of languages.Undo Your Last Action: Accidentally deleted a file? No problem. A simple undo feature lets you reverse your last decision.Expiry Notifications: On startup, the app checks for any temporarily kept files whose time is up and asks you what you'd like to do with them.Persistent State: All your decisions are saved locally in a simple json file, giving you a complete record of your curation activities.Cross-Platform: Built with Python and its standard libraries, Data Curator runs on Windows, macOS, and Linux.InstallationYou can get Data Curator up and running in two ways:1. Using the Executable (Recommended for most users)Go to the Releases page of this repository.Download the appropriate executable for your operating system (.exe for Windows, .app for macOS, or the binary for Linux).No installation is needed. Just run the downloaded file.2. Running from Source (For developers)If you want to run the latest development version or contribute to the project:# 1. Clone the repository
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
How to UseLaunch Data Curator.Click "Select Repository" and choose a folder you want to clean up.The first un-curated file will be loaded into the list and its preview will be shown.Use the action buttons at the bottom of the window to process the file.The app will automatically move to the next file. Continue until the review list is empty.Close the app at any time. Your progress is always saved.ContributingContributions are welcome! Whether it's a bug report, a feature request, or a pull request, your input is valued. Please feel free to open an issue to discuss your ideas.If you'd like to contribute code:Fork the repository.Create a new branch for your feature (git checkout -b feature/AmazingFeature).Commit your changes (git commit -m 'Add some AmazingFeature').Push to the branch (git push origin feature/AmazingFeature).Open a Pull Request.LicenseThis project is licensed under the GNU General Public License v3.0. See the LICENSE file for more details. This means you are free to use, study, share, and modify the software.

## Building an Executable

1. **Add PyInstaller**
   Add PyInstaller as a development dependency so it isn't included in the final package:

   ```bash
   poetry add pyinstaller --group dev
   ```

2. **Run the Packaging Command**
   Run this from the project root to bundle the app:

   ```bash
   poetry run pyinstaller --onefile --windowed --name DataCurator data_curator_app/main.py
   ```

   - `--onefile`: Creates a single executable file.
   - `--windowed`: Prevents a black console window from appearing.
   - `--name DataCurator`: Sets the name of your final executable.
   - `data_curator_app/main.py`: Entry point of the application.

After the command finishes, the executable will be available in the `dist` folder. You can now share that single file with others!
