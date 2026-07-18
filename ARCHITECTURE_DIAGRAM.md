# DawaFlash - System Architecture Diagram

## Visual Architecture (Text Format - Convert to PDF/Image)

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                          DAWAFLASH ARCHITECTURE                              ║
║                   AI-Powered WhatsApp Insurance Platform                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌───────────────┐         ┌───────────────┐        ┌──────────────┐     │
│   │   WhatsApp    │         │   WhatsApp    │        │   WhatsApp   │     │
│   │   User A      │         │   User B      │        │   User C     │     │
│   │  📱 Tunisia   │         │  📱 Tunisia   │        │  📱 Tunisia  │     │
│   └───────┬───────┘         └───────┬───────┘        └──────┬───────┘     │
│           │                         │                        │              │
│           └─────────────────────────┴────────────────────────┘              │
│                                     │                                        │
└─────────────────────────────────────┼────────────────────────────────────────┘
                                      │
                                      │ HTTPS (Messages + Images)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         COMMUNICATION GATEWAY                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                    ┌────────────────────────────────┐                       │
│                    │    Twilio WhatsApp API         │                       │
│                    │                                │                       │
│                    │  • Webhook Receiver            │                       │
│                    │  • Media URL Provider          │                       │
│                    │  • Message Sender (Out-of-band)│                       │
│                    │  • Auth: SID + Token           │                       │
│                    └──────────┬──────────┬──────────┘                       │
│                               │          │                                   │
└───────────────────────────────┼──────────┼───────────────────────────────────┘
                                │          │
                  POST /webhook │          │ Send Message API
                                ▼          │
┌─────────────────────────────────────────────────────────────────────────────┐
│                         APPLICATION LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                      FASTAPI BACKEND SERVER                           │ │
│  │                      (Python 3.11 + Uvicorn)                          │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │                                                                        │ │
│  │   ┌──────────────────────────────────────────────────────────────┐   │ │
│  │   │              WEBHOOK HANDLER (app/main.py)                   │   │ │
│  │   │                                                               │   │ │
│  │   │  • Receive: From, Body, NumMedia, MediaUrl0-3              │   │ │
│  │   │  • Parse phone number & user state                          │   │ │
│  │   │  • Media batching (2-second window)                         │   │ │
│  │   │  • Background task scheduling                               │   │ │
│  │   │  • TwiML response generation                                │   │ │
│  │   └────────────────────┬─────────────────────────────────────────┘   │ │
│  │                        │                                              │ │
│  │   ┌────────────────────▼──────────────────┬──────────────────────┐   │ │
│  │   │                                        │                      │   │ │
│  │   ▼                                        ▼                      ▼   │ │
│  │  ┌────────────────┐    ┌───────────────────────┐   ┌──────────────┐ │ │
│  │  │   ONBOARDING   │    │  CLAIMS PROCESSING    │   │  UTILITIES   │ │ │
│  │  │     ENGINE     │    │       ENGINE          │   │              │ │ │
│  │  │                │    │                       │   │ • Derja      │ │ │
│  │  │ • CIN Verify   │    │ • OCR Extraction      │   │   Translation│ │ │
│  │  │ • Face Match   │    │ • Tariff Validation   │   │ • Batch Mgmt │ │ │
│  │  │ • CNAM Check   │    │ • Fraud Detection     │   │ • Cleanup    │ │ │
│  │  │ • State Update │    │ • Ceiling Management  │   │              │ │ │
│  │  └───────┬────────┘    └───────┬───────────────┘   └──────────────┘ │ │
│  │          │                     │                                      │ │
│  └──────────┼─────────────────────┼──────────────────────────────────────┘ │
│             │                     │                                        │
│             └──────────┬──────────┘                                        │
│                        │                                                   │
└────────────────────────┼───────────────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┬───────────────────┐
         │               │               │                   │
         ▼               ▼               ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SERVICE LAYER                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐   ┌──────────────────┐   ┌─────────────────────┐    │
