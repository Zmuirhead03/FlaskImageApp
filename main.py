import google.generativeai as genai
import json
import os
import sys
import traceback
from flask import Flask, redirect, request, send_file
from google.cloud import storage


storage_client = storage.Client()


   
BUCKET_NAME = "flaskimage_upload"
app = Flask(__name__)
genai.configure(api_key=os.environ['GEMINI_API'])






generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 8192,
  "response_mime_type": "application/json",
}


model = genai.GenerativeModel(
  model_name="gemini-1.5-flash",
#   generation_config=generation_config,
  # safety_settings = Adjust safety settings
  # See https://ai.google.dev/gemini-api/docs/safety-settings
)


PROMPT = "Generate a title and a description of the image. Make it JSON 2 attributes title, description"


def upload_to_gemini(path, mime_type=None):
  """Uploads the given file to Gemini.


  See https://ai.google.dev/gemini-api/docs/prompting_with_media
  """
  file = genai.upload_file(path, mime_type=mime_type)
  print(f"Uploaded file '{file.display_name}' as: {file.uri}")
  print(file)
  return file




def get_list_of_files(BUCKET_NAME):


    print("\n")
    print("get_list_of_files" + BUCKET_NAME)


    blobs = storage_client.list_blobs(BUCKET_NAME)
    print(blobs)
    files = []


    for blob in blobs:
        if blob.name.endswith(".jpeg") or blob.name.endswith(".jpg"):
            files.append(blob.name)
    return files




def upload_file(BUCKET_NAME , file_name):


    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(file_name)


    blob.upload_from_filename(file_name)


    return


def download_file(BUCKET_NAME , file_name):


   
    bucket = storage_client.bucket(BUCKET_NAME)


    blob = bucket.blob(file_name)
    blob.download_to_filename(file_name)
    blob.reload()
    return blob


@app.route('/')
def index():
   
    files = get_list_of_files(BUCKET_NAME)
    page = """<body">
    <h1>Upload an Image</h1>
    <form method="post" enctype="multipart/form-data" action="/upload">
        <input type="file" name="form_file" accept="image/jpeg"/>
        <button type="submit">Upload</button>
    </form>
    <h2>Uploaded Files:</h2>
    <ul>
    """
    idx = 0
    page += "<hr><table width =\"80%\" align=\"center\">\n"
    for file in files:
        image_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{file}"
        idx =idx +1
        if (idx %8):
            page += '   <tr>\n'
            page += f'<td width="50%"><a href="/files/{file}"><img width="300" height="200" src="{image_url}" style="object-fit:cover; border-radius:10px;"></a></td>\n'
            if((idx% 8) ==0):
                page += "</tr>\n"
    page += "</table>"


    return page






@app.route('/upload', methods = {'POST'})
def upload():
        try:
            print("POST /upload")
            file = request.files['form_file']




            file.save(file.filename)
            upload_file(BUCKET_NAME, file.filename)


            response = model.generate_content(
                [upload_to_gemini(file.filename, mime_type="image/jpeg"), "\n\n", PROMPT]




            )


            print(response.text)
            text =response.text.replace('```json','')
            text = text.replace('```','')
            print(text)


            json_file = file.filename + '.json'
            with open(json_file, 'w') as f:
                f.write(text)
            upload_file(BUCKET_NAME, json_file)


            os.remove(file.filename)


        except:
            traceback.print_exc()
       
        if (file.filename):
            return redirect('/files/' +file.filename)


        else:
            return redirect('/')
 




@app.route('/files/<filename>')
def get_file(filename):
    print("GET /files/" + filename)


    try:
        download_file(BUCKET_NAME, filename + '.json')
        with open(filename+'.json' , 'r') as file:
            data = json.load(file)


        print(data)
    except:
        data = {


            'title':'NO TITLE',
            'description':'NO DESCRIPTION'
        }
        traceback.print_exc()
   
    image_html = '<p><h2>' +data['title'] +'</h2>'
    image_html += f'<img src="https://storage.googleapis.com/{BUCKET_NAME}/{filename}" width="500" height="333"><br>{filename}'


    image_html += '<p>' +data['description'] + '</h2>'


    image_html += '<p><p><a href = "/"> BACK </a>'


    return image_html




if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
