Installation

1.Install required packages using:

pip install -r requirements.txt

2.Go to the recommended Windows installer page:

https://github.com/UB-Mannheim/tesseract/wiki

Scroll down to find the latest .exe installer:

Look for something like:
tesseract-ocr-w64-setup-v5.3.1.20230401.exe

Click to download and install it.

During installation, make sure to check:

“Add to system PATH”

Select your desired languages (you can add Malay, Chinese, etc.)

Project Folder Layout

Prepare your project folders as below:

ocr_app/
 ├── app.py
 
 ├── input_files/     ← can put all PDFs here
 
 ├── output_files/    ← script will create text files here

How to Run:
1.Make sure the Tesseract OCR is installed in following path:

C:\Program Files\Tesseract-OCR\tesseract.exe
2.Copy your input files into “input_files” folder.

3.Run the python file using:

python app.py

4.The output files will be created in “output_files” folder in .txt format.