│  │  AI/ML SERVICES  │   │  DATABASE        │   │  MESSAGING          │    │
│  │                  │   │                  │   │                     │    │
│  │  ┌────────────┐  │   │  ┌────────────┐ │   │  ┌───────────────┐ │    │
│  │  │  Gemini    │  │   │  │   SQLite   │ │   │  │ Twilio Client │ │    │
│  │  │  Vision AI │  │   │  │     DB     │ │   │  │  (REST API)   │ │    │
│  │  │            │  │   │  │            │ │   │  │               │ │    │
│  │  │ Features:  │  │   │  │  Tables:   │ │   │  │ Functions:    │ │    │
│  │  │ • OCR      │  │   │  │  • users   │ │   │  │ • Send msg    │ │    │
│  │  │ • Doc      │  │   │  │  • policies│ │   │  │ • Async       │ │    │
│  │  │   Verify   │  │   │  │  • claims  │ │   │  │ • Out-of-band │ │    │
│  │  │ • Face     │  │   │  │  • tariffs │ │   │  └───────────────┘ │    │
│  │  │   Match    │  │   │  │  • sessions│ │   │                     │    │
│  │  │ • Multi-   │  │   │  │            │ │   └─────────────────────┘    │
│  │  │   Image    │  │   │  │  Storage:  │ │                               │
│  │  └────────────┘  │   │  │  • Images  │ │                               │
│  │                  │   │  │    (BLOBs) │ │                               │
│  │  Model:          │   │  │  • Hashes  │ │                               │
│  │  gemini-3.5-     │   │  │  • States  │ │                               │
│  │  flash           │   │  └────────────┘ │                               │
│  │                  │   │                  │                               │
│  │  API: REST       │   │  ACID Compliant │                               │
│  │  Temp: 0         │   │  Row Factory    │                               │
│  └──────────────────┘   └──────────────────┘                               │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    IMAGE PROCESSING                                  │  │
│  │                                                                       │  │
│  │  ┌─────────────┐           ┌──────────────────┐                     │  │
│  │  │   Pillow    │           │  ImageHash       │                     │  │
│  │  │   (PIL)     │           │  (pHash)         │                     │  │
│  │  │             │           │                  │                     │  │
│  │  │ • Image     │           │ • Perceptual     │                     │  │
│  │  │   Load      │───────────▶  Hashing         │                     │  │
│  │  │ • Resize    │           │ • Hamming        │                     │  │
│  │  │ • Format    │           │   Distance       │                     │  │
│  │  │   Convert   │           │ • Duplicate      │                     │  │
│  │  └─────────────┘           │   Detection      │                     │  │
│  │                            └──────────────────┘                     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
                              DATA FLOW DIAGRAMS
═══════════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────────────┐
│                      ONBOARDING FLOW (User KYC)                              │
└─────────────────────────────────────────────────────────────────────────────┘

  User                 WhatsApp            FastAPI            Gemini         DB
   │                      │                   │                 │            │
   │──[Send CIN photos]──▶│                   │                 │            │
   │                      │──[Webhook]───────▶│                 │            │
   │                      │                   │                 │            │
   │                      │◀──[Ack: "Received"]──│              │            │
   │◀─────────────────────│                   │                 │            │
   │                      │                   │                 │            │
   │                      │              [Batch images 2s]      │            │
   │                      │                   │                 │            │
   │                      │              [Download from Twilio] │            │
   │                      │                   │                 │            │
   │                      │                   │──[Verify CIN]──▶│            │
   │                      │                   │                 │            │
   │                      │                   │◀──[Valid:true]──│            │
   │                      │                   │                 │            │
   │                      │                   │──[Store image]─────────────▶│
   │                      │                   │                 │            │
   │                      │                   │──[Update state]────────────▶│
   │                      │                   │                 │            │
   │                      │◀──[Send approval]─│                 │            │
   │◀─────[✅ Approved]───│                   │                 │            │
   │                      │                   │                 │            │
   │──[Send face photo]──▶│                   │                 │            │
   │                      │──[Webhook]───────▶│                 │            │
   │                      │                   │                 │            │
   │                      │                   │◀─[Get CIN img]────────────  │
   │                      │                   │                 │            │
   │                      │                   │──[Compare faces]───────────▶│
   │                      │                   │                 │            │
   │                      │                   │◀──[Match:true]──│            │
   │                      │                   │                 │            │
   │                      │◀──[Send approval]─│                 │            │
   │◀──[✅ Face matched]──│                   │                 │            │
   │                      │                   │                 │            │
   │──[Send CNAM card]───▶│                   │                 │            │
   │                      │──[Webhook]───────▶│                 │            │
   │                      │                   │                 │            │
   │                      │                   │──[Verify CNAM]─▶│            │
   │                      │                   │                 │            │
   │                      │                   │◀──[Valid:true]──│            │
   │                      │                   │   [Extract ID]  │            │
   │                      │                   │                 │            │
   │                      │                   │──[Store + Update state]────▶│
   │                      │                   │   (Status: VERIFIED)         │
   │                      │                   │                 │            │
   │                      │◀──[Send welcome]──│                 │            │
   │◀──[🎊 VERIFIED!]─────│                   │                 │            │
   │                      │                   │                 │            │


