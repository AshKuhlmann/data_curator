import pytest
import tkinter as tk
from unittest.mock import patch
import os
import shutil
import tempfile
from data_curator_app.main import DataCuratorApp


@pytest.fixture
def app():
    """Pytest fixture to create and tear down the DataCuratorApp."""
    # Set up a temporary directory for the test repository
    test_dir = tempfile.mkdtemp()

    # Create some dummy files
    with open(os.path.join(test_dir, "file1.txt"), "w") as f:
        f.write("hello")
    with open(os.path.join(test_dir, "image.png"), "w") as f:
        f.write("fake image data")
    with open(os.path.join(test_dir, "document.pdf"), "w") as f:
        f.write("fake pdf data")

    # Create the app instance
    app = DataCuratorApp()

    # Yield the app and the test directory to the test function
    yield app, test_dir

    # Teardown: destroy the app window and remove the temp directory
    app.destroy()
    shutil.rmtree(test_dir)


def test_select_repository(app):
    """Test selecting a repository and loading files."""
    app_instance, test_dir = app

    # Mock the filedialog to return our test directory
    with patch("tkinter.filedialog.askdirectory", return_value=test_dir):
        app_instance.select_repository()

    # Allow the event loop to process
    app_instance.update_idletasks()
    app_instance.update()

    # Check that the file listbox is populated
    listbox_items = app_instance.file_listbox.get(0, tk.END)

    # The dummy files we created in the fixture
    expected_files = ["document.pdf", "file1.txt", "image.png"]

    # The order might vary, so we sort both lists to compare
    assert sorted(list(listbox_items)) == sorted(expected_files)

    # Check that the repository path label is updated
    assert test_dir in app_instance.repo_label.cget("text")


def test_rename_file(app):
    """Test renaming a file by directly setting the app state."""
    app_instance, test_dir = app

    # First, select the repository to populate the file list
    with patch("tkinter.filedialog.askdirectory", return_value=test_dir):
        app_instance.select_repository()
    app_instance.update_idletasks()
    app_instance.update()

    # Find the index of the file to rename in the app's internal file list
    try:
        # Sort the file list to have a predictable order for testing
        app_instance.file_list.sort()
        pdf_index = app_instance.file_list.index("document.pdf")
    except ValueError:
        pytest.fail("Could not find 'document.pdf' in the app's file_list")

    # Directly set the application's state, bypassing unreliable UI interaction
    app_instance.current_file_index = pdf_index

    # Mock the simpledialog to return a new name
    new_name = "renamed_document.pdf"
    with patch("tkinter.simpledialog.askstring", return_value=new_name):
        app_instance.rename_current_file()

    app_instance.update_idletasks()
    app_instance.update()

    # Check that the file is renamed on the filesystem
    old_file_path = os.path.join(test_dir, "document.pdf")
    new_file_path = os.path.join(test_dir, new_name)
    assert not os.path.exists(old_file_path)
    assert os.path.exists(new_file_path)

    # Check that the listbox is updated
    listbox_items = app_instance.file_listbox.get(0, tk.END)
    assert new_name in listbox_items
    assert "document.pdf" not in listbox_items


def test_delete_and_undo_file(app):
    """Test deleting a file and then undoing the deletion."""
    app_instance, test_dir = app

    # Load repository and prepare state
    with patch("tkinter.filedialog.askdirectory", return_value=test_dir):
        app_instance.select_repository()
    app_instance.update_idletasks()
    app_instance.update()

    # State preparation for the file to be deleted
    file_to_delete = "file1.txt"
    try:
        # Sort for predictability
        app_instance.file_list.sort()
        file_index = app_instance.file_list.index(file_to_delete)
    except ValueError:
        pytest.fail(f"Could not find '{file_to_delete}' in the app's file_list")

    app_instance.current_file_index = file_index
    original_path = os.path.join(test_dir, file_to_delete)

    # Mock the confirmation dialog and delete the file
    with patch("tkinter.messagebox.askyesno", return_value=True):
        app_instance.delete_current_file()

    app_instance.update_idletasks()
    app_instance.update()

    # Verify deletion
    assert not os.path.exists(original_path)
    assert file_to_delete not in app_instance.file_listbox.get(0, tk.END)

    # Undo the deletion
    app_instance.undo_last_action()
    app_instance.update_idletasks()
    app_instance.update()

    # Verify restoration
    assert os.path.exists(original_path)
    assert file_to_delete in app_instance.file_listbox.get(0, tk.END)
