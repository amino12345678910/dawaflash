# Full Derja Translation Update - 100% Tunisian Arabic

## المشكل (The Problem)

**قبل:** الرسائل كانت مخلوطة:
- ✅ بعض الأجزاء Derja Tounsia
- ❌ الرسائل التقنية English (rejection reasons, technical terms)
- ❌ مصطلحات مش مفهومة للمستخدم العادي

**مثال:**
```
❌ Document rejected: The uploaded document is a pharmacy receipt, 
not a Tunisian National Identity Card (CIN).

Brabbi 3awed ab3ath tsawret el CIN...
```

---

## الحل (The Solution)

### ✅ 1. Translation Function
**File:** `app/main.py`

**Function جديدة:** `translate_rejection_to_derja()`

يترجم الأسباب التقنية من English إلى Derja مفهومة:

```python
def translate_rejection_to_derja(step: str, english_reason: str) -> str:
    """Translates technical rejection reasons to user-friendly Tunisian Derja."""
```

**أمثلة للترجمات:**

| English Reason | Derja Translation |
|----------------|-------------------|
| "pharmacy receipt, not CIN" | "Tsawra eli ab3aththa fatora mel pharmacie mech CIN. 🧾" |
| "blurry or unclear" | "Tsawra mech wadh7a barsha. Lazem tkoun clear. 👓" |
| "missing fields" | "Famma ma3loumet me7lela: lazem el esem, rou9em el CIN..." |
| "multiple faces" | "Famma barcha wjoueh fil swar. Lazem selfie wa7dek barka. 👤" |
| "face doesn't match" | "Wjhek ma yetsawwbch m3a tsawret el CIN. 🆔" |
| "not green" | "El carnet lazem yekhdem akhdar. Eli ab3aththa mech akhdar. 🟢" |
| "no CNAM branding" | "Ma fammech logo CNAM walla authentication. 🏥" |

---

### ✅ 2. Enhanced Rejection Messages

#### CIN Rejection (قبل):
```
❌ Document rejected: The uploaded document is a pharmacy receipt...

Brabbi 3awed ab3ath tsawret el CIN...
```

#### CIN Rejection (بعد):
```
❌ *Rafd:* Tsawra eli ab3aththa fatora mel pharmacie mech CIN. 🧾

💡 *Chnouwa lazem:*
Ab3ath tsawer el CIN el Tunisiya mel wjeh w edhar. Lazem tkoun wadh7a w net9raw fiha:
• Esmek el kemel
• Rou9em el CIN (8 ara9em)
• Tarikhet el milad
• Tsawerek

📸 *Conseil:* Swar fil blassa madhya, w rakkez 3al CIN bech tkoun wadh7a. 🪪
```

---

#### Face Rejection (قبل):
```
❌ Document rejected: Face does not match CIN photo...

Brabbi ab3ath tsawer CLEAR...
```

#### Face Rejection (بعد):
```
❌ *Rafd:* Wjhek fil selfie ma yetsawwbch m3a tsawret el CIN. 🆔

💡 *Chnouwa lazem:*
Ab3ath selfie (swar rou7ek) wadh7a:
• Wjhek mel 9oddem mbecher
• 3aynik, mankhrek, w fommek yedhrou el kol
• Blassa madhya (mech dhlam)
• Wa7dek fil swar (mech groupe)
• Bla masque walla nudhdharet chams

🔍 *Mohem:* Bech na9arnou wjhek m3a tsawret el CIN! 📸
```

---

#### CNAM Rejection (قبل):
```
❌ Document rejected: No CNAM branding visible...

Brabbi ab3ath tsawer clear...
```

#### CNAM Rejection (بعد):
```
❌ *Rafd:* Ma fammech logo CNAM walla authentication fil wathi9a. 🏥

💡 *Chnouwa lazem:*
Ab3ath tsawer el Carnet el Akhdar (Carnet Vert) mte3 el CNAM:
• Lazem yekhdem akhdar (CNAM green)
• Lazem fih logo CNAM
• Lazem fih rou9em el beneficiaire
• Lazem fih tabe3 walla taw9i3 rasmi
• Tsawra wadh7a w net9raw fiha

📗 *Conseil:* Carnet CNAM sa7i7 fessel el welaya. 🟢
```

---

### ✅ 3. Enhanced Approval Messages

#### CIN Approval (قبل):
```
✅ Ya3tik essa7a! El CIN mte3ek verified.
Tawa swar rou7ek (selfie)...
```

#### CIN Approval (بعد):
```
✅ *Mabrouk!* El CIN mte3ek t9ablet! 🎉

📋 *Esmek:* [يظهر في الـ CIN]
📅 *Verification:* Sa7i7

➡️ *El 5otwa ejjeya:*
Tawa ab3athli selfie (swar rou7ek) wadh7a mel 9oddem bech na9arnou wjhek m3a tsawret el CIN.

💡 Lazem:
• Wjhek mel 9oddem mbecher
• Blassa madhya
• Wadh7a w net9raw fiha

📸 Yalla swar rou7ek!
```