┌─────────────────────────────────────────────────────────────────────────────┐
│                      CLAIMS PROCESSING FLOW                                  │
└─────────────────────────────────────────────────────────────────────────────┘

  User              WhatsApp         FastAPI        Gemini      ImageHash    DB
   │                   │                │             │             │         │
   │─[Send receipt]───▶│                │             │             │         │
   │                   │──[Webhook]────▶│             │             │         │
   │                   │                │             │             │         │
   │                   │◀─[Ack msg]─────│             │             │         │
   │◀──["Processing"]──│                │             │             │         │
   │                   │                │             │             │         │
   │                   │          [Download image]    │             │         │
   │                   │                │             │             │         │
   │                   │                │──────────────────────────▶│         │
   │                   │                │      [Calculate pHash]    │         │
   │                   │                │◀─────────────────────────│         │
   │                   │                │                           │         │
   │                   │                │───────[Check duplicates]─────────▶│
   │                   │                │                           │         │
   │                   │                │◀──────[Not duplicate]────────────│
   │                   │                │                           │         │
   │                   │                │──[OCR Extract]──▶│        │         │
   │                   │                │     items+prices │        │         │
   │                   │                │                  │        │         │
   │                   │                │◀──[Items JSON]───│        │         │
   │                   │                │                  │        │         │
   │                   │                │◀─────────[Lookup tariffs]────────│
   │                   │                │      [Apply caps]         │         │
   │                   │                │      [Check ceiling]      │         │
   │                   │                │      [Fraud scoring]      │         │
   │                   │                │                           │         │
   │                   │          [Decision: AUTO_APPROVED]         │         │
   │                   │                │                           │         │
   │                   │                │──[Record claim]──────────────────▶│
   │                   │                │  [Update ceiling_used]            │
   │                   │                │                           │         │
   │                   │◀─[Send result]─│                           │         │
   │◀──[✅ Approved]───│                │                           │         │
   │   [15 TND paid]   │                │                           │         │
   │                   │                │                           │         │


═══════════════════════════════════════════════════════════════════════════════
                              COMPONENT DETAILS
═══════════════════════════════════════════════════════════════════════════════

┌──────────────────────────────────────────────────────────────────────┐
│                    MEDIA BATCHING MECHANISM                           │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Timeline (2-second batching window):                                │
│                                                                       │
│  t=0.0s    │  Image 1 arrives  │ Create batch, timestamp=0.0       │
│            │                   │ Reply: "5dhina tsawra (1)..."      │
│            │                   │ Schedule: process_after_2s()       │
│            │                   │                                     │
│  t=0.5s    │  Image 2 arrives  │ Add to batch                       │
│            │                   │ Reply: "5dhina tsawra (2)..."      │
│            │                   │                                     │
│  t=1.2s    │  Image 3 arrives  │ Add to batch                       │
│            │                   │ Reply: "5dhina tsawra (3)..."      │
│            │                   │                                     │
│  t=2.5s    │  Window closes    │ Process ALL 3 images together     │
│            │                   │ Send ONE final response            │
│            │                   │ Cleanup batch from memory          │
│            │                   │                                     │
│  Cleanup Triggers:                                                   │
│  • After processing (success/reject)                                │
│  • On error/exception                                                │
│  • On text message (clear stuck batches)                            │
│  • Timeout: 10 seconds (stale removal)                              │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘


