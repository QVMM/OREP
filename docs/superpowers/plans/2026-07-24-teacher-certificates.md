# Teacher Certificates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the existing certificate foundation with teacher issuance, generated PDFs, uploaded files, history, revocation, and secure student downloads.

**Architecture:** Extend the existing certificate tables and `TeacherGrowthService`; do not create a competing award model. A dedicated file service owns validation, storage, PDF rendering, and authorized download. The teacher team workspace supplies recipients and issuance history; the existing student profile remains the recipient view.

**Tech Stack:** Java 21, Spring Boot 3.2, OpenPDF, multipart upload, Flyway/MySQL, Vue 3, Vite.

---

### Task 1: Certificate Metadata Migration

**Files:**
- Create: `backend/src/main/resources/db/migration/V106__certificate_sources_and_files.sql`

- [ ] **Step 1: Add nullable compatibility fields**

```sql
ALTER TABLE student_certificate
    ADD COLUMN source_type VARCHAR(24) NULL AFTER certificate_type,
    ADD COLUMN award_level VARCHAR(64) NULL AFTER description,
    ADD COLUMN issuer_name VARCHAR(160) NULL AFTER issuer_user_id,
    ADD COLUMN original_file_name VARCHAR(255) NULL AFTER pdf_url,
    ADD COLUMN mime_type VARCHAR(120) NULL AFTER original_file_name;

UPDATE student_certificate
SET source_type = 'UPLOADED'
WHERE source_type IS NULL;
```

- [ ] **Step 2: Verify migration against a schema copy**

Run the migration in the backend test context and assert existing certificate
rows remain readable.

### Task 2: File and PDF Service

**Files:**
- Create: `backend/src/main/java/com/orep/backend/service/CertificateFileService.java`
- Test: `backend/src/test/java/com/orep/backend/service/CertificateFileServiceTest.java`

- [ ] **Step 1: Write failing validation and PDF tests**

Cover PDF/PNG/JPG acceptance, executable rejection, random stored names, and a
generated PDF containing embedded Chinese text.

- [ ] **Step 2: Run tests and verify RED**

Run: `cd backend && mvn -Dtest=CertificateFileServiceTest test`

Expected: service class is absent.

- [ ] **Step 3: Implement controlled storage**

Store files below `${OREP_STORAGE_ROOT}/certificates`, cap size using the
existing upload policy, and never concatenate the original filename into the
disk path.

- [ ] **Step 4: Implement generated PDF**

Use OpenPDF and the existing Chinese font discovery rules. Render title,
recipient display name, description, award level, issuer, issue date, and
certificate number. Fail with a clear response when no embeddable Chinese font
is available.

- [ ] **Step 5: Run tests and verify GREEN**

Run: `cd backend && mvn -Dtest=CertificateFileServiceTest test`

Expected: all tests pass.

### Task 3: Issuance, History, Revocation, Download

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/service/TeacherGrowthService.java`
- Modify: `backend/src/main/java/com/orep/backend/controller/TeacherGrowthController.java`
- Modify: `backend/src/main/java/com/orep/backend/service/StudentProfileService.java`
- Test: `backend/src/test/java/com/orep/backend/controller/TeacherGrowthControllerTest.java`

- [ ] **Step 1: Add failing endpoint tests**

Cover generated issuance, uploaded issuance, automatic unique number, multiple
users, team recipient, history listing, revocation, and unauthorized download.

- [ ] **Step 2: Run tests and verify RED**

Run: `cd backend && mvn -Dtest=TeacherGrowthControllerTest test`

Expected: multipart, list, revoke, and download endpoints are missing.

- [ ] **Step 3: Add API surface**

```text
GET    /api/teacher/student-growth/teams/{teamId}/certificates
POST   /api/teacher/student-growth/certificates/generated
POST   /api/teacher/student-growth/certificates/uploaded
DELETE /api/teacher/student-growth/certificates/{certificateId}
GET    /api/student-profile/certificates/{certificateId}/download
```

- [ ] **Step 4: Enforce tenant and recipient scope**

Teachers may issue only to accessible teams/members. Students may download only
an active certificate addressed to them or one of their active teams. Revocation
sets `status='REVOKED'` and retains rows/files.

- [ ] **Step 5: Run tests and verify GREEN**

Run: `cd backend && mvn -Dtest=TeacherGrowthControllerTest,StudentProfileControllerTest test`

Expected: all focused tests pass.

### Task 4: Teacher Certificate Workspace

**Files:**
- Modify: `frontend/teacher/src/api/index.js`
- Modify: `frontend/teacher/src/views/team/TeamWorkspaceView.vue`

- [ ] **Step 1: Add API helpers**

Add history, generated issuance, uploaded issuance, and revoke helpers. Use
`FormData` only for uploaded mode.

- [ ] **Step 2: Add the “奖状” team tab**

Display active/revoked history with recipient, source, issue date, preview,
download, and revoke actions.

- [ ] **Step 3: Add one issuance drawer**

Use a segmented mode selector (“系统生成” / “上传奖状”), recipient checkboxes,
team-recipient option, title, level, description, issuer, date, and file input
for upload mode. Submit only fields valid for the selected mode.

- [ ] **Step 4: Build teacher frontend**

Run: `cd frontend/teacher && npm run build`

Expected: Vite exits 0.

### Task 5: Student Profile Download

**Files:**
- Modify: `frontend/user/src/views/Profile.vue`
- Test: `frontend/user/tests/student-certificate.spec.js`

- [ ] **Step 1: Add failing UI contract test**

Assert active generated and uploaded awards render, revoked awards do not, and
download uses the authorized endpoint instead of a raw disk path.

- [ ] **Step 2: Run test and verify RED**

Run: `cd frontend/user && npx playwright test tests/student-certificate.spec.js --reporter=line`

Expected: current profile still uses raw `pdfUrl`.

- [ ] **Step 3: Switch to authorized downloads**

Keep the existing preview, add source/level metadata, and point download to
`/api/student-profile/certificates/{id}/download`.

- [ ] **Step 4: Run test and build**

Run: `cd frontend/user && npx playwright test tests/student-certificate.spec.js --reporter=line && npm run build`

Expected: test and build pass.

### Task 6: Integrated Verification

**Files:**
- Verify only; no new files.

- [ ] **Step 1: Run focused backend tests and package**

Run: `cd backend && mvn -Dtest=CertificateFileServiceTest,TeacherGrowthControllerTest,StudentProfileControllerTest test && mvn -DskipTests package`

Expected: zero test failures and the backend JAR is produced.

- [ ] **Step 2: Deploy affected services**

Rebuild/recreate `backend`, `frontend-user`, and `frontend-teacher` only. Preserve
database volumes and the production resource directory.

- [ ] **Step 3: Verify production end to end**

Issue one generated test award and one uploaded test award to a controlled test
account, verify student preview/download, revoke them, and confirm they disappear
from the active student list while remaining in teacher history.
