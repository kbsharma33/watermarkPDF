from flask import Flask, request, send_file, render_template, url_for
from PyPDF2 import PdfReader, PdfWriter
from pdf2image import convert_from_bytes
from PIL import Image
import io
import os

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def upload_file():
    return render_template('upload_image_with_preview.html')

@app.route('/preview', methods=['POST'])
def preview_first_page():
    uploaded_pdf = request.files['pdf_file']
    pdf_bytes = uploaded_pdf.read()

    # Convert the first page of the PDF to an image
    first_page_image = convert_from_bytes(pdf_bytes, first_page=1, last_page=1)[0]
    preview_path = os.path.join(UPLOAD_FOLDER, "preview.jpg")
    first_page_image.save(preview_path)

    # Save the PDF file for watermarking
    pdf_path = os.path.join(UPLOAD_FOLDER, "uploaded.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    return render_template('upload_image_with_preview.html', preview_url=url_for('static', filename="preview.jpg"))

@app.route('/watermark', methods=['POST'])
def watermark_pdf():
    watermark_image = request.files['image_file']
    transparency = float(request.form['transparency'])
    x_position = int(request.form['x_position'])
    y_position = int(request.form['y_position'])

    # Load the uploaded PDF
    pdf_path = os.path.join(UPLOAD_FOLDER, "uploaded.pdf")
    pdf_reader = PdfReader(pdf_path)
    pdf_writer = PdfWriter()

    # Process the watermark image
    watermark_img = Image.open(watermark_image).convert("RGBA")
    watermark_img = apply_transparency(watermark_img, transparency)

    for page in pdf_reader.pages:
        # Convert the PDF page to a Pillow image
        pdf_page_image = convert_pdf_page_to_image(page)

        # Overlay the watermark
        watermarked_image = overlay_watermark(pdf_page_image, watermark_img, x_position, y_position)

        # Convert the watermarked image back to PDF
        buffer = io.BytesIO()
        watermarked_image.save(buffer, format="PDF")
        buffer.seek(0)
        pdf_writer.add_page(PdfReader(buffer).pages[0])

    # Save and return the watermarked PDF
    output_pdf = io.BytesIO()
    pdf_writer.write(output_pdf)
    output_pdf.seek(0)

    return send_file(output_pdf, as_attachment=True, download_name="watermarked.pdf", mimetype='application/pdf')

def apply_transparency(image, transparency):
    """Apply transparency to an image."""
    alpha = image.getchannel("A")
    alpha = alpha.point(lambda p: p * transparency)
    image.putalpha(alpha)
    return image

def overlay_watermark(page_image, watermark_image, x, y):
    """Overlay the watermark image onto the PDF page image."""
    page_image.paste(watermark_image, (x, y), watermark_image)
    return page_image

def convert_pdf_page_to_image(page):
    """Convert a PDF page to a Pillow image."""
    buffer = io.BytesIO()
    page_writer = PdfWriter()
    page_writer.add_page(page)
    buffer.seek(0)
    return convert_from_bytes(buffer.getvalue())[0]

if __name__ == '__main__':
    app.run(debug=True)