┌──────────────────────────────────────────────────────────────────────┐
│                    FRAUD DETECTION PIPELINE                           │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Layer 1: DUPLICATE DETECTION                                        │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ pHash Algorithm                                                │ │
│  │  1. Load image → Convert to grayscale                         │ │
│  │  2. Resize to 32x32 (standardize)                             │ │
│  │  3. Apply DCT (Discrete Cosine Transform)                     │ │
│  │  4. Extract low-frequency components                          │ │
│  │  5. Generate 16-character hex hash                            │ │
│  │  6. Compare with database: Hamming distance ≤ 4 = DUPLICATE  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  Layer 2: TARIFF VALIDATION                                          │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ For each extracted item:                                       │ │
│  │  1. Lookup in tariffs table (case-insensitive)               │ │
│  │  2. If found: min(requested, max_reimbursable)               │ │
│  │  3. If not found: Flag as UNKNOWN_ITEMS (+0.3 fraud score)   │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  Layer 3: CEILING ENFORCEMENT                                        │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ remaining = ceiling_total - ceiling_used                       │ │
│  │ payout = min(assessed_amount, remaining)                       │ │
│  │ if assessed > remaining: Flag CEILING_EXCEEDED (+0.3)         │ │
│  │ if remaining < 10 TND: Flag CEILING_NEAR (+0.1)               │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  Layer 4: RULE-BASED SCORING                                         │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ fraud_score = 0.0                                              │ │
│  │ if unknown_items: +0.3                                         │ │
│  │ if over_ceiling: +0.3                                          │ │
│  │ if near_ceiling: +0.1                                          │ │
│  │ if total > 100 TND: +0.2                                       │ │
│  │                                                                │ │
│  │ Decision:                                                      │ │
│  │  fraud_score == 0.0 → AUTO_APPROVED                           │ │
│  │  fraud_score > 0.0 → MANUAL_REVIEW                            │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
                          DEPLOYMENT ARCHITECTURE
═══════════════════════════════════════════════════════════════════════════════

                        ┌─────────────────────┐
                        │   Users (WhatsApp)  │
                        └──────────┬──────────┘
                                   │
                                   │ HTTPS
                                   ▼
                        ┌─────────────────────┐
                        │  Twilio API Gateway │
                        └──────────┬──────────┘
                                   │
                                   │ POST /webhook
                                   ▼
            ┌──────────────────────────────────────────┐
            │         Internet / Firewall              │
            └──────────────────┬───────────────────────┘
                               │
                               │ Port 443
                               ▼
            ┌──────────────────────────────────────────┐
            │         Nginx (Reverse Proxy)            │
            │  • SSL/TLS Termination                   │
            │  • Load Balancing                        │
            │  • Static file serving                   │
            └──────────────────┬───────────────────────┘
                               │
                               │ Port 8000
                               ▼
            ┌──────────────────────────────────────────┐
            │    FastAPI Application Server            │
            │    (Uvicorn ASGI)                        │
            │                                          │
            │  • 4 worker processes                   │
            │  • Async event loop                     │
            │  • Background task queue                │
            └──────────┬───────────┬───────────────────┘
                       │           │
            ┌──────────▼────┐  ┌───▼──────────────┐
            │   SQLite DB   │  │  External APIs   │
            │  (Persistent) │  │  • Gemini        │
            │               │  │  • Twilio        │
            └───────────────┘  └──────────────────┘