---

#### Face Approval (بعد):
```
✅ *Perfect!* Wjhek yetsaweb m3a el CIN! 🎉

🔍 *Face Match:* Confirmed ✓
👤 *El Hwya:* Verified

➡️ *El 5otwa el a5ira:*
Tawa bech ncommletou el inscription, ab3athli tsawer clear mte3 el *Carnet el Akhdar* mte3 el CNAM.

💡 Lazem:
• Akhdar el loun (CNAM green)
• Fih logo CNAM
• Wadh7 w net9raw fih

🟢 Yalla 9rib nkammou!
```

---

#### CNAM Approval (بعد):
```
🎊 *MABROUK!* 🎊

✅ El inscription kamlet bne7! El contrat mte3ek bel CNAM w DawaFlash bda rasmyan!

📋 *Status:* VERIFIED ✓
🏥 *CNAM:* Connected
💳 *Plafond:* Active

━━━━━━━━━━━━━━━

🩺 *Tawa chnouwa?*
Fi ay wa9t t7ess rou7ek mridh w t7eb t3addi Matlab Mrayah, ab3athli:

1️⃣ Tsawer el *Bulletin de Soin* (el wara9a el khadhra)
2️⃣ Tsawer el *Ordonnance* (el wasef mte3 el docteur)

W e7na na3mlou el reste! El flous traja3lek direct. 💰

━━━━━━━━━━━━━━━

✨ *DawaFlash* - El da3em mte3ek fi el se7a! 🇹🇳
```

---

### ✅ 4. Claims Processing Messages (All Derja)

#### Auto-Approved Claim (قبل):
```
Ya Amina Ben Ali! 🩺

DawaFlash kammel el processing...

Decision: *AUTO APPROVED* 🎉
🚀 El flous mte3ek t'acceptat w 3addineha lel virement!
```

#### Auto-Approved Claim (بعد):
```
Ahla *Amina Ben Ali*! 🩺

✅ DawaFlash kammel el processing mte3 el Matlab mte3ek!

━━━━━━━━━━━━━━━
📋 *Détails el Fatora:*
- Doliprane: 8.00 DT ✅
- Spasfon: 7.00 DT ✅

💰 *El 7seb:*
• Total el matlab: 15.00 DT
• Montant mwafe9 3lih: 15.00 DT
• Plafond el ba9i: 385.00 DT

━━━━━━━━━━━━━━━
📌 *El 9arar:* T9ABLET AUTOMATIQUEMENT 🎉

🎊 *Mabrouk!*
El matlab mte3ek t9ablet w el flous bech traja3lek direct!

💸 *El montant:* 15.00 DT
🏦 *El virement:* Fi tari9ou (1-3 jours)

✨ Bessahtek w rabi ichafik! 🇹🇳
```

---

#### Manual Review (قبل):
```
Decision: *UNDER MANUAL REVIEW* 🔍
⚠️ Kén famma items mch unlisted, walla fét 100 DT, y7eblou manual review...
```

#### Manual Review (بعد):
```
━━━━━━━━━━━━━━━
📌 *El 9arar:* FI EL CONTROLE EL YÉDAWI 🔍

⚠️ *Chnowa 9a3ed ysir?*
El matlab mte3ek 7atitou fi controle yédawi (manual review) 3and el adjuster bech yetfassed afdhal.

💡 *Liwech?*
• Famma médicaments mech fel liste el rasmiya: XYZMedicine
• El montant kbir barsha (plus que 100 DT)

⏰ Lahdha barka, el adjuster bech y9allem w yji3lek el rep!
```

---

#### Over-Ceiling (قبل):
```
Ya Amina, el Matlab mte3ek fih overspend. El fatora fiha 45.00 DT 
ama el plafond el ba9i mte3ek fih 5.00 DT kahaw. ⚠️
```

#### Over-Ceiling (بعد):
```
Ahla *Amina Ben Ali*! 🩺

⚠️ *Tanbih mohem:*
El matlab mte3ek fih overspend (fa9et el plafond).

💰 *El 7seb:*
• El fatora fiha: 45.00 DT
• El plafond el ba9i: 5.00 DT
• El far9: 40.00 DT zayed

━━━━━━━━━━━━━━━
🔍 *Chnowa 9a3ed ysir?*
7atina el matlab fi *Controle Yédawi* m3a l'adjuster bech yetfassed el mawdhou3 afdhal.

⏰ El adjuster bech ychouf:
• El montant el sa7i7
• El plafond el mutba9
• Chnowa el possible nkhabrou bih

📲 Bech yji3lek el 9arar 9rib inchallah! Sabri chwaya. 🙏
```

---

#### Extraction Failure (قبل):
```
⚠️ *DawaFlash Agent:* We were unable to read any medicine items...
Please upload a clearer photo...
```

