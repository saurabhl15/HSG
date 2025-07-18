# Product Requirements Document (PRD)

## Project Title: Real-Time Multilingual Sermon Translation Platform

## Overview

This project aims to build a cloud-based real-time audio translation solution for live sermons delivered in English. The system will translate speech into Hindi, Telugu, and Kannada, convert it to natural-sounding audio using Text-to-Speech (TTS), and make it available to church attendees via a Subsplash-based mobile app.

---

## 1. Goals and Objectives

- Enable seamless, real-time sermon translation from English to three Indian languages.
- Deliver translated audio to users via a mobile app with low latency (acceptable delay: 2-3 seconds).
- Provide high accuracy and naturalness using cloud-based ASR, translation, and TTS APIs.
- Support 20–30 hours of sermon translation per month within a monthly cost of \~INR 20,000.

---

## 2. Use Cases

### Use Case 1: Live Sermon Translation (Zoom Input)

**Actor:** Pastor, Technical Team
**Description:** Pastor speaks in English via Zoom. The system listens, translates, and streams audio in Hindi, Telugu, and Kannada.

### Use Case 2: In-Church Streaming (Mic Input)

**Actor:** Pastor, Congregation
**Description:** Sermon is captured via local microphone. Translated audio is sent to a user friendly app.

### Use Case 3: App-Based Audio Access

**Actor:** Congregant
**Description:** User opens the  app, selects their preferred language, and listens to the translated sermon in real-time.

---

## 3. Key Requirements

### Functional Requirements

- Real-time ASR (Speech-to-Text) from English audio
- Real-time translation to Hindi, Telugu, and Kannada
- Real-time TTS for translated text
- WebRTC or HLS streaming of TTS audio
- Backend management of input, translation logic, and audio output
- Embedded audio player or WebView support in Subsplash app

### Non-Functional Requirements

- Latency target: under 3 seconds end-to-end
- Accuracy target: >90% sentence-level translation quality
- Scalability: Up to 5 concurrent listeners per language per sermon
- Cloud cost target: under INR 20,000/month

---

## 4. Architecture Components

1. **Input Capture Layer**
   - Audio capture via Zoom/OBS/WebRTC or Mic - Already done in church; check for improvements possible
2. **ASR Layer**
   - Azure Speech SDK for real-time English transcription
3. **Chunker Module**
   - Rule-based segmentation of speech for translation
   - Future upgrade: AI-based clause/sentence boundary detection
4. **Translation Layer**
   - Azure Translator API (optional: fine-tuned Custom Translator)
5. **TTS Layer**
   - Azure Neural TTS (hi-IN, te-IN, kn-IN voices)
6. **Audio Streamer**
   - WebRTC for low latency or HLS for simpler client-side integration
7. **Mobile Delivery Layer**
   - WebView/Audio player inside Subsplash
8. **Admin Dashboard (Optional for v1.0)**
   - Monitor latency, audio quality, and translation accuracy

---

## 5. Milestones and Timeline

### Phase 1: Backend Core (Week )

-

### Phase 2: Real-Time Audio Streaming, Infra (Week )

-

### Phase 3: App Integration (Week )

-

### Phase 4: End-to-End Testing (Week )

-

### Phase 5: Optimization + Scaling (Week )

-

---

## 6. Open Questions

- Does Subsplash allow embedding direct audio players or only URL links?
- Will Zoom be used live always, or will OBS/local mic sometimes replace it?
- Do we need archive/download options for translated audio?
- Will there be a fallback or "subtitle-only" mode for poor network conditions? Or other Disaster Recovery scenarios.
- Who manages glossary/translation tuning — tech team or translators?

---

## 7. Success Metrics

- Latency: <3s per chunk
- Translation accuracy: >90% semantic accuracy (via human eval)
- Uptime during sermon: >99%
- Listener satisfaction (post-pilot survey): >80% positive

---

## 8. Notes

- MVP will prioritize Hindi stream. Telugu and Kannada can trail by one milestone.
- Future enhancements may include voice cloning or sermon archiving.

