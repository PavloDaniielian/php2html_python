import os
import shutil
import re
import zipfile
import time
import pathlib
from pathlib import Path
from typing import Dict, List
from PyQt6.QtWidgets import (
    QLineEdit, QTextEdit, QMessageBox, QProgressBar, QWidget
)

STR_PHP_CONTENT_START = "start of reseller site"
STR_PHP_CONTENT_END = "end of reseller site"

gnAllFilesNumToProcess = 0
giCurProcessingFile = 0
gnProgresStepsNum = 0
giCurProgresStep = 0
def get_files_count(directory: str) -> int:
    return sum(1 for _ in Path(directory).rglob("*"))
def calcNeedingFilesNumToProcess( n: int, oto1: bool, oto2: bool ):
    global gnAllFilesNumToProcess  # Declare it as global to modify its value
    gnAllFilesNumToProcess += n
    if oto1:
        gnAllFilesNumToProcess += n
    if oto2:
        gnAllFilesNumToProcess += n
    if oto1 and oto2:
        gnAllFilesNumToProcess += n

gProgressObj: QProgressBar = None
def advanceProgress():
    global gProgressObj, gnProgresStepsNum, giCurProgresStep, gnAllFilesNumToProcess, giCurProcessingFile
    giCurProcessingFile += 1
    gProgressObj.setValue( int( 100 * giCurProgresStep / gnProgresStepsNum + 100 / gnProgresStepsNum * giCurProcessingFile / gnAllFilesNumToProcess ) )
def nextProgressStep():
    global gProgressObj, gnProgresStepsNum, giCurProgresStep, giCurProcessingFile
    giCurProgresStep += 1
    giCurProcessingFile = 0
    gProgressObj.setValue( int( 100 * giCurProgresStep / gnProgresStepsNum ) )

gGoingObj: QLineEdit = None
def showGoing( text: str ):
    global gGoingObj
    gGoingObj.setText( text )

gLogObj: QTextEdit = None
def appendLog( text: str ):
    global gLogObj
    gLogObj.append( text )

gMainWinObj: QWidget = None
def showMessage(content: str, title: str = "Fail"):
    msg_box = QMessageBox(gMainWinObj)
    msg_box.setIcon(QMessageBox.Icon.Information)  # Set an information icon
    msg_box.setWindowTitle(title)  # Title of the message box
    msg_box.setText(content)  # Message text
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)  # Add OK button
    msg_box.exec()  # Show the message box


