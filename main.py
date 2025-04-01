import google.generativeai as genai
import json
import os
import sys
import traceback
import io
from flask import Flask, redirect, request, send_file
from google.cloud import storage
import logging

logging.basicConfig(level=logging.INFO)
print(">>> Flask app is starting...")

app = Flask(__name__)
storage_client = storage.Client()

BUCKET_NAME = "flaskimage_upload"
genai.configure(api_key=os.environ['GEMINI_API'])

generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "application/json",
}

model = genai.GenerativeModel(model_name="gemini-1.5-flash")

PROMPT = "Generate a title and a description of the image. Make it JSON 2 attributes title, description"

def upload_to_gemini(path, mime_type=None):
    file = genai.upload_file(path, mime_type=mime_type)
    print(f"Uploaded file '{file.display_name}' as: {file.uri}")
    return file

def get_list_of_files(BUCKET_NAME):
    print("get_list_of_files " + BUCKET_NAME)
    blobs = storage_client.list_blobs(BUCKET_NAME)
    files = [blob.name for blob in blobs if blob.name.endswith((".jpeg", ".jpg"))]
    return files

def upload_file(BUCKET_NAME, file_name):
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(file_name)
    blob.upload_from_filename(file_name)

def download_file(BUCKET_NAME, file_name):
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(file_name)
    blob.download_to_filename(file_name)
    blob.reload()
    return blob

@app.route('/')
def index():
    try:
        files = get_list_of_files(BUCKET_NAME)
        page = """<body>
        <h1>Upload an Image</h1>
        <form method="post" enctype="multipart/form-data" action="/upload">
            <input type="file" name="form_file" accept="image/jpeg"/>
            <button type="submit">Upload</button>
        </form>
        <h2>Uploaded Files:</h2>
        <hr><table width="80%" align="center">
        """
        idx = 0
        for file in files:
            image_url = f"/proxy/{file}"
            if idx % 8 == 0:
                page += '<tr>'
            page += f'<td width="50%"><a href="/files/{file}"><img width="300" height="200" src="{image_url}" style="object-fit:cover; border-radius:10px;"></a></td>\n'
            idx += 1
            if idx % 8 == 0:
                page += '</tr>\n'
        page += "</table></body>"
        return page
    except Exception as e:
        traceback.print_exc()
        return f"<h1>Internal Server Error</h1><pre>{e}</pre>", 500

@app.route('/upload', methods=['POST'])
def upload():
    try:
        print("POST /upload")
        file = request.files['form_file']
        file.save(file.filename)
        upload_file(BUCKET_NAME, file.filename)

        response = model.generate_content([
            upload_to_gemini(file.filename, mime_type="image/jpeg"),
            "\n\n",
            PROMPT
        ])

        print(response.text)
        text = response.text.replace('```json', '').replace('```', '')
        json_file = file.filename + '.json'
        with open(json_file, 'w') as f:
            f.write(text)
        upload_file(BUCKET_NAME, json_file)
        os.remove(file.filename)

        return redirect('/files/' + file.filename)
    except Exception as e:
        traceback.print_exc()
        return f"<h1>Upload Failed</h1><pre>{e}</pre>", 500

@app.route('/files/<filename>')
def get_file(filename):
    print("GET /files/" + filename)
    data = {
        'title': 'NO TITLE',
        'description': 'NO DESCRIPTION'
    }
    try:
        download_file(BUCKET_NAME, filename + '.json')
        with open(filename + '.json', 'r') as f:
            text = f.read()
            if text.strip():
                data = json.loads(text)
        os.remove(filename + '.json')
    except Exception as e:
        print(f"Error reading JSON for {filename}: {e}")
        traceback.print_exc()

    image_html = f"""
    <h2>{data['title']}</h2>
    <img src="/proxy/{filename}" width="500" height="333"><br>
    <p>{data['description']}</p>
    <p><a href="/">BACK</a></p>
    """
    return image_html

@app.route('/proxy/<filename>')
def proxy_image(filename):
    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        image_data = blob.download_as_bytes()
        mime_type = "image/jpeg" if filename.lower().endswith((".jpg", ".jpeg")) else "application/octet-stream"
        return send_file(io.BytesIO(image_data), mimetype=mime_type, download_name=filename)
    except Exception as e:
        traceback.print_exc()
        return f"Error loading image: {e}", 500

if __name__ == "__main__":
    print(">>> Running Flask directly")
    app.run(host="0.0.0.0", port=8080)
