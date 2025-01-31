import sys
import os
import configparser
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit, QHBoxLayout, QVBoxLayout, QCheckBox, QFileDialog, QProgressBar, QTextEdit, QGridLayout, QToolButton, QFrame
)
from PyQt6.QtCore import Qt  # Fix: Ensure Qt is imported

# Configuration file handling
CONFIG_FILE = "settings.ini"
MAX_EMAILS_NUM = 7

def load_config():
    config = configparser.ConfigParser()
    default_settings = {
        "phpDir": "D:/Work/Upwork/20250127/converting",
        "templateDir": "D:/Work/Upwork/20250127/template",
        "htmlDir": "D:/Work/Upwork/20250127/converting/_HTML RESELLERS",
        "productName": "HealthSupplementNewsletters",
        "classesToKeep": "staatliches",
        "replaceDir": "health",
        "emailLinks": "YOUR LINK",
        "deleteUncompressedFiles": "false"
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
        self.setWindowFlags(Qt.WindowType.Popup)
        #self.setFixedSize(300, 100)
        self.setStyleSheet("background-color: lightgray; border-radius: 5px; padding: 10px;")
        
        layout = QVBoxLayout()
        label = QLabel(message)
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.PlainText)  # Force plain text rendering
        layout.addWidget(label)
        self.setLayout(layout)