def process_php_file(file_path: str, new_file_path: str, dl:int, product_name: str, tagline: str, classes_to_keep: List, replace_urls: List) -> bool:
    php_file = file_path[file_path.rfind('\\')+1:]
    showGoing( f"Processing {php_file} ...")
    temp_file_path = f"{new_file_path}_temp"
    b_insert = Path(new_file_path).exists()
    if b_insert:
        shutil.copy(new_file_path, temp_file_path)
    try:
        if Path(file_path).exists():
            with open(file_path, "r", encoding="utf-8") as in_file, open(new_file_path, "w", encoding="utf-8") as out_file:
                temp_file = open(temp_file_path, "r", encoding="utf-8") if b_insert else None
                # Insert head part
                if b_insert and temp_file:
                    for line in temp_file:
                        if STR_PHP_CONTENT_START in line:
                            break
                        line = re.sub(r"PRODUCT NAME", product_name, line)
                        line = re.sub(r"TAGLINE", tagline, line)
                        out_file.write(line)
                    for line in temp_file:
                        if STR_PHP_CONTENT_END in line:
                            break
                    for line in in_file:
                        if STR_PHP_CONTENT_START in line:
                            break
                remove_div_tags = 0
                skip_div_tags_to_remove = 0
                oto = 0
                for line in in_file:
                    if b_insert and STR_PHP_CONTENT_END in line:
                        break
                    removed_once = True
                    while removed_once:
                        removed_once = False
                        # Remove special blocks
                        if "if($oto1 == '1')" in line:
                            oto = 1
                            if dl == 0 or dl == 2:
                                for line in in_file:
                                    if "<?php }" in line:
                                        break
                        if "if($oto2 == '1')" in line:
                            oto = 2
                            if dl == 0 or dl == 1:
                                for line in in_file:
                                    if "<?php }" in line:
                                        break
                        # Remove comments
                        t = line.find("<!--")
                        if t != -1:  # Equivalent to `std::string::npos`
                            prefix = line[:t]  # Extract text before comment
                            line = line[t + 4:]  # Remove the `<!--`
                            while True:
                                t = line.find("-->")
                                if t != -1:
                                    line = prefix + line[t + 3:]  # Remove `-->`
                                    removed_once = True
                                    break
                                next_line = next(in_file, None)  # Read next line
                                if next_line is None:  # End of file
                                    break
                                line = next_line  # Update line with next content
                        # Remove PHP blocks
                        t = line.find("<?php")
                        if t != -1:  # Equivalent to `std::string::npos`
                            prefix = line[:t]  # Extract text before comment
                            line = line[t + 5:]  # Remove the `<!--`
                            while True:
                                t = line.find("?>")
                                if t != -1:
                                    line = prefix + line[t + 2:]  # Remove `-->`
                                    removed_once = True
                                    break
                                next_line = next(in_file, None)  # Read next line
                                if next_line is None:  # End of file
                                    break
                                line = next_line  # Update line with next content
                        # Remove script tags
                        t = line.find("<script")
                        if t != -1:  # Equivalent to `std::string::npos`
                            prefix = line[:t]  # Extract text before comment
                            line = line[t + 7:]  # Remove the `<!--`
                            while True:
                                t = line.find("</script>")
                                if t != -1:
                                    line = prefix + line[t + 9:]  # Remove `-->`
                                    removed_once = True
                                    break
                                next_line = next(in_file, None)  # Read next line
                                if next_line is None:  # End of file
                                    break
                                line = next_line  # Update line with next content
                        # Remove specific divs
                        t = line.find('id="noreseller"')
                        if t != -1:  # Equivalent to `std::string::npos`
                            prefix = line[:line.find("<div")]  # Extract text before the <div> tag
                            line = line[t + 15:]  # Remove `id="noreseller"`
                            while True:
                                t1 = line.find("<div")
                                t2 = line.find("</div>")
                                if t1 == -1:
                                    t1 = 1000000
                                if t2 == -1:
                                    t2 = 1000000
                                if t1 < t2:  # Found an opening <div> before closing </div>
                                    skip_div_tags_to_remove += 1
                                    line = line[t1 + 5:]  # Remove <div> tag
                                elif t2 < t1:  # Found a closing </div> before opening <div>
                                    if skip_div_tags_to_remove > 0:
                                        skip_div_tags_to_remove -= 1
                                        line = line[t2 + 6:]  # Remove </div>
                                    else:
                                        line = prefix + line[t2 + 6:]  # Remove the last </div> and exit
                                        removed_once = True
                                        break
                                else:
                                    next_line = next(in_file, None)  # Read next line
                                    if next_line is None:  # End of file
                                        break
                                    line = next_line  # Continue processing
                        # Remove unwanted a tags
                        t = line.find('href="https://warriorplus.com/o2"')
                        if t != -1:  # Equivalent to `std::string::npos`
                            prefix = line[:line.find("<a")]  # Extract text before the <a> tag
                            line = line[t + 15:]
                            while True:
                                t = line.find("</a>")
                                if t != -1:
                                    line = prefix + line[t + 4:]  # Remove closing </a> tag
                                    removed_once = True
                                    break
                                next_line = next(in_file, None)  # Read next line safely
                                if next_line is None:  # End of file
                                    break
                                line = next_line  # Continue processing
                    # Remove .css? lines
                    if ".css?" in line:
                        continue
                    # Handle unwanted divs
                    if '<div class="bg' in line:
                        remove_div_tags += 1
                        next_line = next(in_file, None)
                        if next_line and '<div class="content"' in next_line:
                            remove_div_tags += 1
                            continue
                    if remove_div_tags > 0:
                        if "<div" in line:
                            skip_div_tags_to_remove += 1
                        if "</div>" in line:
                            if skip_div_tags_to_remove > 0:
                                skip_div_tags_to_remove -= 1
                            else:
                                remove_div_tags -= 1
                                continue
                    # Remove animated classes and styles
                    line = re.sub(r'\b(animated|slide-up|slide-down|slide-left|slide-right|zoom)\b', '', line)
                    line = re.sub(r'--speed:\s[0-9]+(\.[0-9]+)?s;?', '', line)
                    # Replace "PRODUCT NAME" -> product_name
                    line = re.sub(r"PRODUCT NAME", product_name, line)
                    # Replace file paths with appropriate versions
                    str_files = "files/" if oto == 0 else "files_oto1/" if oto == 1 else "files_oto2/"
                    for replace_url in replace_urls:
                        line = line.replace(replace_url, str_files)
                    # clean up
                    line = re.sub(r'class="\s*([^"]*?)\s*"', lambda m: f'class="{m.group(1).strip()}"', line)
                    line = re.sub(r'class="\s*"', '', line)
                    line = re.sub(r'style="\s*([^"]*?)\s*"', lambda m: f'style="{m.group(1).strip()}"', line)
                    line = re.sub(r'style="\s*"', '', line)
                    line = re.sub(r'<\s+', '<', line)
                    line = re.sub(r'\s+>', '>', line)
                    # Write modified line if not empty
                    if line.strip():
                        out_file.write(line)
                # Insert foot part
                if b_insert and temp_file:
                    for line in temp_file:
                        line = re.sub(r"PRODUCT NAME", product_name, line)
                        line = re.sub(r"TAGLINE", tagline, line)
                        out_file.write(line)
                    temp_file.close()
        Path(temp_file_path).unlink(missing_ok=True)  # Delete temp file
        return True
    except Exception as e:
        showMessage(f"Error processing PHP file {file_path} : {str(e)}")
        return False

