from flask import Flask, request, jsonify
from google.cloud import storage
import random
import string
from datetime import timedelta
import socket  # Import the socket module to get the hostname

app = Flask(__name__)

# Google Cloud Storage setup
BUCKET_NAME = "storify-cloud-files"
storage_client = storage.Client()  # Automatically uses the VM's default service account
bucket = storage_client.bucket(BUCKET_NAME)

# Dictionary to store file access codes
file_access_codes = {}

# Generate a 5-digit random code
def generate_code():
    return ''.join(random.choices(string.digits, k=5))

# Upload file route
@app.route('/upload', methods=['POST'])
def upload_file():
    # Get the hostname (VM) serving the request
    hostname = socket.gethostname()
    
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    blob = bucket.blob(file.filename)
    blob.upload_from_file(file)

    # Generate a unique 5-digit code for the file
    access_code = generate_code()
    file_access_codes[file.filename] = access_code

    # Print the hostname where the file is uploaded
    print(f"File uploaded by {hostname}.")

    return jsonify({
        "message": "File uploaded successfully",
        "url": f"https://storage.googleapis.com/{BUCKET_NAME}/{file.filename}",
        "access_code": access_code,
        "hostname": hostname  # Include the hostname in the response
    })

# List files based on access code
@app.route('/list', methods=['POST'])
def list_files():
    # Get the hostname of the server processing the request
    hostname = socket.gethostname()
    
    data = request.get_json()
    entered_code = data.get("code", "")

    if not entered_code:
        return jsonify({"error": "No access code provided"}), 400

    # Filter files that match the entered code
    valid_files = [filename for filename, code in file_access_codes.items() if code == entered_code]

    # Print the hostname where the list request was processed
    print(f"List request processed by {hostname}.")

    return jsonify({"files": valid_files, "hostname": hostname})

# Download file route
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    # Get the hostname of the server processing the request
    hostname = socket.gethostname()
    
    blob = bucket.blob(filename)
    
    if not blob.exists():
        return jsonify({"error": "File not found"}), 404

    signed_url = blob.generate_signed_url(
        expiration=timedelta(hours=1),  # URL valid for 1 hour
        method="GET"
    )
    
    # Print the hostname where the download request was processed
    print(f"Download request processed by {hostname} for file {filename}.")

    return jsonify({"download_url": signed_url, "hostname": hostname})

# Delete file route
@app.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    # Get the hostname of the server processing the request
    hostname = socket.gethostname()
    
    blob = bucket.blob(filename)
    
    if not blob.exists():
        return jsonify({"error": "File not found"}), 404

    try:
        blob.delete()
        file_access_codes.pop(filename, None)  # Remove access code
        # Print the hostname where the delete request was processed
        print(f"Delete request processed by {hostname} for file {filename}.")
        return jsonify({"message": f"File '{filename}' deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to delete file: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8083)  # Production mode, runs on port 80
