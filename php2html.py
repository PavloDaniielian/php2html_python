import sys
import os
import configparser
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit, QHBoxLayout, QVBoxLayout, QCheckBox, QFileDialog, QProgressBar, QTextEdit, QGridLayout, QSizePolicy, QSpacerItem
)

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

# Main Window Class
class ConverterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PHP to HTML Site Converter")
        self.setGeometry(200, 30, 1000, 900)
        self.config = load_config()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        def create_directory_section(label_text, default_path):
            layout = QHBoxLayout()
            label = QLabel(label_text)
            label.setFixedWidth(110)
            edit = QLineEdit(default_path)
            browse_button = QPushButton("...")
            browse_button.setFixedWidth(30)
            browse_button.clicked.connect(lambda: self.browse_folder(edit))
            layout.addWidget(label)
            layout.addWidget(edit)
            layout.addWidget(browse_button)
            return layout, edit
        
        def create_text_section(label_text, default_value):
            layout = QHBoxLayout()
            label = QLabel(label_text)
            label.setFixedWidth(110)
            edit = QLineEdit(default_value)
            layout.addWidget(label)
            layout.addWidget(edit)
            return layout, edit
        
        # PHP, Template, and HTML Directories
        php_layout, self.php_input = create_directory_section("PHP Directory:", self.config["phpDir"])
        template_layout, self.template_input = create_directory_section("Template Directory:", self.config["templateDir"])
        html_layout, self.html_input = create_directory_section("HTML Directory:", self.config["htmlDir"])
        
        # Product Name, Classes, Replace Dir
        product_layout, self.product_input = create_text_section("Product Name:", self.config["productName"])
        classes_layout, self.classes_input = create_text_section("Classes to Keep:", self.config["classesToKeep"])
        replace_layout, self.replace_input = create_text_section("Replace Directory:", self.config["replaceDir"])
        
        # Assign Emails Section
        email_layout = QGridLayout()
        email_layout.addWidget(QLabel("Assign Emails:"), 0, 1, 1, 2)
        email_layout.addWidget(QLabel("Source Site Emails (detected)"), 0, 3)
        email_layout.addWidget(QLabel("Client's Destination Emails (emails/*.txt)"), 0, 5)
        self.source_emails = []
        self.destination_emails = []
        
        for i in range(MAX_EMAILS_NUM):
            email_layout.setColumnMinimumWidth(1, 50)
            email_label = QLabel(f"Email {i+1}:")
            email_layout.addWidget(email_label, i+1, 2)
            email_label.setFixedWidth(60)
            source_email = QLineEdit()
            dest_email = QLineEdit()
            self.source_emails.append(source_email)
            self.destination_emails.append(dest_email)
            email_layout.addWidget(source_email, i+1, 3)
            email_layout.addWidget(QLabel("====>"), i+1, 4)
            email_layout.addWidget(dest_email, i+1, 5)
        
        # Email Links
        email_links_layout, self.email_links_input = create_text_section("Email Links:", self.config["emailLinks"])
        
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
        progress_label = QLabel("Progress:")
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