def process_email_file(file_path: str, new_file_path: str, email_links_from: str, email_links_to: str) -> bool:
    email_file = new_file_path[new_file_path.rfind('\\')+1:]
    showGoing( f"Processing {email_file} ...")
    temp_file_path = f"{new_file_path}_temp"
    if Path(new_file_path).exists():
        shutil.copy(new_file_path, temp_file_path)
    try:
        if Path(file_path).exists():
            with open(file_path, "r", encoding="utf-8") as in_file, open(new_file_path, "w", encoding="utf-8") as out_file:
                for line in in_file:
                    lower_line = line.lower()
                    forbidden_phrases = ["resell rights", "re-sell rights", "resale rights", "resellable", "licensing rights"]
                    if any(phrase in lower_line for phrase in forbidden_phrases):
                        continue
                    if "best regards" in lower_line:
                        break
                    line = re.sub(fr"{email_links_from}\S*", email_links_to, line)
                    out_file.write(line)
            temp_file = Path(temp_file_path)
            if temp_file.exists():
                with open(temp_file, "r", encoding="utf-8") as temp_in, open(new_file_path, "a", encoding="utf-8") as out_file:
                    for line in temp_in:
                        out_file.write(line)
                temp_file.unlink()  # Delete the temp file
            appendLog(f"Processed email: {email_file}")
        else:
            appendLog(f"It doesn't exist email source file: {file_path}")
        advanceProgress()
        return True
    except Exception as e:
        showMessage(f"Error processing email {email_file} : {str(e)}")
        return False