Production Stack Recommendations:
┌─────────────────────────────────────────────────────────────┐
│ Component          │ Development      │ Production          │
├─────────────────────────────────────────────────────────────┤
│ Web Server         │ Uvicorn          │ Nginx + Uvicorn     │
│ Database           │ SQLite           │ PostgreSQL          │
│ Process Manager    │ Manual           │ Supervisor/systemd  │
│ SSL/TLS            │ None (HTTP)      │ Let's Encrypt       │
│ Monitoring         │ Logs             │ Prometheus/Grafana  │
│ Error Tracking     │ Console          │ Sentry              │
│ Caching            │ None             │ Redis               │
│ File Storage       │ Local Disk       │ S3/Cloud Storage    │
└─────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
                              SECURITY LAYERS
═══════════════════════════════════════════════════════════════════════════════

┌──────────────────────────────────────────────────────────────────────┐
│                         SECURITY ARCHITECTURE                         │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Layer 1: TRANSPORT SECURITY                                         │
│  • HTTPS/TLS 1.3 for all API calls                                  │
│  • Twilio webhook signature verification                             │
│  • Certificate pinning (optional)                                    │
│                                                                       │
│  Layer 2: AUTHENTICATION & AUTHORIZATION                             │
│  • Phone number as user identifier                                   │
│  • Twilio SID + Auth Token for API                                  │
│  • Gemini API key for AI services                                    │
│  • State-based access control (onboarding gates)                    │
│                                                                       │
│  Layer 3: DATA PROTECTION                                            │
│  • Sensitive images stored as BLOBs                                  │
│  • Database encryption (SQLCipher recommended)                       │
│  • At-rest encryption for disk volumes                               │
│  • PII redaction in logs                                             │
│                                                                       │
│  Layer 4: FRAUD PREVENTION                                           │
│  • Perceptual hashing (duplicate detection)                          │
│  • Tariff validation (price cap enforcement)                         │
│  • Ceiling limits (annual maximum)                                   │
│  • Rule-based fraud scoring                                          │
│  • Manual review queue                                               │
│                                                                       │
│  Layer 5: APPLICATION SECURITY                                       │
│  • Input validation (phone numbers, amounts)                         │
│  • SQL injection prevention (parameterized queries)                  │
│  • XSS prevention (input sanitization)                               │
│  • Rate limiting (per user, per endpoint)                            │
│  • Image size limits (max 10MB)                                      │
│                                                                       │
│  Layer 6: MONITORING & AUDIT                                         │
│  • All claims logged with timestamps                                 │
│  • Fraud attempts recorded                                           │
│  • State transitions audited                                         │
│  • Error tracking (Sentry recommended)                               │
│  • Performance monitoring (APM)                                      │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
                         TECHNOLOGY STACK SUMMARY
═══════════════════════════════════════════════════════════════════════════════

Backend Framework:    FastAPI 0.111.0 (Python 3.11+)
ASGI Server:          Uvicorn 0.30.1
Database:             SQLite 3 (dev), PostgreSQL (prod)
AI/ML:                Google Gemini 3.5 Flash
Messaging:            Twilio WhatsApp API
Image Processing:     Pillow 10.3.0 + imagehash 4.3.1
Environment:          python-dotenv 1.0.1
Validation:           Pydantic 2.7.4

Dependencies:
├─ fastapi==0.111.0
├─ uvicorn==0.30.1
├─ google-generativeai==0.8.3
├─ twilio==9.1.0
├─ pydantic==2.7.4
├─ python-dotenv==1.0.1
├─ imagehash==4.3.1
└─ Pillow==10.3.0


═══════════════════════════════════════════════════════════════════════════════
            END OF ARCHITECTURE DIAGRAM - DAWAFLASH v1.0
═══════════════════════════════════════════════════════════════════════════════
```

**Convert to Visual Diagram:**
- Use Draw.io (diagrams.net)
- Use Lucidchart
- Use Microsoft Visio
- Export as PDF or PNG

**Color Scheme Recommendation:**
- User Layer: Blue (#3498db)
- Communication Layer: Green (#2ecc71)
- Application Layer: Orange (#e67e22)
- Service Layer: Purple (#9b59b6)
- Data Layer: Gray (#95a5a6)
- Security: Red (#e74c3c)
