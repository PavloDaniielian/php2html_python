import sys
import os
import configparser
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit, QHBoxLayout, QVBoxLayout, QFrame, QCheckBox, QFileDialog, QProgressBar, QTextEdit, QGridLayout, QToolButton, QToolTip,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt  # Fix: Ensure Qt is imported
from core.convert import start_conversion
from pathlib import Path
import re
from typing import List, Dict, Tuple
import time

# Configuration file handling
CONFIG_FILE = "settings.ini"
MAX_EMAILS_NUM = 7

def load_config():
    config = configparser.ConfigParser()
    default_settings = {
        "phpDir": "D:\\Work\\Upwork\\20250127\\converting",
        "templateDir": "D:\\Work\\Upwork\\20250127\\template",
        "htmlDir": "D:\\Work\\Upwork\\20250127\\converting\\_HTML RESELLERS",
        "productName": "HealthSupplementNewsletters",
        "classesToKeep": "staatliches",
        "replaceDir": "health",
        "replaceLinks": "https://supersalesmachine.s3.amazonaws.com/members/health/\nhttps://www.supersalesmachine.com/a/health/files/\nhttps://www.supersalesmachine.com/o/health/files/",
        "emailLinksFrom": "https://www.supersalesmachine.com/",
        "emailLinksTo": "YOUR LINK",
        "createZipFiles": "true",
        "deleteUncompressedFiles": "false",
    }
    if not os.path.exists(CONFIG_FILE):
        save_config(default_settings)
    else:
        config.read(CONFIG_FILE)
        return {key: config.get("DEFAULT", key, fallback=value) for key, value in default_settings.items()}
    return default_settings

def save_config(settings):
    config = configparser.ConfigParser()
    config["DEFAULT"] = settings
    with open(CONFIG_FILE, "w") as configfile:
        config.write(configfile)

