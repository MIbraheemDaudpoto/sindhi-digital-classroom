# Sindhi Digital Classroom (SDC) - Security & Child Privacy Policy

Authored under **agency-application-security-engineer** following ECC `agent-security-hardening` and international child privacy safeguards (COPPA, FERPA, UNICEF guidelines).

---

## 1. Child Data Protection & Privacy Principles

SDC is deployed in rural contexts serving minor students (Class 6 to 10), often on shared family or school devices. Data protection is built into the architecture:

### 1.1 Zero PII Policy for Students
- **No Real Names:** Students are identified strictly by `school_code` + `student_code` (e.g. `SCH-HYD-01` + `STU-104`).
- **No Photos or Biometrics:** SDC prohibits photo uploads or profile pictures of minor students.
- **Hashed Authentication PINs:** Student 4-digit PINs are hashed using PBKDF2/SHA256 with cryptographic salt before storage.
- **No Home Address Collection:** GPS location, device MAC addresses, and physical addresses are never queried or stored.

### 1.2 Audio & Voice Data Governance
- Speech samples collected for ASR fine-tuning require **explicit Guardian Consent and Child Assent** stored in the `consents` table.
- Audio recordings are anonymized with pseudonymous speaker codes and stripped of environmental metadata.
- Female student voice recordings are strictly restricted to authorized research personnel with gender-matched data handling protocols.

### 1.3 Anonymized Data Export (FR-36)
- Education department and research exports format all progress, quiz scores, and Cohen's d learning gains into CSVs with zero student identifiers.

---

## 2. Role-Based Access Control (RBAC) Matrix (FR-02)

| Permission / Page | Student (`STUDENT`) | Teacher (`TEACHER`) | Admin (`ADMIN`) | Officer (`OFFICER`) |
| :--- | :---: | :---: | :---: | :---: |
| Browse & Watch Lessons | Yes | Yes | Yes | Yes |
| Take Smart Video Quizzes | Yes | No | No | No |
| Ask AI Tutor | Yes | Yes | Yes | No |
| Upload Video & Transcripts (FR-09) | No | Yes | Yes | No |
| Approve / Edit Draft Questions (FR-13)| No | Yes | Yes | No |
| View Class Results & Weak Topics (FR-30)| No | Yes (Assigned) | Yes | No |
| View District Summary Dashboards (FR-31)| No | No | Yes | Yes |
| Manage School Accounts & Consents | No | No | Yes | No |
| Audit Logs & Content Retiring (FR-34, FR-35)| No | No | Yes | No |

---

## 3. Shared-Device Security (FR-03)
- Quick user switch clears session tokens from localStorage and memory immediately.
- Offline IndexedDB partitions learning attempts and quiz state by student ID to prevent sibling or classmate data crossover.
