import requests
import xml.etree.ElementTree as ET
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("==================================================")
print("   DAWAFLASH LOCAL MULTI-MEDIA SIMULATOR 🇹🇳      ")
print("==================================================")
print("-> To send text: Just type your text normally.")
print("-> To send an image: Type '/image filename.jpg' (e.g., /image receipt_original.jpg)")
print("-> Type 'exit' to quit.\n")

URL = "http://127.0.0.1:8000/webhook"
IMAGE_SERVER_URL = "http://127.0.0.1:8080"
USER_PHONE = "+21692177031"

while True:
    try:
        user_input = input("You: ").strip()
        if user_input.lower() == 'exit':
            print("\nClosing Simulator. Good luck! 🚀")
            break
        if not user_input:
            continue

        # Default setup for normal text interactions
        payload = {
            "From": f"whatsapp:{USER_PHONE}",
            "Body": user_input,
            "NumMedia": "0"
        }

        # If the user uses the image command, dynamically alter the Twilio payload matrix
        if user_input.startswith("/image "):
            filename = user_input.replace("/image ", "").strip()
            payload["Body"] = "" 
            payload["NumMedia"] = "1"
            payload["MediaUrl0"] = f"{IMAGE_SERVER_URL}/{filename}"
            payload["MediaContentType0"] = "image/jpeg"
            print(f"[System]: Simulating upload of {filename} via local gateway...")

        response = requests.post(URL, data=payload)
        
        if response.status_code == 200:
            raw_text = response.text.strip()
            if not raw_text:
                print("\nDawaFlash Bot: [Empty 200 OK Response]\n")
                continue
            try:
                root = ET.fromstring(raw_text)
                body_element = root.find(".//Body") or root.find(".//body")
                if body_element is not None and body_element.text:
                    print(f"\nDawaFlash Bot: {body_element.text}\n")
                else:
                    print(f"\nDawaFlash Bot (Raw TwiML): {raw_text}\n")
            except ET.ParseError:
                print(f"\nDawaFlash Bot (Raw Text): {raw_text}\n")
        else:
            print(f"\n❌ Server Error: Status Code {response.status_code}\n")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to FastAPI server on port 8000!\n")
    except KeyboardInterrupt:
        print("\nExiting...")
        break
