# Batch Memory Cleanup Fix - Critical Bug

## المشكل اللي كان (The Problem)

### Scenario:
```
1. User: *sends 2 CIN images*
   System: Batches them, processes
   Result: ❌ Rejection (e.g., "not a CIN, it's a face photo")

2. Batch stays in memory (NOT CLEANED UP!) 🐛

3. User: *sends text message "سلام"*
   System: Sees pending batch, confused
   Result: ❌ NO RESPONSE (silent bug!)
```

**Root Cause:** الـ batch ما يتفسخش بعد rejection أو error!

---

## الحل (The Solution)

### ✅ 1. Automatic Batch Cleanup After Processing

**File:** `app/main.py` - `verify_onboarding_step_in_background()`

**Added cleanup after EVERY processing:**

```python
# After sending response (success or failure)
twilio_client.messages.create(body=reply_text, ...)
print(f"✅ [ONBOARDING BG] Message dispatched")

# CRITICAL: Clean up batch
batch_key = f"{phone_number}:{step}"
if batch_key in pending_media_batches:
    del pending_media_batches[batch_key]
    print(f"🧹 [CLEANUP] Cleared batch: {batch_key}")
```

**Also in exception handler:**
```python
except Exception as e:
    print(f"💥 Error: {e}")
    
    # Clean up even on error!
    batch_key = f"{phone_number}:{step}"
    if batch_key in pending_media_batches:
        del pending_media_batches[batch_key]
        print(f"🧹 [CLEANUP] Cleared batch after error")
```

**الآن:** الـ batch يتفسخ بعد كل processing (success, rejection, or error)!

---

### ✅ 2. Cleanup on Text Messages

**Problem:** لما المستخدم يبعث text بعد rejection، الـ batch pending يمنع الـ response!

**Solution:** فسخ الـ batch لما يجي text message:

```python
elif current_state == 'NEED_CIN':
    if num_media == 0:
        # Text message - clear any pending batch
        batch_key = f"{phone_number}:NEED_CIN"
        if batch_key in pending_media_batches:
            del pending_media_batches[batch_key]
            print(f"🧹 [CLEANUP] Cleared batch on text message")
        
        reply = "Brabbi ab3athli tsawer el CIN..."
```

**الآن:** text messages يعملو cleanup تلقائي!

---

### ✅ 3. Stale Batch Cleanup (10 second timeout)

**Added automatic cleanup for old batches:**

```python
# At start of every webhook
current_time = time.time()
keys_to_delete = []

for key, batch in pending_media_batches.items():
    if batch["timestamp"] and (current_time - batch["timestamp"]) > 10.0:
        keys_to_delete.append(key)

for key in keys_to_delete:
    print(f"🧹 [CLEANUP] Removing stale batch: {key}")
    del pending_media_batches[key]
```

**الآن:** الـ batches القديمة (> 10 ثواني) يتفسخو تلقائياً!

---

## Flow Comparison

### قبل (BUGGY):
```
User: *sends 2 wrong images*
System: 
  - Batch created
  - Process → ❌ Rejection
  - Batch STAYS IN MEMORY 🐛

User: "سلام"
System: 
  - Sees pending batch
  - Confused, no response ❌

User: "Hello?"
System: ... (still silent) ❌
```

---

### بعد (FIXED):
```
User: *sends 2 wrong images*
System:
  - Batch created
  - Process → ❌ Rejection
  - Batch CLEANED UP ✅

User: "سلام"
System: 
  - No pending batch
  - Responds normally ✅
  - "Brabbi ab3athli tsawer el CIN..."

User: *sends correct images*
System: 
  - New batch
  - Process → ✅ Success
  - Batch cleaned up ✅
```

---

## Cleanup Triggers

**الـ batch يتفسخ في:**

1. ✅ **After successful verification**
   - When document is approved
   - State transitions (NEED_CIN → NEED_FACE)

2. ✅ **After rejection**
   - When document is rejected
   - User gets rejection message

3. ✅ **On error**
   - When processing fails (exception)
   - Prevents stuck batches

4. ✅ **On text message**
   - When user sends text without media
   - Clears confusion

5. ✅ **Timeout (10 seconds)**
   - Automatic stale batch removal
   - Safety net

---

## Technical Details

### Batch Lifecycle:

