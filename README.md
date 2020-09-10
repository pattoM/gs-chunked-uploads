# google-storage-chunked-file-upload
Upload files directly to google storage. Chunked upload functionality is enabled by Dropzone.js 

### Running the app locally 
1. Export the flask environment variable  `export FLASK_APP=main.py`
2. Run with `flask run`
3. If debug mode needs to be enabled for dev, `export FLASK_DEBUG=1`

Note 1: As usual, activate your virtualenvironment and install requirements before attempting to run the app 
`source venv/bin/activate` then `pip install -r requirements.txt` 


### Deployment considerations 
The provided procfile ensures seamless deployment to heroku.

### Live Demo Link 
https://gs-chunked-uploads.herokuapp.com/


### Other considerations 
Store the json credentials key in the same directory as `main.py` file. 
Remove indicated lines of code that delete uploads immediately they succeed. This is currently meant to conserve space on the demo website backend. 