#### Extraction Failure (بعد):
```
⚠️ *Mochkla fi el 9raya!*

Ma njamnech na9raw el médicaments w el as3ar mel swar eli ab3aththom.

💡 *El 7al:*
1️⃣ Ab3ath tsawer afdhal (wadh7a, fi blassa madhya)
2️⃣ Walla ektebhomli:
   Mthalan: "Chrit Doliprane b 8 DT w Spasfon b 7 DT"

📸 Lazem tsawer el *Bulletin de Soin* w el *Ordonnance* mte3 el docteur!
```

---

#### Technical Error (قبل):
```
AI Processing Error during OCR: {error}
```

#### Technical Error (بعد):
```
❌ *Mochkla techni9a!*

Famma error wa9et fil système w ma njamnech nkammou el processing.

💡 *Chnouwa ta3mel:*
• 3awed ab3ath el swar ba3d chwaya
• Walla ektebli el médicaments w el as3ar

🛠️ E7na na7lou el mochkel! Sabri chwaya.
```

---

## Message Structure

### الهيكل الموحد للرسائل:

```
[Emoji] *العنوان بالدارجة*

[محتوى مفصل بالدارجة]

━━━━━━━━━━━━━━━  [فاصل اختياري]

💡 *Chnouwa lazem / Liwech / Chnouwa 9a3ed ysir:*
• نقطة 1
• نقطة 2

[نصيحة أو خطوة تالية]

[Emoji ختامي]
```

---

## Benefits للمستخدم

### قبل:
❌ رسائل مخلوطة (English + Derja)
❌ مصطلحات تقنية مش مفهومة
❌ مش واضح ليش رفضوله
❌ مش واضح شنوة يلزمو يعمل

### بعد:
✅ **100% Derja Tounsia** - لغة مفهومة
✅ **شرح واضح** - ليش رفضوله
✅ **خطوات محددة** - شنوة يلزمو
✅ **Emojis مساعدة** - visual cues
✅ **Tone ودود** - مش رسمي زيادة
✅ **Structured** - منظم و سهل قراتو

---

## Terminology Updates

### التحديثات في المصطلحات:

| English | Old | New (Derja) |
|---------|-----|-------------|
| Document rejected | Document rejected | ❌ *Rafd* |
| Required | You must | 💡 *Lazem* / *Chnouwa lazem* |
| Reason | Because | *Liwech?* |
| What's happening | Status | *Chnowa 9a3ed ysir?* |
| Next step | Next | ➡️ *El 5otwa ejjeya* |
| Advice/Tip | Note | 📸 *Conseil* |
| Verified | Verified | ✅ Sa7i7 / T9ablet |
| Manual Review | UNDER MANUAL REVIEW | FI EL CONTROLE EL YÉDAWI |
| Auto-Approved | AUTO APPROVED | T9ABLET AUTOMATIQUEMENT |
| Processing Error | Error | ❌ *Mochkla techni9a* |

---

## User Experience Improvements

### 1. Clarity (الوضوح)
**قبل:** "The uploaded document is a pharmacy receipt"
**بعد:** "Tsawra eli ab3aththa fatora mel pharmacie mech CIN"

### 2. Actionable (قابل للتنفيذ)
**قبل:** Generic "please upload clear photo"
**بعد:** 
```
💡 *Chnouwa lazem:*
• Wjhek mel 9oddem mbecher
• Blassa madhya
• Bla masque
```

### 3. Empathy (التعاطف)
**قبل:** Cold technical message
**بعد:** "Sabri chwaya, el adjuster bech y9allem w yji3lek el rep! 🙏"

### 4. Cultural (ثقافي)
**بعد:** "Bessahtek w rabi ichafik! 🇹🇳"

---

## System Status: 100% Derja ✅

### الآن كل شيء Derja:
1. ✅ **Onboarding messages** - CIN, Face, CNAM
2. ✅ **Rejection reasons** - مترجمة للدارجة
3. ✅ **Approval messages** - واضحة و مفهومة
4. ✅ **Claims processing** - من البداية للنهاية
5. ✅ **Error messages** - user-friendly
6. ✅ **Instructions** - خطوة بخطوة بالدارجة

### Files Modified:
- **`app/main.py`** - Translation function + all onboarding messages
- **`app/services/agents.py`** - All claims processing messages

---

## Testing Checklist

### Onboarding:
- [ ] CIN rejection → Derja clear + instructions
- [ ] CIN approval → Derja + next step
- [ ] Face rejection → Derja + reasons
- [ ] Face approval → Derja + excitement
- [ ] CNAM rejection → Derja + what's needed
- [ ] CNAM approval → Full Derja celebration

### Claims:
- [ ] Auto-approved → 100% Derja
- [ ] Manual review → Derja explanation
- [ ] Over-ceiling → Derja + clear numbers
- [ ] Extraction error → Derja + solutions
- [ ] Technical error → Derja + reassurance

**كل شيء جاهز بالدارجة التونسية! 🇹🇳** ✨
