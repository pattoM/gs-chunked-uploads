#imports - specified in requirements.txt 
from flask import Flask, render_template, request, redirect, url_for
from google.auth.transport import requests
from google.cloud import datastore
from google.cloud import storage
from google.auth.transport.requests import AuthorizedSession
import requests
import os, io
from config import Config
from uuid import uuid4
import datetime

#app instance and config from config class
app = Flask(__name__)

app.config.from_object(Config)


# setting application credentials env variable
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = app.config['CREDENTIAL_FILE']



#init credentials from service acc = used to authenticate requests to the server. 
from google.oauth2 import service_account
import googleapiclient.discovery
# Get credentials
credentials = service_account.Credentials.from_service_account_file(
    filename=os.environ['GOOGLE_APPLICATION_CREDENTIALS'],
    scopes=['https://www.googleapis.com/auth/cloud-platform'])

#creating storage client objects
storage_client = storage.Client()
storage_bucket = storage_client.get_bucket(app.config['CLOUD_STORAGE_BUCKET'])


#function to start resumable upload session and return the uri 
def start_resumable_upload_session(name, mime_type):
    """
    Mime type from the original file extension to upload file correctly. 

    """
    url = f"https://storage.googleapis.com/upload/storage/v1/b/{app.config['CLOUD_STORAGE_BUCKET']}/o?uploadType=resumable&name={name}"
    headers = {
        "X-Upload-Content-Type":mime_type
    }
    #prep an authenticated session to make requests 
    authed_session = AuthorizedSession(credentials)

    resp = authed_session.post(url, headers=headers)
    if resp.status_code == 200:
        return resp.headers.get('Location',None)
    else:
        return None 


resumable_upload_object_dict = {

}

video_mime_type_map = {
    "flv":"video/x-flv",
    "mp4":"video/mp4",
    "m3u8":"application/x-mpegURL",
    "ts":"video/MP2T",
    "3gp":"video/3gpp",
    "mov":"video/quicktime",
    "avi":"video/x-msvideo",
    "wmv":"video/x-ms-wmv"
}



@app.route('/')
def index():
    #control chunk size for uploads by simply changing the config value MAX_CHUNK_SIZE
    
    return render_template("index.html", file_chunk_size=app.config['MAX_CHUNK_SIZE']) 



@app.route('/upload/', methods=['POST'])
def upload():
    #read chunk size - dropzone also provides the current chunk size in request. Fallback incase someone uses http client with wrong value
    file_chunk = request.files.get('form-file')
    file_chunk.seek(0, os.SEEK_END)
    file_length = file_chunk.tell()
    #return seek pointer to zero
    file_chunk.seek(0)


    dzuuid = request.form.get('dzuuid')

    if not file_chunk or not dzuuid:
        return "Error 1", 400

    #get the mime type for the file 
    file_ext = file_chunk.filename.split(".")[-1] 

    if file_ext in video_mime_type_map:
        full_mimetype = video_mime_type_map[file_ext]
    else:
        return "Error 2",400

    if dzuuid in resumable_upload_object_dict:
        # just stream the next chunk
        sess_uri = resumable_upload_object_dict[dzuuid]["sess_uri"] 
        last_byte = resumable_upload_object_dict[dzuuid]["last_chunk"]
        tot_size = resumable_upload_object_dict[dzuuid]["tot_size"]
        authed_session = AuthorizedSession(credentials) 
        cn_length = file_length


        headers = {
            "Content-Length": str(cn_length),
            "Content-Range": f"bytes {int(last_byte)+1}-{int(last_byte)+int(cn_length)}/{tot_size}",
            "Content-Type":full_mimetype
        }

        

        resp = authed_session.put(sess_uri,data=file_chunk.read(), headers=headers) 
        if resp.status_code in (200,201,):
            del resumable_upload_object_dict[dzuuid]
            #if file was smaller than chunksize, delete the uploaded files 
            #this is a fallback to avoid filling my drive. Delete loop below in your setup
            blobs = storage_bucket.list_blobs()
            for blob in blobs:
                try:
                    print("Deleting: ", blob.public_url) 
                except:
                    pass 
                try:
                    blob.delete()
                except:
                    pass
            return 'ok'
        elif resp.status_code == 308:
            #update last chunk and return ok 
            last_byte_header = resp.headers.get("Range")
            last_byte = last_byte_header.split("=")[1].split("-")[1]
            resumable_upload_object_dict[dzuuid]["last_chunk"] = last_byte 
            return 'ok'
        else:
            return "Error 3",400

    else:
        # save to datastore since its first instance, create resumable upload object and start streaming

        uuid_filename = uuid4().hex + "." + file_ext

        sess_uri = start_resumable_upload_session(uuid_filename, full_mimetype)
        authed_session = AuthorizedSession(credentials) 
        cn_length = file_length
        tot_size = int(request.form.get("dztotalfilesize"))
        adjusted_tot_size = tot_size-1
        adjusted_cn_length = cn_length -1

        headers = {
            "Content-Length": str(cn_length),
            "Content-Range": f"bytes 0-{adjusted_cn_length}/{tot_size}",
            "Content-Type": full_mimetype
        }


        resp = authed_session.put(sess_uri,data=file_chunk.read(), headers=headers)
        if resp.status_code in  (308,200,201,):
            try:
                last_byte_header = resp.headers.get("Range")

                last_byte = last_byte_header.split("=")[1].split("-")[1]
            except:
                last_byte = 0 #set to zero, this exception is when chunk is smaller than chunk size.

            resumable_upload_object_dict[dzuuid] = {
                "sess_uri": sess_uri,
                "last_chunk": last_byte,
                "tot_size": tot_size 
            }

            #pop from dict if response is code 200 or 201 . These status codes are returned when upload has completed 
            if resp.status_code in (200,201,):
                print("Deleting resumable upload uri :: ")
                del resumable_upload_object_dict[dzuuid]

                #if file was smaller than chunksize, delete the uploaded files 
                #this is a fallback to avoid filling my drive. Delete loop below in your setup
                blobs = storage_bucket.list_blobs()
                for blob in blobs:
                    try:
                        print("Deleting: ", blob.public_url) 
                    except:
                        pass 
                    try:
                        blob.delete()
                    except:
                        pass 
                
                    

            # extract opptional form fields == these can be saved to sql db or even to datastore. Liberty is yours 
            name = str(request.form.get("form-name", ""))
            email = str(request.form.get("form-email", ""))
            country = str(request.form.get("form-country", ""))
            msg = str(request.form.get("form-message", ""))
            file_url = f"https://storage.googleapis.com/test-bucket-alpha-1/{uuid_filename}"


            return 'ok'
        else:
            return "Error 4",400

    

