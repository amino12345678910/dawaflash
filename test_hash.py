from PIL import Image, ImageDraw
import imagehash

print("--- Initializing Dynamic Image Fraud Check ---")

# 1. Create a base mock receipt image
img1 = Image.new('RGB', (400, 500), color=(255, 255, 255))
canvas1 = ImageDraw.Draw(img1)
canvas1.text((20, 20), "PHARMACIE TUNISIE", fill=(0, 0, 0))
canvas1.text((20, 50), "Augmentin: 45.0 TND", fill=(0, 0, 0))
img1.save("mock_receipt_original.jpg")

# 2. Create a modified copy (simulating compression or minor visual tampering)
img2 = img1.copy()
canvas2 = ImageDraw.Draw(img2)
canvas2.rectangle([10, 10, 15, 15], fill=(5, 5, 5)) # Add tiny visual noise artifact
img2.save("mock_receipt_tampered.jpg")

# 3. Calculate perceptual hashes (pHash focuses on structural frequencies)
hash_original = imagehash.phash(Image.open("mock_receipt_original.jpg"))
hash_tampered = imagehash.phash(Image.open("mock_receipt_tampered.jpg"))

# 4. Compute Hamming Distance
distance = hash_original - hash_tampered

print(f"Original Structure pHash: {hash_original}")
print(f"Tampered Structure pHash: {hash_tampered}")
print(f"Calculated Hamming Distance: {distance}")

# 5. Assert against your architecture's strict anti-fraud gateway threshold (<= 4)
if distance <= 4:
    print("STATUS: ❌ DUPLICATE DETECTED. CLAIMS INGESTION BLOCK TRIGGERED.")
else:
    print("STATUS: ✅ UNIQUE CLAIM. ROUTING FILE TO NEXT ENGINE MODULE.")