def copy_directory(src: str, dst: str) -> bool:
    if not Path(src).exists() :
        return False
    Path(dst).mkdir(parents=True, exist_ok=True)
    for file in Path(src).rglob("*"):
        if file.is_dir():
            Path(dst + "/" + file.name).mkdir(parents=True, exist_ok=True)
        elif file.is_file():
            showGoing( f"Copying {file} directory to {dst}/{file.name} ...")
            shutil.copy2(file, dst + "/" + file.name)
            advanceProgress()
    return True

def delete_uncompressed_files(directory: str):
    for path in Path(directory).rglob("*"):
        if path.is_file() and not path.name.endswith(".zip"):
            path.unlink()
        elif path.is_dir():  # Check if it's a directory
            shutil.rmtree(path, ignore_errors=True)  # Delete folder and contents

def create_zip(zip_path: str, directory: str, filesToZip: List[str]):
    zip_file = Path(zip_path).name  # Extract the ZIP file name
    base_dir = Path(directory).resolve()  # Convert to absolute path
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_dir in filesToZip:
            file_path = base_dir / file_dir  # Convert to full path
            if file_path.is_file():
                showGoing(f"Zipping {file_path.relative_to(base_dir)} to {zip_file} ...")
                zipf.write(file_path, file_path.relative_to(base_dir))
                advanceProgress()
            elif file_path.is_dir():
                for file in file_path.rglob("*"):  # Recursively find all files
                    if file.is_file() and not file.name.endswith(".zip"):  # Exclude ZIPs
                        showGoing(f"Zipping {file.relative_to(base_dir)} to {zip_file} ...")
                        zipf.write(file, file.relative_to(base_dir))
                        advanceProgress()