class HelpPopup(QWidget):
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # Ensures no unwanted white space
        # Apply only outer border and remove extra margins
        self.setStyleSheet("""
            background-color: white;
            border: 1px solid black;  /* Ensures only outer border */
            padding: 5px;
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # Removes extra margins
        layout.setSpacing(0)  # Ensures no unwanted spacing
        label = QLabel(message, self)
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.PlainText)  # Ensure plain text
        label.setStyleSheet("font-size: 14px;")  # ✅ Set font size to 14px
        layout.addWidget(label)

# Main Window Class
class ConverterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PHP to HTML Site Converter")
        self.setGeometry(200, 30, 1200, 900)
        self.config = load_config()
        self.popups = []  # Track open popups
        self.initUI()

    def detect_emails(self):
        php_dir = self.php_input.text().strip()
        for i_email in range(MAX_EMAILS_NUM):
            self.source_emails[i_email].setText("")
            self.destination_emails[i_email].setText("")
        i_email = 0
        if not Path(php_dir).exists():
            return
        for entry in Path(php_dir).iterdir():
            new_file = entry.name
            if entry.is_dir():
                continue
            if "broadcast" not in new_file:
                continue
            self.source_emails[i_email].setText(new_file)
            self.destination_emails[i_email].setText(f"broadcast{i_email+1}.txt")
            i_email += 1
            if i_email >= MAX_EMAILS_NUM:
                break
            with open(entry, "r", encoding="utf-8") as file:
                email_content = file.read()
            match = re.search(r"\s*(https://[^/]+\.com/)", email_content)
            if match:
                self.email_links_from_input.setText( match.group(1) )

    def detect_phpVariable(self):
        file_path = f"{self.php_input.text().strip()}/config.php"
        if not Path(file_path).exists():
            return
        with open(file_path, "r", encoding="utf-8") as file:
            php_code = file.read()
        match = re.search(r"\$pname\s*=\s*['\"](.*?)['\"];", php_code)
        if match:
            self.product_input.setText( match.group(1) )

    def detect_replacing(self):
        file_path = f"{Path(self.php_input.text()).resolve().as_posix()}/dl.php"
        if not Path(file_path).exists():
            return
        with open(file_path, "r", encoding="utf-8") as file:
            dir = ""
            urls = []
            bDetect = False
            for line in file:
                if line.find("$main == '1'") != -1 or line.find("$oto1 == '1'") != -1 or line.find("$oto2 == '1'") != -1:
                    bDetect = True
                if bDetect:
                    if line.find("<?php }") != -1:
                        break
                    if line.find("href=\"https://") != -1:
                        match = re.search(r'href\s*=\s*["\']([^"\']+)["\']', line)
                        if match:
                            url = match.group(1)
                            url = url[:url.rfind("/")+1]
                            if url not in urls:
                                urls.append(url[:url.rfind("/")+1])
                                if url[url.__len__()-7:] == "/files/" :
                                    url = url[:url.__len__()-7]
                                    dir = url[url.rfind("/")+1:]
                                else:
                                    url = url[:url.__len__()-1]
                                    dir = url[url.rfind("/")+1:]
            self.replace_urls.setText("")
            for url in urls:
                self.replace_urls.append(url)
            self.replace_input.setText(dir)
    
    def detect_zipName(self):
        zipName = self.product_input.text().replace(" ","")
        self.zip_input.setText(zipName)

    def initUI(self):
        layout = QVBoxLayout()

        help_messages = {
            "PHP Directory :": "This is the source site that contains PHP files, images and broadcast emails. File contents will be copied over to reseller's HTML site and processed. Use tags <?php // start of reseller site; ?> and <?php // end of reseller site; ?> to define content to copy over to reseller's HTML site.",
            "Template Directory :": "This is the HTML reseller base template that will be copied over to the reseller's HTML site folder. You can create multiple base templates with different headers, footers, styles and layouts. Use tags <!-- start of reseller site --> and  <!-- end of reseller site --> to define where content should be added.",
            "HTML Directory :": "This is the reseller's HTML directory where files from the \"PHP Directory\" and \"Template Directory\" are combined. This is usually located within a folder in the PHP Directory to keep things organized.",
            "Product Name :": "This will replace any instances of \"PRODUCT NAME\" in the reseller's HTML site with the one you specify. In most cases it replaces the title tag and footer text.",
            "Classes to Keep :": "This defines which custom style classes should be kept in the reseller's HTML site. For example the original h1 tag may contain custom fonts like <h1 class=\"staatliches\">Title</h1>. If \"staatliches\" is defined, then the h1 tag remains the same. If nothing is defined, then tag is stripped and becomes <h1>Title</h1>",
            "Replace Dir (detected) :": "Defines the Amazon S3 URL to strip. Performs find and replace and only adds folder and filename download link to all thankyou*.html pages. For example \"https://supersalesmachine.s3.amazonaws.com/members/supercashsavers/file.zip\" becomes \"files/file.zip\". Reseller then uploads zip files to corresponding folders. ",
            "Assign Emails :": "Looks for all broadcast emails in PHP Directory and allows you to choose which ones to use for reseller's site. Example if you have a series of broadcast*.txt emails, but broadcast3.txt is gift email, you can assign broadcast3.txt to not be copied over.",
            "Replace Email Links :": "This searches for all instances of URLs that start with a specific string, then replaces the line with YOUR LINK or a custom tag. Any email signatures from the source site will be removed. To add new signatures, simply customize the HTML template emails."
        }

        def create_directory_section(label_text, default_path):
            help_message = help_messages[label_text]
            help_button = QToolButton()
            help_button.setText("?")
            help_button.setFixedSize(20, 20)
            help_button.clicked.connect(lambda: self.show_help(help_message, help_button))
            help_message_forTooltip = help_message.replace("<", "&lt;").replace(">", "&gt;")
            layout = QHBoxLayout()
            label = QLabel(label_text)
            label.setFixedWidth(123)
            label.setToolTip(help_message_forTooltip)
            edit = QLineEdit(default_path)
            edit.setToolTip(help_message_forTooltip)
            browse_button = QPushButton("...")
            browse_button.setFixedWidth(30)
            browse_button.clicked.connect(lambda: self.browse_folder(edit))
            
            layout.addWidget(label)
            layout.addWidget(help_button)
            layout.addWidget(edit)
            layout.addWidget(browse_button)
            return layout, edit
        
        def create_text_section(label_text, default_value):
            help_message = help_messages[label_text]
            help_button = QToolButton()
            help_button.setText("?")
            help_button.setFixedSize(20, 20)
            help_button.clicked.connect(lambda: self.show_help(help_message, help_button))
            help_message_forTooltip = help_message.replace("<", "&lt;").replace(">", "&gt;")
            layout = QHBoxLayout()
            label = QLabel(label_text)
            label.setFixedWidth(123)
            label.setToolTip(help_message_forTooltip)
            label.setTextFormat(Qt.TextFormat.PlainText)  # Force plain text rendering
            edit = QLineEdit(default_value)
            edit.setToolTip(help_message_forTooltip)
            
            layout.addWidget(label)
            layout.addWidget(help_button)
            layout.addWidget(edit)
            return layout, edit
        
        def create_text_texts_section(label_text1, default_value1, label_text2, default_value2):
            help_message = help_messages[label_text1]
            layout = QHBoxLayout()
            label1 = QLabel(label_text1)
            label1.setFixedWidth(123)
            label1.setToolTip(help_message)
            label1.setTextFormat(Qt.TextFormat.PlainText)  # Force plain text rendering
            help_button = QToolButton()
            help_button.setText("?")
            help_button.setFixedSize(20, 20)
            help_button.clicked.connect(lambda: self.show_help(help_message, help_button))
            edit1 = QLineEdit(default_value1)
            edit1.setMaximumWidth(200)
            label2 = QLabel(label_text2)
            edit2 = QTextEdit("")
            edit2.setMaximumHeight(70)
            for text in [cls.strip() for cls in default_value2.split("\n") if cls.strip()]:
                edit2.append(text)
            
            layout.addWidget(label1, alignment=Qt.AlignmentFlag.AlignTop)
            layout.addWidget(help_button, alignment=Qt.AlignmentFlag.AlignTop)
            layout.addWidget(edit1, alignment=Qt.AlignmentFlag.AlignTop)
            layout.addWidget(label2, alignment=Qt.AlignmentFlag.AlignTop)
            layout.addWidget(edit2)
            return layout, edit1, edit2
        
        def create_text2_section(label_text, label_text1, default_value1, label_text2, default_value2):
            help_message = help_messages[label_text]
            layout = QHBoxLayout()
            label = QLabel(label_text)
            label.setFixedWidth(123)
            label.setToolTip(help_message)
            label.setTextFormat(Qt.TextFormat.PlainText)  # Force plain text rendering
            help_button = QToolButton()
            help_button.setText("?")
            help_button.setFixedSize(20, 20)
            help_button.clicked.connect(lambda: self.show_help(help_message, help_button))
            label1 = QLabel(label_text1)
            edit1 = QLineEdit(default_value1)
            label2 = QLabel(label_text2)
            edit2 = QLineEdit(default_value2)
            
            layout.addWidget(label)
            layout.addWidget(help_button)
            layout.addWidget(label1)
            layout.addWidget(edit1)
            layout.addWidget(label2)
            layout.addWidget(edit2)
            return layout, edit1, edit2
        
        # PHP, Template, and HTML Directories
        php_layout, self.php_input = create_directory_section("PHP Directory :", self.config["phpDir"])
        template_layout, self.template_input = create_directory_section("Template Directory :", self.config["templateDir"])
        html_layout, self.html_input = create_directory_section("HTML Directory :", self.config["htmlDir"])
        self.php_input.textChanged.connect(lambda: self.onChange_PhpDir())
        
        # Product Name, Classes, Replace Dir
        product_layout, self.product_input = create_text_section("Product Name :", self.config["productName"])
        self.product_input.textChanged.connect(lambda: self.onChange_ProductName())
        classes_layout, self.classes_input = create_text_section("Classes to Keep :", self.config["classesToKeep"])
        replace_layout, self.replace_input, self.replace_urls = create_text_texts_section("Replace Dir (detected) :", self.config["replaceDir"], "Replaces URLs :", self.config["replaceLinks"])
        self.replace_input.textChanged.connect(lambda: self.onChange_ReplaceDir())
        
        # Assign Emails Section
        email_layout = QGridLayout()

        help_message = help_messages["Assign Emails :"]
        label = QLabel("Assign Emails :")
        label.setToolTip(help_message.replace("<", "&lt;").replace(">", "&gt;"))
        email_layout.addWidget(label, 0, 1)
        help_button = QToolButton()
        help_button.setText("?")
        help_button.setFixedSize(20, 20)
        help_button.clicked.connect(lambda: self.show_help(help_message, help_button))
        email_layout.addWidget(help_button, 0, 2)
        
        email_layout.addWidget(QLabel("Source Site Emails (detected)"), 0, 3)
        email_layout.addWidget(QLabel("Client's Destination Emails (emails/*.txt)"), 0, 5)
        self.source_emails = []
        self.destination_emails = []
        email_layout.setColumnMinimumWidth(1, 123)
        email_layout.setColumnMinimumWidth(2, 0)
        email_layout.setColumnMinimumWidth(4, 60)
        
        for i in range(MAX_EMAILS_NUM):
            email_label = QLabel(f"Email {i+1}:")
            email_layout.addWidget(email_label, i+1, 1, 1, 2, Qt.AlignmentFlag.AlignRight)
            email_label.setFixedWidth(60)
            source_email = QLineEdit()
            dest_email = QLineEdit()
            self.source_emails.append(source_email)
            self.destination_emails.append(dest_email)
            email_layout.addWidget(source_email, i+1, 3)
            email_layout.addWidget(QLabel("====>"), i+1, 4, Qt.AlignmentFlag.AlignCenter)
            email_layout.addWidget(dest_email, i+1, 5)
        
        # Email Links
        email_links_layout, self.email_links_from_input, self.email_links_to_input = create_text2_section("Replace Email Links :", "    Search for URLs starting with", self.config["emailLinksFrom"], "    Replace URLs with", self.config["emailLinksTo"])
        
        # zip section
        zip_frame = QFrame(self)
        zip_frame.setFixedSize(750, 30)
        self.createZip_checkbox = QCheckBox("Create ZIP Files", zip_frame)
        self.createZip_checkbox.setChecked(self.config["createZipFiles"] == "true")
        zip_label = QLabel(f"Zip Filename:", zip_frame)
        zip_label.move( 150, 2 )
        self.zip_input = QLineEdit("Product Name", zip_frame)
        self.zip_input.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.zip_input.setGeometry( 230, 0, 250, 20 )
        zipSuffix_label = QLabel(f"_RR.zip", zip_frame)
        zipSuffix_label.move( 483, 2 )
        self.delete_checkbox = QCheckBox("Delete Uncompressed Files", zip_frame)
        self.delete_checkbox.setChecked(self.config["deleteUncompressedFiles"] == "true")
        self.delete_checkbox.move( 580, 0 )
        
        # auto type
        self.detect_emails()
        self.detect_phpVariable()
        self.detect_replacing()
        self.detect_zipName()
        
        # Convert Button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.convert_button = QPushButton("Create Site")
        self.convert_button.setFixedSize(200, 40)
        self.convert_button.clicked.connect(self.start_conversion)
        button_layout.addWidget(self.convert_button)
        button_layout.addStretch()
        
        # Progress Bar with Label
        progress_layout = QHBoxLayout()
        progress_label = QLabel("Progress :")
        self.progress = QProgressBar()
        self.progress.setStyleSheet("""
            QProgressBar {
                border-radius: 5px;
                background-color: lightgrey;
                text-align: center;
                font-size: 16px;
            }
            QProgressBar::chunk {
                width: 5px;
            }
        """)
        progress_layout.addWidget(progress_label)
        progress_layout.addWidget(self.progress)
        
        # Log Output
        self.going = QLabel("Ready to create a site...")
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        
        # Add widgets to layout
        for section in [php_layout, template_layout, html_layout, product_layout, classes_layout, replace_layout]:
            layout.addLayout(section)
        layout.addLayout(email_layout)
        layout.addLayout(email_links_layout)
        layout.addWidget(zip_frame)
        layout.addLayout(button_layout)
        layout.addLayout(progress_layout)
        layout.addWidget(self.going)
        layout.addWidget(self.log_output)
        layout.setSpacing(10)
        
        self.setLayout(layout)
        QToolTip.setFont( QFont("Arial",11) )
    

    def show_help(self, message, button):
        popup = HelpPopup(message, self)
        self.popups.append(popup)
        popup.move(button.mapToGlobal(button.rect().bottomRight()))
        popup.show()
        popup.setFocus()
        def close_popup(event, popup=popup):
            popup.close()
        popup.focusOutEvent = close_popup
    
    def browse_folder(self, line_edit):
        folder = QFileDialog.getExistingDirectory(self, "Select Directory", directory=line_edit.text())
        if folder:
            line_edit.setText(folder.replace("/","\\"))
    
    def onChange_PhpDir(self):
        self.html_input.setText(Path(self.php_input.text()).resolve().as_posix().replace("/","\\") + "\\_HTML RESELLERS")
        self.detect_emails()
        self.detect_phpVariable()
        self.detect_replacing()
    
    def onChange_ProductName(self):
        self.detect_zipName()
    
    def onChange_ReplaceDir(self):
        dir = self.replace_input.text()
        urls = self.replace_urls.toPlainText().split("\n")
        self.replace_urls.setText("")
        for url in urls:
            if url[url.__len__()-7:] == "/files/" :
                url_prefix = url[:url.__len__()-7]
                url = url_prefix[:url_prefix.rfind("/")+1] + dir + url[url.__len__()-7:]
            else:
                url_prefix = url[:url.__len__()-1]
                url = url_prefix[:url_prefix.rfind("/")+1] + dir + url[url.__len__()-1:]
            self.replace_urls.append(url)
    
    def start_conversion(self):
        self.config = {
            "phpDir": self.php_input.text().replace("/","\\"),
            "templateDir": self.template_input.text().replace("/","\\"),
            "htmlDir": self.html_input.text().replace("/","\\"),
            "productName": self.product_input.text(),
            "classesToKeep": self.classes_input.text(),
            "replaceDir": self.replace_input.text(),
            "replaceLinks": self.replace_urls.toPlainText(),
            "emailLinksFrom": self.email_links_from_input.text(),
            "emailLinksTo": self.email_links_to_input.text(),
            "createZipFiles": "true" if self.createZip_checkbox.isChecked() else "false",
            "deleteUncompressedFiles": "true" if self.delete_checkbox.isChecked() else "false",
        }
        save_config(self.config)

        classesToKeep = [cls.strip() for cls in self.config["classesToKeep"].split(",") if cls.strip()]
        replace_urls = [cls.strip() for cls in self.replace_urls.toPlainText().split("\n") if cls.strip()]

        email_map = {}
        for i in range(MAX_EMAILS_NUM):
            _in = self.source_emails[i].text().strip()
            if not _in:
                continue
            _out = self.destination_emails[i].text().strip()
            if not _out or _out == "(none)":
                continue
            email_map[_in] = _out
        
        file_copy_array_0 = [ "emails", "files", "images", "js", "affiliates", "articles", "jv" ]
        file_copy_array_n = [ "files_oto", "images_oto" ]
        file_php_array_0 = [ "disclaimer", "index", "privacy", "terms", "affiliates", "jv", "dl" ]
        file_php_array_n = [ "oto" ]
        file_html_array_0 = [ "disclaimer", "index", "privacy", "terms", "affiliates", "jv", "thankyou", "thankyou_signup" ]
        file_html_array_n = [ "oto", "thankyou_with_oto" ]

        start_conversion(
            self.config["phpDir"], self.config["templateDir"], self.config["htmlDir"],
            self.config["productName"], classesToKeep, replace_urls,
            self.config["emailLinksFrom"], self.config["emailLinksTo"],
            self.config["createZipFiles"]=="true", self.zip_input.text(), self.config["deleteUncompressedFiles"]=="true",
            email_map, file_copy_array_0, file_copy_array_n, file_php_array_0, file_php_array_n, file_html_array_0, file_html_array_n,
            self, self.progress, self.going, self.log_output
        )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ConverterApp()
    window.show()
    sys.exit(app.exec())
