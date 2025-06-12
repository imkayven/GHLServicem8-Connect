from flask import Flask, request, jsonify
import requests
import time
from datetime import datetime
import os

app = Flask(__name__)

# === Constants ===
API_KEY = os.getenv("SERVICEM8_API_KEY")
STAFF_UUID = "f885d6a8-52e8-4292-862e-22dff508506b"    
CATEGORY_UUID = "2aa7d1dd-a75a-4c2c-aa25-22b6c288851b" ## Standard
JOB_STATUS = "Quote"

# Webhook URL
WEBHOOK_URL = "https://services.leadconnectorhq.com/hooks/Js2We1X09LX46pHT1RPI/webhook-trigger/64c0ee86-9732-455c-a4da-1ec9ea91abbc"

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "X-Api-Key": API_KEY
}

@app.route("/servicem8/create-job", methods=["POST"])
def create_job():
    print("=== Step 0: Receiving request ===")
    data = request.get_json()
    print("Received data:", data)

    # Safely extract and default all fields to empty string if missing or empty
    firstname = data.get("first_name", "") or ""
    lastname = data.get("last_name", "") or ""
    email = data.get("email", "") or ""
    job_address = data.get("Job Address", "") or ""
    job_description = data.get("Job Description", "") or ""
    phone = data.get("phone", "") or ""
    schedule_date_and_time = data.get("schedule_date_and_time", "") or ""

    billing_address = job_address  # Same as job_address
    work_done_description = "work_done_description here"
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Step 1: Create job
    print("=== Step 1: Creating job ===")
    create_payload = {
        "status": JOB_STATUS,
        "active": 1,
        "created_by_staff_uuid": STAFF_UUID,
        "date": current_date,
        "billing_address": billing_address,
        "category_uuid": CATEGORY_UUID,
        "job_address": job_address,
        "job_description": job_description,
        "work_done_description": work_done_description
    }
    # print("Job creation payload:", create_payload)

    create_url = "https://api.servicem8.com/api_1.0/job.json"
    create_response = requests.post(create_url, json=create_payload, headers=headers)
    print("Job creation response:", create_response.status_code, create_response.text)

    if create_response.status_code != 200:
        return jsonify({
            "error": "Failed to create job",
            "details": create_response.text
        }), 500

    time.sleep(1)  # Allow job time to save

    # Step 2: Find newly created job
    print("=== Step 2: Fetching job list ===")
    get_url = "https://api.servicem8.com/api_1.0/job.json"
    get_response = requests.get(get_url, headers=headers)
    # print("Job list response:", get_response.status_code)

    if get_response.status_code != 200:
        return jsonify({
            "error": "Failed to fetch jobs",
            "details": get_response.text
        }), 500

    jobs = get_response.json()
    matching_job = next((job for job in jobs if
                         job.get("job_address") == job_address and
                         job.get("job_description") == job_description), None)

    if not matching_job:
        print("Job not found after creation.")
        return jsonify({"error": "Job not found after creation"}), 404

    job_uuid = matching_job["uuid"]
    print("Matched Job UUID:", job_uuid)

    # Step 3: Create job contact
    print("=== Step 3: Creating job contact ===")
    contact_url = "https://api.servicem8.com/api_1.0/jobcontact.json"
    contact_payload = {
        "job_uuid": job_uuid,
        "first": firstname,
        "last": lastname,
        "phone": phone,
        "mobile": phone,
        "email": email,
        "type": "JOB",
        "is_primary_contact": 1
    }

    # print("Job contact payload:", contact_payload)

    contact_response = requests.post(contact_url, json=contact_payload, headers=headers)
    print("Contact creation response:", contact_response.status_code, contact_response.text)

    if contact_response.status_code != 200:
        return jsonify({
            "error": "Failed to create job contact",
            "details": contact_response.text
        }), 500


    # Step 4: Get Staff Full Name
    print("=== Step 4: Fetching staff info ===")
    staff_url = f"https://api.servicem8.com/api_1.0/staff/{STAFF_UUID}.json"
    staff_response = requests.get(staff_url, headers=headers)
    print("Staff fetch response:", staff_response.status_code)

    if staff_response.status_code == 200:
        staff_data = staff_response.json()
        staff_full_name = f"{staff_data.get('first', '')} {staff_data.get('last', '')}".strip()
    else:
        staff_full_name = "Unknown"


    # === Final Response ===
    print("=== Job and contact creation successful ===")
    return jsonify({
        "message": "Job and contact created successfully",
        "job_id": job_uuid, ## job_uuid
        "job_status": JOB_STATUS,
        "assigned_staff": staff_full_name,
        "schedule_date_and_time": schedule_date_and_time,
        "job_description": job_description,
        "job_address": job_address,
        "date_created": current_date
    }), 200


@app.route('/ghl/send-data', methods=['POST'])
def send_to_ghl():
    data = request.get_json()

    # Validate required fields
    required_fields = ["first_name", "last_name", "phone", "email", "job_address", "job_description"]
    missing = [field for field in required_fields if field not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    # Combine name
    name = f"{data['first_name'].capitalize()} {data['last_name'].capitalize()}"

    # Create payload
    payload = {
        "first_name": data["first_name"],
        "last_name": data["last_name"],
        "phone": data["phone"],
        "email": data["email"],
        "job_address": data["job_address"],
        "job_description": data["job_description"],
        "name": name
    }

    # Send POST request to webhook
    response = requests.post(WEBHOOK_URL, json=payload)

    # Return the webhook response
    return jsonify({
        "status_code": response.status_code,
        "webhook_response": response.text
    })


@app.route('/test', methods=['POST'])
def log_post_request():
    # Get the JSON data from the request
    data = request.get_json()
    
    # # Print the data to the console (log)
    # print(data)
    
    # ###You can also log it to a file if you prefer
    # with open('log.txt', 'a') as f:
    #     f.write(str(data) + '\n')
    
    # Return a response
    # return 'Received and logged the POST request successfully!', 200
    return jsonify(data), 200

@app.route('/', methods=['GET'])
def index():
    return jsonify({
    "message": {
        "status": "ok",
        "developer": "kayven",
        "email": "yvendee2020@gmail.com"
    }})

if __name__ == "__main__":
    app.run(debug=True)