def start_conversion(php_dir: str, template_dir: str, html_dir: str,
                      product_name: str, tagline:str, classes_to_keep: List,
                      replace_urls: List,
                      email_links_from: str, email_links_to: str,
                      make_zip: bool, zip_name: str, delete_uncompressed: bool,
                      email_map: Dict[str, str], file_copy_array_0: List, file_copy_array_n: List, file_php_array_0: List, file_php_array_n: List, file_html_array_0: List, file_html_array_n: List,
                      mainWin: QWidget, progress: QProgressBar, going: QLineEdit, log_out: QTextEdit ):
    php_dir = Path(php_dir).resolve().as_posix()
    template_dir = Path(template_dir).resolve().as_posix()
    html_dir = Path(html_dir).resolve().as_posix()
    if php_dir == template_dir:
        showMessage("PHP Directory and Template Directory can not be the same.")
        return
    if php_dir == html_dir:
        showMessage("PHP Directory and HTML Directory can not be the same.")
        return
    if template_dir == html_dir:
        showMessage("Template Directory and HTML Directory can not be the same.")
        return
    php_dir = php_dir.replace('/', '\\')
    template_dir = template_dir.replace('/', '\\')
    html_dir = html_dir.replace('/', '\\')
    
    # set global variable
    global gProgressObj
    gProgressObj = progress
    global gGoingObj
    gGoingObj = going
    global gLogObj
    gLogObj = log_out
    global gMainWinObj
    gMainWinObj = mainWin

    # Validate php directory
    showGoing( "Validating php directory ...")
    if not Path(php_dir).exists() or not Path(php_dir).is_dir():
        showMessage("Error: PHP directory does not exist or is not a directory.")
        return
    # remove origin destination directory
    if Path(html_dir).exists():
        showGoing( "Removing origin destination directory ...")
        try:
            shutil.rmtree(html_dir)  # Remove the entire directory
            appendLog(f"HTML directory existed. Removed: {html_dir}")
        except Exception as e:
            showMessage(f"Error: Failed to remove existing HTML directory. {str(e)}")
            return
    # Create new destination directory
    showGoing( "Creating new html directory ...")
    try:
        Path(html_dir).mkdir(parents=True, exist_ok=True)  # Equivalent to fs::create_directories
        appendLog(f"HTML directory created: {html_dir}")
    except Exception as e:
        showMessage(f"Error: Failed to create HTML directory. {str(e)}")
        return
    # Copy template directory to html directory
    showGoing( "Copying template directory to html directory ...")
    try:
        shutil.copytree(template_dir, html_dir, dirs_exist_ok=True)  # Equivalent to fs::copy with recursive & overwrite
        appendLog(f"Copied template directory to HTML directory: {html_dir}")
    except Exception as e:
        showMessage(f"Error: Failed to copy template directory to HTML directory. {str(e)}")
        return
    
    # Determine oto*
    global gnProgresStepsNum, giCurProgresStep
    gnProgresStepsNum = 2 if create_zip else 1
    oto1 = oto2 = False
    if os.path.exists(php_dir+"/oto1.php") or os.path.exists(template_dir+"/oto1.html"):
        oto1 = True
        gnProgresStepsNum += 1 if create_zip else 0
    if os.path.exists(php_dir+"/oto2.php") or os.path.exists(template_dir+"/oto2.html"):
        oto2 = True
        gnProgresStepsNum += 1 if create_zip else 0
    if oto1 and oto2:
        gnProgresStepsNum += 1 if create_zip else 0
    giCurProgresStep = -1
    nextProgressStep()

    # Get the total number of files to process
    showGoing( "Getting the total number of files to process ...")
    global gnAllFilesNumToProcess, giCurProcessingFile
    gnAllFilesNumToProcess = 0
    for sub_dir in file_copy_array_0:
        gnAllFilesNumToProcess += get_files_count(php_dir + "/" + sub_dir)
    gnAllFilesNumToProcess += file_php_array_0.__len__()
    gnAllFilesNumToProcess += email_map.__len__()
    if oto1:
        for sub_dir in file_copy_array_n:
            gnAllFilesNumToProcess += get_files_count(php_dir + "/" + sub_dir + "1")
        gnAllFilesNumToProcess += file_php_array_n.__len__()
    if oto2:
        for sub_dir in file_copy_array_n:
            gnAllFilesNumToProcess += get_files_count(php_dir + "/" + sub_dir + "2")
        gnAllFilesNumToProcess += file_php_array_n.__len__()
    giCurProcessingFile = 0
    
    # Process all files in php directory
    showGoing( "Getting the total number of files to process ...")
    # Copying files
    for sub_dir in file_copy_array_0:
        if copy_directory(php_dir + "/" + sub_dir, html_dir + "/" + sub_dir):
            appendLog(f"Copied {sub_dir} directory")
    if oto1:
        for sub_dir in file_copy_array_n:
            if copy_directory(php_dir + "/" + sub_dir + "1", html_dir + "/" + sub_dir + "1"):
                appendLog(f"Copied {sub_dir}1 directory")
    if oto2:
        for sub_dir in file_copy_array_n:
            if copy_directory(php_dir + "/" + sub_dir + "2", html_dir + "/" + sub_dir + "2"):
                appendLog(f"Copied {sub_dir}2 directory")
    # Processing Email files
    Path(html_dir+"/emails").mkdir(parents=True, exist_ok=True)
    for src_file, dst_file in email_map.items():
        src = os.path.join(php_dir, src_file)
        dst = os.path.join(html_dir, "emails", dst_file)
        if not process_email_file(src, dst, email_links_from, email_links_to):
            return
    # Processing PHP files
    file_php_array = file_php_array_0.copy()
    if oto1:
        for file in file_php_array_n:
            file_php_array.append(file+"1")
    if oto2:
        for file in file_php_array_n:
            file_php_array.append(file+"2")
    for file in file_php_array:
        src = os.path.join(php_dir, file+".php")
        if file == "dl":
            dst = os.path.join(html_dir, "thankyou.html")
            if not process_php_file(src, dst, 0, product_name, tagline, classes_to_keep, replace_urls):
                return
            if oto1:
                dst = os.path.join(html_dir, "thankyou_with_oto1.html")
                if not process_php_file(src, dst, 1, product_name, tagline, classes_to_keep, replace_urls):
                    return
            if oto2:
                dst = os.path.join(html_dir, "thankyou_with_oto2.html")
                if not process_php_file(src, dst, 2, product_name, tagline, classes_to_keep, replace_urls):
                    return
            if oto1 and oto2:
                dst = os.path.join(html_dir, "thankyou_with_oto1_oto2.html")
                if not process_php_file(src, dst, 12, product_name, tagline, classes_to_keep, replace_urls):
                    return
        else:
            dst = os.path.join(html_dir, file + ".html")
            if not process_php_file(src, dst, -1, product_name, tagline, classes_to_keep, replace_urls):
                return
        appendLog(f"Processed php file: {file}.php")
        advanceProgress()
    
    # Zip up the html directory
    if make_zip:
        nFilesToZip0 = file_html_array_0.__len__()
        for sub_dir in file_copy_array_0:
            nFilesToZip0 += get_files_count(html_dir + "/" + sub_dir)
        file_zip_array0 = file_copy_array_0.copy()
        for file in file_html_array_0:
            file_zip_array0.append(file + ".html")
        zip_file = f"{zip_name.replace(' ', '')}_RR"
        zip_filepath = html_dir + "/" + zip_file
            # Zip up RR
        nextProgressStep()
        gnAllFilesNumToProcess = nFilesToZip0
        create_zip(zip_filepath + ".zip", html_dir, file_zip_array0)
        appendLog(f"Zipped up the html directory to {zip_file}.zip")
            # Zip up RR1
        nextProgressStep()
        nFilesToZip1 = file_html_array_n.__len__()
        for sub_dir in file_copy_array_n:
            nFilesToZip1 += get_files_count(html_dir + "/" + sub_dir + "1")
        gnAllFilesNumToProcess = nFilesToZip0 + nFilesToZip1
        file_zip_array1 = file_zip_array0.copy()
        for file in file_copy_array_n:
            file_zip_array1.append(file + "1")
        for file in file_html_array_n:
            file_zip_array1.append(file + "1.html")
        create_zip(zip_filepath + "OTO1.zip", html_dir, file_zip_array1)
        appendLog(f"Zipped up the html directory to {zip_file}OTO1.zip")
            # Zip up RR2
        nextProgressStep()
        nFilesToZip2 = file_html_array_n.__len__()
        for sub_dir in file_copy_array_n:
            nFilesToZip2 += get_files_count(html_dir + "/" + sub_dir + "2")
        gnAllFilesNumToProcess = nFilesToZip0 + nFilesToZip2
        file_zip_array2 = file_zip_array0.copy()
        for file in file_copy_array_n:
            file_zip_array2.append(file + "2")
        for file in file_html_array_n:
            file_zip_array2.append(file + "2.html")
        create_zip(zip_filepath + "OTO2.zip", html_dir, file_zip_array2)
        appendLog(f"Zipped up the html directory to {zip_file}OTO2.zip")
            # Zip up RR12
        nextProgressStep()
        gnAllFilesNumToProcess = nFilesToZip0 + nFilesToZip1 + nFilesToZip2 + 1
        file_zip_array12 = file_zip_array1.copy()
        for file in file_copy_array_n:
            file_zip_array12.append(file + "2")
        for file in file_html_array_n:
            file_zip_array12.append(file + "2.html")
        file_zip_array12.append("thankyou_with_oto1_oto2.html")
        create_zip(zip_filepath + "OTO12.zip", html_dir, file_zip_array12)
        appendLog(f"Zipped up the html directory to {zip_file}OTO12.zip")

        # delete_uncompressed
        if delete_uncompressed:
            delete_uncompressed_files( html_dir )
            appendLog(f"Deleted uncompressed files")

    # complete
    nextProgressStep()
    showGoing( "Conversion completed successfully!")
    showMessage("Conversion completed successfully!", "Success")
    return