```
[CREATE]
User sends image → batch created with timestamp

[COLLECT]
More images arrive within 2s → added to batch

[PROCESS]
After 2s window → verify_onboarding_step_in_background()
  ↓
  Success → send approval → DELETE BATCH ✅
  ↓
  Reject → send rejection → DELETE BATCH ✅
  ↓
  Error → log error → DELETE BATCH ✅

[CLEANUP]
If somehow missed → timeout cleanup (10s) ✅
```

---

### Batch Keys:

```python
# Format: "phone_number:step"
batch_key = f"{phone_number}:NEED_CIN"
# Example: "+21692177031:NEED_CIN"

# Different steps = different batches
"+21692177031:NEED_CIN"    # CIN batch
"+21692177031:NEED_FACE"   # Face batch (separate)
"+21692177031:NEED_CARNET" # CNAM batch (separate)
```

---

## Test Scenarios

### Scenario 1: Wrong Images → Text Message
```
✅ Send 2 wrong CIN images
✅ Get rejection
✅ Send "سلام"
✅ Get response: "Brabbi ab3athli tsawer..."
```

### Scenario 2: Correct Images
```
✅ Send 2 correct CIN images
✅ Get approval
✅ Batch cleaned up
✅ Move to next step
```

### Scenario 3: Interrupted Flow
```
✅ Send 1 image
✅ Wait 5 seconds
✅ Send text "forget it"
✅ Batch cleaned on text
✅ Get response
```

### Scenario 4: Error Handling
```
✅ Send image that causes error
✅ Error logged
✅ Batch cleaned up even on error
✅ User can try again
```

---

## Logging

### What You'll See in Logs:

**Batch Creation:**
```
📥 [WEBHOOK RECEIVED] From: +216... | Media Count: 1
🆕 [BATCH] Created batch for +216...:NEED_CIN
```

**Batch Collection:**
```
📥 [WEBHOOK RECEIVED] From: +216... | Media Count: 1
📸 [BATCH] Added to batch (2 images total)
```

**Processing:**
```
🔍 [BATCH] Processing 2 images for +216...
✅ [ONBOARDING BG] Message dispatched
```

**Cleanup:**
```
🧹 [CLEANUP] Cleared batch: +216...:NEED_CIN
```

**Stale Cleanup:**
```
🧹 [CLEANUP] Removing stale batch: +216...:NEED_CIN
```

**Text Message Cleanup:**
```
🧹 [CLEANUP] Cleared batch on text message: +216...:NEED_CIN
```

---

## Configuration

### Tunable Parameters:

```python
# Batch collection window
MEDIA_BATCH_WINDOW = 2.0  # seconds

# Stale batch timeout
STALE_TIMEOUT = 10.0  # seconds (in cleanup code)
```

**Recommendations:**
- Keep window at 2 seconds (good for most connections)
- Keep timeout at 10 seconds (prevents stuck batches)

---

## Memory Safety

### Before Fix:
```python
pending_media_batches = {
    "+216...:NEED_CIN": {
        "urls": [...],
        "timestamp": 123456,
        "processed": True  # But not deleted! 🐛
    }
}
# Memory leak! Grows forever!
```

### After Fix:
```python
pending_media_batches = {
    # Empty after processing ✅
    # Only active batches remain
}
# Clean memory, no leaks!
```

---

## System Status: FIXED ✅

### What Works Now:

1. ✅ **Batch cleanup after approval**
2. ✅ **Batch cleanup after rejection**
3. ✅ **Batch cleanup on error**
4. ✅ **Batch cleanup on text message**
5. ✅ **Automatic stale batch removal**
6. ✅ **Memory safe (no leaks)**
7. ✅ **Text messages always work**

### Files Modified:

**`app/main.py`:**
- Added cleanup in `verify_onboarding_step_in_background()`
- Added cleanup in exception handler
- Added cleanup on text messages
- Added stale batch removal at webhook start

---

## Important Notes

⚠️ **Critical:** هاذا fix ضروري جداً! بدونو النظام يتعلق و ما يجاوبش.

✅ **Memory Safe:** الـ batches الآن يتفسخو دائماً (5 طرق مختلفة للتنظيف)

✅ **User Friendly:** المستخدم يقدر يبعث text في أي وقت و يجيه جواب

🎯 **Robust:** حتى في حالة error، الـ batch يتفسخ

---

**النظام الآن robust و memory-safe! 🚀**
