import sys
import os
import subprocess
import platform
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QLabel, QLineEdit, QMessageBox
)


class FileUploader(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.upload_folder = 'uploads'
        os.makedirs(self.upload_folder, exist_ok=True)

    def initUI(self):
        self.setWindowTitle('File Upload and Download')
        self.setGeometry(100, 100, 400, 200)

        layout = QVBoxLayout()

        self.upload_button = QPushButton('Upload File', self)
        self.upload_button.clicked.connect(self.upload_file)
        layout.addWidget(self.upload_button)

        self.download_label = QLabel('Enter filename to download:', self)
        layout.addWidget(self.download_label)

        self.filename_input = QLineEdit(self)
        layout.addWidget(self.filename_input)

        self.download_button = QPushButton('Download File', self)
        self.download_button.clicked.connect(self.download_file)
        layout.addWidget(self.download_button)

        self.setLayout(layout)

    def upload_file(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Select File", "",
                                                   "All Files (*)", options=options)
        if file_name:
            try:
                # Save the file to the upload folder
                destination = os.path.join(
                    self.upload_folder, os.path.basename(file_name))
                with open(file_name, 'rb') as fsrc, open(destination, 'wb') as fdst:
                    fdst.write(fsrc.read())
                QMessageBox.information(self, 'Success', f'File {
                                        os.path.basename(file_name)} uploaded successfully!')
            except Exception as e:
                QMessageBox.critical(
                    self, 'Error', f'Failed to upload file: {e}')

    def download_file(self):
        filename = self.filename_input.text()
        if filename:
            file_path = os.path.join(self.upload_folder, filename)
            if os.path.exists(file_path):
                # Open the file for download using subprocess
                try:
                    if platform.system() == "Windows":
                        os.startfile(file_path)  # Windows
                    elif platform.system() == "Darwin":
                        subprocess.run(["open", file_path])  # macOS
                    else:
                        subprocess.run(["xdg-open", file_path])  # Linux
                    QMessageBox.information(self, 'Success', f'File {
                                            filename} opened successfully!')
                except Exception as e:
                    QMessageBox.critical(
                        self, 'Error', f'Failed to open file: {e}')
            else:
                QMessageBox.warning(self, 'Error', f'File {
                                    filename} does not exist.')
        else:
            QMessageBox.warning(self, 'Error', 'Please enter a filename.')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    uploader = FileUploader()
    uploader.show()
    sys.exit(app.exec_())
