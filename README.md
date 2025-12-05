# OCR Application (Tesseract + Python)

This project provides a simple and automated way to perform OCR (Optical Character Recognition) on PDF files using Python and Tesseract OCR.
Just place your PDFs into a folder, run the script, and the extracted text will be saved automatically.

## Installation
1. Install Python Dependencies

Run the following command to install all required packages:

```bash
pip install -r requirements.txt
```

2. Install Tesseract OCR (Windows)

Go to the recommended Windows installer page:

```bash
https://github.com/UB-Mannheim/tesseract/wiki
```

Scroll down to find the latest **.exe** installer, usually named similar to:

```bash
tesseract-ocr-w64-setup-v5.3.1.20230401.exe
```

Download and run the installer.

During installation, ensure you check:

Add Tesseract to system PATH

Select additional languages you need
(e.g., English, Malay, Chinese, etc.)

## Project Folder Structure

Prepare your project directory as follows:

Tesseract_OCR/

 ├── app.py               ← main OCR script
 
 ├── input_files/         ← place all PDF files here
 
 ├── output_files/        ← OCR output (.txt) will be saved here

## How to Run
1. Verify Tesseract OCR Path

Make sure Tesseract is installed here:

```bash
C:\Program Files\Tesseract-OCR\tesseract.exe
```

If installed elsewhere, update the path inside your Python script accordingly.

2. Add Input Files

Copy your PDF files into the input_files folder

—or—

Open the application interface to select files/folders.

3. Run the OCR Application

```bash
python app.py
```

4. Output

All extracted text files will be saved in:

output_files/

Each PDF will produce one .txt file with the same name.

## Notes

Supports multi-language OCR depending on your Tesseract installation.

Works best with high-quality scanned documents.
