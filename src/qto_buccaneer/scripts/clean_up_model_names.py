import os
import sys

def clean_up_files(folder_path):
    # First pass: Delete files without "(Edited)"
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            if "(EDITED)" not in filename:
                try:
                    os.remove(file_path)
                    print(f"Deleted: {filename}")
                except Exception as e:
                    print(f"Error deleting {filename}: {str(e)}")

    # Second pass: Rename files by removing " (Edited)"
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            if " (EDITED)" in filename:
                new_filename = filename.replace(" (EDITED)", "")
                new_file_path = os.path.join(folder_path, new_filename)
                try:
                    os.rename(file_path, new_file_path)
                    print(f"Renamed: {filename} -> {new_filename}")
                except Exception as e:
                    print(f"Error renaming {filename}: {str(e)}")

if __name__ == "__main__":
    #if len(sys.argv) != 2:
    #    print("Usage: python clean_up_model_names.py <folder_path>")
    #    sys.exit(1)
    #
    folder_path = "projects/Seefeld__private/all_models__private"
    if not os.path.isdir(folder_path):
        print(f"Error: {folder_path} is not a valid directory")
        sys.exit(1)
    
    clean_up_files(folder_path)

