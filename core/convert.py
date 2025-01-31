import os
import shutil
import re
import zipfile
import pathlib
from pathlib import Path
from typing import Dict

MAX_EMAILS_NUM = 7
STR_PHP_CONTENT_START = "start of reseller site"
STR_PHP_CONTENT_END = "end of reseller site"

def trim(text: str) -> str:
    return text.strip()

def get_files_count(directory: str) -> int:
    return sum(1 for _ in Path(directory).rglob("*"))

def process_php_file(file_path: str, new_file_path: str, product_name: str, classes_to_keep: str, replace_dir: str):
    with open(file_path, "r", encoding="utf-8") as infile, open(new_file_path, "w", encoding="utf-8") as outfile:
        inside_reseller_section = False
        for line in infile:
            if STR_PHP_CONTENT_START in line:
                inside_reseller_section = True
                continue
            if STR_PHP_CONTENT_END in line:
                inside_reseller_section = False
                continue
            if inside_reseller_section:
                # Replace product name
                line = re.sub(r"PRODUCT NAME", product_name, line)
                # Replace download links
                line = re.sub(rf"https://supersalesmachine.s3.amazonaws.com/members/{replace_dir}/", "files/", line)
            outfile.write(line)

def process_email_file(file_path: str, new_file_path: str, your_link: str):
    with open(file_path, "r", encoding="utf-8") as infile, open(new_file_path, "w", encoding="utf-8") as outfile:
        for line in infile:
            #line = re.sub(r"https://www.supersalesmachine.com/[^"]*", your_link, line)
            outfile.write(line)

def copy_files(src: str, dst: str):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

def delete_uncompressed_files(directory: str):
    for path in Path(directory).rglob("*"):
        if path.is_file() and not path.name.endswith(".zip"):
            path.unlink()

def create_zip(zip_path: str, directory: str):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in Path(directory).rglob("*"):
            zipf.write(file, file.relative_to(directory))

def start_conversion(php_dir: str, template_dir: str, html_dir: str, product_name: str, classes_to_keep: str,
                      replace_dir: str, email_map: Dict[str, str], your_link: str, delete_uncompressed: bool):
    if not os.path.exists(php_dir):
        print("Error: PHP directory does not exist.")
        return
    if os.path.exists(html_dir):
        shutil.rmtree(html_dir)
    copy_files(template_dir, html_dir)
    for email_file, destination_file in email_map.items():
        process_email_file(os.path.join(php_dir, email_file), os.path.join(html_dir, "emails", destination_file), your_link)
    for file in Path(php_dir).rglob("*.php"):
        new_path = os.path.join(html_dir, file.name.replace(".php", ".html"))
        process_php_file(str(file), new_path, product_name, classes_to_keep, replace_dir)
    create_zip(os.path.join(html_dir, f"{product_name.replace(' ', '_')}.zip"), html_dir)
    if delete_uncompressed:
        delete_uncompressed_files(html_dir)
    print("Conversion completed successfully!")
