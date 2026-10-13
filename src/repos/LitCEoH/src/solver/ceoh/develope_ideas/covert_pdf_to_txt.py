import os
from PyPDF2 import PdfReader

def convert_pdfs_to_text(pdf_folder, txt_folder):

    # Ensure the output folder exists
    if not os.path.exists(txt_folder):
        try:
            os.makedirs(txt_folder)
            print(f"Created output folder: {txt_folder}")
        except Exception as e:
            print(f"Error creating output folder '{txt_folder}': {e}")
            return

    # Check if the input folder exists
    if not os.path.exists(pdf_folder):
        print(f"Error: Input folder '{pdf_folder}' does not exist.")
        return

    # Check if the input folder is empty
    if not os.listdir(pdf_folder):
        print(f"Error: Input folder '{pdf_folder}' is empty.")
        return

    # Iterate through all PDF files in the source folder
    for filename in os.listdir(pdf_folder):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(pdf_folder, filename)
            txt_filename = f"{os.path.splitext(filename)[0]}.txt"
            txt_path = os.path.join(txt_folder, txt_filename)

            # Check if the text file already exists
            if os.path.exists(txt_path):
                print(f"Text already extracted for '{filename}'. Skipping...")
                continue

            try:
                # Read the PDF file
                reader = PdfReader(pdf_path)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()

                # Check if text was extracted
                if not text.strip():
                    print(f"Warning: No text extracted from {filename}.")
                else:
                    # Write the extracted text to a .txt file
                    with open(txt_path, "w", encoding="utf-8") as txt_file:
                        txt_file.write(text)
                    print(f"Converted: {filename} -> {txt_filename}")
            except FileNotFoundError:
                print(f"Error: File not found '{filename}'. Skipping...")
            except Exception as e:
                print(f"Error processing '{filename}': {e}")
        else:
            print(f"Skipping non-PDF file: {filename}")