# Main Window Class
class ConverterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PHP to HTML Site Converter")
        self.setGeometry(200, 30, 1000, 900)
        self.config = load_config()
        self.popups = []  # Track open popups
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        help_messages = {
            "PHP Directory :": "This is the source site that contains PHP files, images and broadcast emails. File contents will be copied over to reseller's HTML site and processed. Use tags <?php // start of reseller site; ?> and <?php // end of reseller site; ?> to define content to copy over to reseller's HTML site.",
            "Template Directory :": "This is the HTML reseller base template that will be copied over to the reseller's HTML site folder. You can create multiple base templates with different headers, footers, styles and layouts. Use tags <!-- start of reseller site --> and  <!-- end of reseller site --> to define where content should be added.",
            "HTML Directory :": "This is the reseller's HTML directory where files from the \"PHP Directory\" and \"Template Directory\" are combined. This is usually located within a folder in the PHP Directory to keep things organized.",
            "Product Name :": "This will replace any instances of \"PRODUCT NAME\" in the reseller's HTML site with the one you specify. In most cases it replaces the title tag and footer text.",
            "Classes to Keep :": "This defines which custom style classes should be kept in the reseller's HTML site. For example the original h1 tag may contain custom fonts like <h1 class=\"staatliches\">Title</h1>. If \"staatliches\" is defined, then the h1 tag remains the same. If nothing is defined, then tag is stripped and becomes <h1>Title</h1>",
            "Replace Directory :": "Defines the Amazon S3 URL to strip. Performs find and replace and only adds folder and filename download link to all thankyou*.html pages. For example \"https://supersalesmachine.s3.amazonaws.com/members/supercashsavers/file.zip\" becomes \"files/file.zip\". Reseller then uploads zip files to corresponding folders. ",
            "Assign Emails :": "Looks for all broadcast emails in PHP Directory and allows you to choose which ones to use for reseller's site. Example if you have a series of broadcast*.txt emails, but broadcast3.txt is gift email, you can assign broadcast3.txt to not be copied over.",
            "Email Links :": "Replaces instances of URLs that start with https://www.supersalesmachine.com... with default YOUR LINK or a custom placeholder in all emails/broadcast*.txt files. Reseller can then add their own link."
        }

        def create_directory_section(label_text, default_path):
            help_message = help_messages[label_text].replace("<", "&lt;").replace(">", "&gt;")
            layout = QHBoxLayout()
            label = QLabel(label_text)
            label.setFixedWidth(110)
            label.setToolTip(help_message)
            edit = QLineEdit(default_path)
            browse_button = QPushButton("...")
            browse_button.setFixedWidth(30)
            browse_button.clicked.connect(lambda: self.browse_folder(edit))
            help_button = QToolButton()
            help_button.setText("?")
            help_button.setFixedSize(20, 20)
            help_button.clicked.connect(lambda: self.show_help(help_message, help_button))
            
            layout.addWidget(label)
            layout.addWidget(edit)
            layout.addWidget(browse_button)
            layout.addWidget(help_button)
            return layout, edit
        
        def create_text_section(label_text, default_value):
            help_message = help_messages[label_text].replace("<", "&lt;").replace(">", "&gt;")
            layout = QHBoxLayout()
            label = QLabel(label_text)
            label.setFixedWidth(110)
            label.setToolTip(help_message)
            label.setTextFormat(Qt.TextFormat.PlainText)  # Force plain text rendering
            edit = QLineEdit(default_value)
            edit.setToolTip(help_message)
            help_button = QToolButton()
            help_button.setText("?")
            help_button.setFixedSize(20, 20)
            help_button.clicked.connect(lambda: self.show_help(help_message, help_button))
            
            layout.addWidget(label)
            layout.addWidget(edit)
            layout.addWidget(help_button)
            return layout, edit
        
        # PHP, Template, and HTML Directories
        php_layout, self.php_input = create_directory_section("PHP Directory :", self.config["phpDir"])
        template_layout, self.template_input = create_directory_section("Template Directory :", self.config["templateDir"])
        html_layout, self.html_input = create_directory_section("HTML Directory :", self.config["htmlDir"])
        
        # Product Name, Classes, Replace Dir
        product_layout, self.product_input = create_text_section("Product Name :", self.config["productName"])
        classes_layout, self.classes_input = create_text_section("Classes to Keep :", self.config["classesToKeep"])
        replace_layout, self.replace_input = create_text_section("Replace Directory :", self.config["replaceDir"])
        
        # Assign Emails Section
        email_layout = QGridLayout()

        help_message = help_messages["Assign Emails :"].replace("<", "&lt;").replace(">", "&gt;")
        label = QLabel("Assign Emails :")
        label.setToolTip(help_message)
        email_layout.addWidget(label, 0, 1, 1, 2)
        help_button = QToolButton()
        help_button.setText("?")
        help_button.setFixedSize(20, 20)
        help_button.clicked.connect(lambda: self.show_help(help_message, help_button))
        email_layout.addWidget(help_button, 0, 3)
        
        email_layout.addWidget(QLabel("Source Site Emails (detected)"), 0, 4)
        email_layout.addWidget(QLabel("Client's Destination Emails (emails/*.txt)"), 0, 6)
        self.source_emails = []
        self.destination_emails = []
        email_layout.setColumnMinimumWidth(1, 50)
        email_layout.setColumnMinimumWidth(2, 0)
        email_layout.setColumnMinimumWidth(3, 0)
        
        for i in range(MAX_EMAILS_NUM):
            email_label = QLabel(f"Email {i+1}:")
            email_layout.addWidget(email_label, i+1, 2, 1, 2)
            email_label.setFixedWidth(60)
            source_email = QLineEdit()
            dest_email = QLineEdit()
            self.source_emails.append(source_email)
            self.destination_emails.append(dest_email)
            email_layout.addWidget(source_email, i+1, 4)
            email_layout.addWidget(QLabel("====>"), i+1, 5)
            email_layout.addWidget(dest_email, i+1, 6)
        
        # Email Links
        email_links_layout, self.email_links_input = create_text_section("Email Links :", self.config["emailLinks"])
        
        # Checkbox
        self.delete_checkbox = QCheckBox("Delete Uncompressed Files")
        self.delete_checkbox.setChecked(self.config["deleteUncompressedFiles"] == "true")
        
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
        progress_layout.addWidget(progress_label)
        progress_layout.addWidget(self.progress)
        
        # Log Output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        
        # Add widgets to layout
        for section in [php_layout, template_layout, html_layout, product_layout, classes_layout, replace_layout]:
            layout.addLayout(section)
        layout.addLayout(email_layout)
        layout.addLayout(email_links_layout)
        layout.addWidget(self.delete_checkbox)
        layout.addLayout(button_layout)
        layout.addLayout(progress_layout)
        layout.addWidget(self.log_output)
        layout.setSpacing(10)
        
        self.setLayout(layout)
    

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
            line_edit.setText(folder)
    
    def start_conversion(self):
        self.config = {
            "phpDir": self.php_input.text(),
            "templateDir": self.template_input.text(),
            "htmlDir": self.html_input.text(),
            "productName": self.product_input.text(),
            "classesToKeep": self.classes_input.text(),
            "replaceDir": self.replace_input.text(),
            "emailLinks": self.email_links_input.text(),
            "deleteUncompressedFiles": "true" if self.delete_checkbox.isChecked() else "false"
        }
        save_config(self.config)
        
        self.log_output.append("Starting conversion...")
        self.progress.setValue(0)
        import time
        for i in range(1, 101, 10):
            time.sleep(0.1)
            self.progress.setValue(i)
        self.log_output.append("Conversion completed successfully!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ConverterApp()
    window.show()
    sys.exit(app.exec())
