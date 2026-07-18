from PIL import Image, ImageDraw
import imagehash

print("--- Running Realistic WhatsApp Distortion Check ---")

# 1. Create a base receipt image
img1 = Image.new('RGB', (400, 500), color=(255, 255, 255))
canvas = ImageDraw.Draw(img1)
canvas.text((20, 20), "PHARMACIE TUNISIE", fill=(0, 0, 0))
canvas.text((20, 50), "Augmentin: 45.0 TND", fill=(0, 0, 0))
canvas.text((20, 80), "Date: 18/07/2026", fill=(0, 0, 0))
img1.save("receipt_original.jpg")

# 2. Simulate WhatsApp behavior: Resize down + degrade JPEG quality heavily
img_loaded = Image.open("receipt_original.jpg")
img_distorted = img_loaded.resize((380, 475)) 
img_distorted.save("receipt_whatsapp.jpg", "JPEG", quality=30)

# 3. Calculate perceptual hashes
hash_original = imagehash.phash(Image.open("receipt_original.jpg"))
hash_whatsapp = imagehash.phash(Image.open("receipt_whatsapp.jpg"))

# 4. Compute Hamming Distance
distance = hash_original - hash_whatsapp

print(f"Original pHash:  {hash_original}")
print(f"WhatsApp pHash:  {hash_whatsapp}")
print(f"Calculated Hamming Distance: {distance}")

if distance <= 4:
    print("STATUS: ❌ DUPLICATE DETECTED. SYSTEM RESISTED WHATSAPP DISTORTION COLD.")
else:
    print("STATUS: ✅ UNIQUE CLAIM.")
