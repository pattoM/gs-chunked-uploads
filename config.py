class Config:
    SECRET_KEY='78dccbbe7d524670964d795641a150c3'
    CLOUD_STORAGE_BUCKET = 'test-bucket-alpha-1' #the name of the google cloud storage bucket here 
    MAX_CONTENT_LENGTH = 300 * 1024 * 1024 #safety fallback incase someone uses a http client to send a large file
    MAX_CHUNK_SIZE = 5242880 #default of 5mb , this must be in multiples of (256*1024)
    CREDENTIAL_FILE = "test-aug-2020-286707-5fb444a69d88.json" #json key file downloaded from your console