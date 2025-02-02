import os
import time
import sys
from flask import Flask, request, redirect
from google.cloud import storage

storage_client = storage.Client()

BUCKET_NAME = "flaskimage_upload"

app = Flask(__name__)

def get_list_of_files(bucket_name):
    """Retrieve a list of all files in the Cloud Storage bucket."""
    try:
        bucket = storage_client.bucket(bucket_name)
        blobs = bucket.list_blobs()
        return [blob.name for blob in blobs]
    except Exception as e:
        print(f"Error retrieving files: {e}", file=sys.stderr)
        return [] 


def upload_file(bucket_name, file):
    """Upload a file to Cloud Storage and make it public."""
    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file.filename)

        print(f"Uploading file: {file.filename} to Cloud Storage bucket: {bucket.name}")


        blob.upload_from_file(file, content_type="image/jpeg")
        blob.make_public()

        return blob.public_url 
    except Exception as e:
        print(f"Upload failed: {e}", file=sys.stderr)
        return None 


@app.route('/')
def index():
    """Render the main page with file upload and file list."""
    files = get_list_of_files(BUCKET_NAME) 
    page = """
    <h1>Upload an Image</h1>
    <form method="post" enctype="multipart/form-data" action="/upload">
        <input type="file" name="form_file" accept="image/jpeg"/>
        <button type="submit">Upload</button>
    </form>
    <h2>Uploaded Files:</h2>
    <ul>
    """
    for file in files:
        page += f'<li><a href="https://storage.googleapis.com/{BUCKET_NAME}/{file}" target="_blank">{file}</a></li>'
    page += "</ul>"
    return page


@app.route('/upload', methods=["POST"])
def upload():
    """Handle image uploads."""
    file = request.files.get('form_file') 

 
    file_url = upload_file(BUCKET_NAME, file) 

    return redirect("/")  
    

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)