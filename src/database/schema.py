"""SQLite relational schema for Sindhi Digital Classroom (SDC).
Enforces foreign keys, indexing, and WAL mode.
Authored under agency-database-optimizer and agency-application-security-engineer.
"""

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schools (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    district TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_schools_code ON schools(code);
CREATE INDEX IF NOT EXISTS idx_schools_district ON schools(district);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    role TEXT NOT NULL, -- STUDENT, TEACHER, ADMIN, OFFICER
    school_id TEXT,
    pseudonymous_code TEXT UNIQUE NOT NULL, -- Student code or Teacher username
    full_name TEXT,
    school_name_custom TEXT,
    city TEXT,
    pin_hash TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    language TEXT DEFAULT 'sindhi',
    revocation_cutoff_epoch REAL DEFAULT 0.0,
    created_at TEXT NOT NULL,
    FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_code ON users(pseudonymous_code);
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_school ON users(school_id);
CREATE INDEX IF NOT EXISTS idx_users_revocation ON users(id, revocation_cutoff_epoch);

CREATE TABLE IF NOT EXISTS student_invites (
    code_hash TEXT PRIMARY KEY,
    school_id TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used_by TEXT,
    used_at TEXT,
    FOREIGN KEY(school_id) REFERENCES schools(id) ON DELETE SET NULL,
    FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(used_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_student_invites_expiry ON student_invites(expires_at, used_at);

CREATE TABLE IF NOT EXISTS courses (
    id TEXT PRIMARY KEY,
    class_level INTEGER NOT NULL, -- 6, 7, 8, 9, 10
    subject TEXT NOT NULL, -- Math, Science, English, Sindhi
    title_sindhi TEXT NOT NULL,
    title_english TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_courses_class_subj ON courses(class_level, subject);

CREATE TABLE IF NOT EXISTS lessons (
    id TEXT PRIMARY KEY,
    course_id TEXT NOT NULL,
    unit_number INTEGER NOT NULL,
    title_sindhi TEXT NOT NULL,
    title_english TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    duration_seconds INTEGER DEFAULT 600,
    status TEXT DEFAULT 'PUBLISHED', -- DRAFT, PUBLISHED, RETIRED
    summary_sindhi TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_lessons_course ON lessons(course_id, unit_number);

CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    lesson_id TEXT NOT NULL,
    hls_url TEXT NOT NULL,
    fallback_url TEXT NOT NULL,
    audio_only_url TEXT NOT NULL,
    resolution_240p TEXT,
    resolution_360p TEXT,
    file_size_bytes INTEGER DEFAULT 25000000,
    FOREIGN KEY(lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_videos_lesson ON videos(lesson_id);

CREATE TABLE IF NOT EXISTS transcripts (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    text_sindhi TEXT NOT NULL,
    confidence REAL DEFAULT 0.95,
    is_flagged INTEGER DEFAULT 0,
    FOREIGN KEY(video_id) REFERENCES videos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_transcripts_video ON transcripts(video_id, start_time);

CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,
    lesson_id TEXT NOT NULL,
    timestamp_seconds REAL NOT NULL,
    text_sindhi TEXT NOT NULL,
    options_json TEXT NOT NULL, -- JSON array of 4 choices in Sindhi
    correct_answer_index INTEGER NOT NULL,
    difficulty TEXT DEFAULT 'MEDIUM', -- EASY, MEDIUM, HARD
    topic TEXT NOT NULL,
    status TEXT DEFAULT 'PENDING_APPROVAL', -- DRAFT, PENDING_APPROVAL, APPROVED, REJECTED
    approved_by TEXT,
    approved_at TEXT,
    FOREIGN KEY(lesson_id) REFERENCES lessons(id) ON DELETE CASCADE,
    FOREIGN KEY(approved_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_questions_lesson ON questions(lesson_id, status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_questions_lesson_ts_text ON questions(lesson_id, timestamp_seconds, text_sindhi);

CREATE TABLE IF NOT EXISTS attempts (
    id TEXT PRIMARY KEY,
    attempt_uuid TEXT UNIQUE,
    user_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    selected_option INTEGER NOT NULL,
    is_correct INTEGER NOT NULL,
    time_taken_seconds REAL DEFAULT 0.0,
    device_sync_time TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_attempts_attempt_uuid ON attempts(attempt_uuid);
CREATE INDEX IF NOT EXISTS idx_attempts_user ON attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_attempts_question ON attempts(question_id);

-- Spec Compatibility Views
CREATE VIEW IF NOT EXISTS video_quizzes AS 
    SELECT id, lesson_id, timestamp_seconds AS timestamp_sec, text_sindhi AS question_sindhi, 
           options_json, correct_answer_index AS correct_idx, status AS approval_status, 
           approved_by, approved_at 
    FROM questions;

CREATE VIEW IF NOT EXISTS quiz_attempts AS 
    SELECT id, attempt_uuid, user_id, question_id, selected_option, is_correct, 
           time_taken_seconds, device_sync_time, created_at 
    FROM attempts;

CREATE TABLE IF NOT EXISTS progress (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    last_position_seconds REAL DEFAULT 0.0,
    is_completed INTEGER DEFAULT 0,
    pre_test_score REAL DEFAULT 0.0,
    post_test_score REAL DEFAULT 0.0,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(lesson_id) REFERENCES lessons(id) ON DELETE CASCADE,
    UNIQUE(user_id, lesson_id)
);

CREATE INDEX IF NOT EXISTS idx_progress_user ON progress(user_id);

CREATE TABLE IF NOT EXISTS quiz_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    class_level INTEGER NOT NULL,
    subject TEXT NOT NULL,
    lesson_ids_json TEXT NOT NULL,
    mode TEXT DEFAULT 'practice', -- practice or assessment
    difficulty TEXT DEFAULT 'MEDIUM',
    total_questions INTEGER NOT NULL,
    questions_snapshot_json TEXT NOT NULL,
    provider_used TEXT NOT NULL,
    model_used TEXT,
    inference_request_id TEXT,
    inference_status TEXT DEFAULT 'NOT_RUN',
    is_live_ai INTEGER DEFAULT 0,
    status TEXT DEFAULT 'IN_PROGRESS', -- IN_PROGRESS, COMPLETED, ABANDONED
    score REAL DEFAULT NULL,
    max_score REAL DEFAULT NULL,
    percentage REAL DEFAULT NULL,
    answers_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    submitted_at TEXT DEFAULT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_quiz_sessions_user ON quiz_sessions(user_id, status);
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_created ON quiz_sessions(created_at);

CREATE TABLE IF NOT EXISTS chat_logs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    lesson_id TEXT,
    question_text TEXT NOT NULL,
    retrieved_chunks_json TEXT,
    answer_text TEXT NOT NULL,
    is_refused INTEGER DEFAULT 0,
    is_flagged_wrong INTEGER DEFAULT 0,
    provider_type TEXT,
    model_name TEXT,
    inference_status TEXT,
    is_unavailable INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(lesson_id) REFERENCES lessons(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_chat_logs_user ON chat_logs(user_id);

CREATE TABLE IF NOT EXISTS consents (
    id TEXT PRIMARY KEY,
    guardian_code TEXT NOT NULL,
    child_code TEXT NOT NULL,
    scope TEXT NOT NULL, -- SPEECH_TRAINING, LEARNING_ANALYTICS
    is_granted INTEGER NOT NULL DEFAULT 1,
    consent_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audio_samples (
    id TEXT PRIMARY KEY,
    speaker_code TEXT NOT NULL,
    dialect TEXT NOT NULL, -- Lari, Siroli, Vicholi
    age_group TEXT NOT NULL,
    consent_id TEXT NOT NULL,
    audio_path TEXT NOT NULL,
    transcript_text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(consent_id) REFERENCES consents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    details_json TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);

CREATE TABLE IF NOT EXISTS academic_policies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    default_deadline_days INTEGER DEFAULT 7,
    max_marks_default INTEGER DEFAULT 20,
    allow_late_submissions INTEGER DEFAULT 1,
    late_penalty_pct REAL DEFAULT 10.0,
    max_attempts INTEGER DEFAULT 1,
    auto_publish_assignments INTEGER DEFAULT 1,
    auto_grading_enabled INTEGER DEFAULT 1,
    confidence_threshold REAL DEFAULT 0.65,
    retry_max_attempts INTEGER DEFAULT 3,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assignments (
    id TEXT PRIMARY KEY,
    course_id TEXT NOT NULL,
    lesson_id TEXT,
    title_sindhi TEXT NOT NULL,
    title_english TEXT,
    description_sindhi TEXT NOT NULL,
    due_date TEXT NOT NULL,
    max_marks INTEGER DEFAULT 10,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT DEFAULT 'PUBLISHED', -- DRAFT, PUBLISHED, ARCHIVED
    generation_source TEXT DEFAULT 'MANUAL', -- MANUAL, AI_RAG_STBB
    target_class_level INTEGER,
    subject TEXT,
    questions_json TEXT, -- Structured list of questions (MCQ, Short, Numerical, Descriptive) with rubrics & source refs
    rubric_json TEXT, -- Overall or question-level marking guidelines
    source_reference TEXT, -- Textbook chapter/page/lesson citation
    FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE,
    FOREIGN KEY(lesson_id) REFERENCES lessons(id) ON DELETE SET NULL,
    FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_assignments_course ON assignments(course_id);
CREATE INDEX IF NOT EXISTS idx_assignments_due ON assignments(due_date);
CREATE INDEX IF NOT EXISTS idx_assignments_status ON assignments(status);
CREATE INDEX IF NOT EXISTS idx_assignments_class_subj ON assignments(target_class_level, subject);

CREATE TABLE IF NOT EXISTS assignment_submissions (
    id TEXT PRIMARY KEY,
    assignment_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    submission_text TEXT NOT NULL,
    answers_json TEXT, -- Optional JSON map or array of question answers
    marks_awarded REAL,
    teacher_feedback TEXT,
    graded_by TEXT, -- User ID or 'AI_TUTOR_AUTO'
    graded_at TEXT,
    grading_status TEXT DEFAULT 'GRADED', -- SUBMITTED, GRADING_IN_PROGRESS, GRADED, NEEDS_RETRY, NEEDS_REVIEW
    grading_details_json TEXT, -- Question-by-question breakdown, rubric versions, confidence scores, source refs
    grading_confidence REAL, -- Calibrated confidence score
    submitted_at TEXT NOT NULL,
    attempt_number INTEGER DEFAULT 1,
    is_late INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    FOREIGN KEY(assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(assignment_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_submissions_assignment ON assignment_submissions(assignment_id);
CREATE INDEX IF NOT EXISTS idx_submissions_user ON assignment_submissions(user_id);
CREATE INDEX IF NOT EXISTS idx_submissions_status ON assignment_submissions(grading_status);

CREATE TABLE IF NOT EXISTS student_notifications (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title_sindhi TEXT NOT NULL,
    message_sindhi TEXT NOT NULL,
    notification_type TEXT NOT NULL, -- ASSIGNMENT_AVAILABLE, DEADLINE_APPROACHING, RESULT_PUBLISHED, GRADING_DELAYED
    reference_id TEXT, -- e.g. assignment_id or submission_id
    is_read INTEGER DEFAULT 0,
    delivered_channel TEXT DEFAULT 'IN_APP', -- IN_APP, SMS
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_notifications_user ON student_notifications(user_id, is_read);


CREATE TABLE IF NOT EXISTS youtube_videos (
    id TEXT PRIMARY KEY,
    lesson_id TEXT,
    youtube_id TEXT NOT NULL,
    title TEXT NOT NULL,
    channel_name TEXT NOT NULL,
    original_url TEXT NOT NULL,
    embed_url TEXT NOT NULL,
    class_level INTEGER,
    subject TEXT,
    language TEXT DEFAULT 'sindhi',
    topic TEXT,
    duration_seconds INTEGER,
    curriculum_status TEXT DEFAULT 'PENDING_VERIFICATION', -- PENDING_VERIFICATION, MAPPED, APPROVED
    attribution_text TEXT NOT NULL,
    is_embeddable INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY(lesson_id) REFERENCES lessons(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_youtube_lesson ON youtube_videos(lesson_id);
CREATE INDEX IF NOT EXISTS idx_youtube_status ON youtube_videos(curriculum_status);

CREATE TABLE IF NOT EXISTS lesson_reviews (
    id TEXT PRIMARY KEY,
    lesson_id TEXT NOT NULL,
    reviewer_id TEXT NOT NULL,
    action TEXT NOT NULL, -- APPROVED, REJECTED, REVISION_REQUESTED
    comments TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(lesson_id) REFERENCES lessons(id) ON DELETE CASCADE,
    FOREIGN KEY(reviewer_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_reviews_lesson ON lesson_reviews(lesson_id);
CREATE INDEX IF NOT EXISTS idx_attempts_user_created ON attempts(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_progress_user_lesson ON progress(user_id, lesson_id);
CREATE INDEX IF NOT EXISTS idx_chat_logs_created ON chat_logs(created_at);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at REAL NOT NULL,
    used INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pwd_reset_token ON password_reset_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_pwd_reset_user ON password_reset_tokens(user_id);

-- ============================================================================
-- SDC Phase 3.2: Reusable Multi-Subject Curriculum & Textbook Management Schema
-- ============================================================================

CREATE TABLE IF NOT EXISTS subjects (
    id TEXT PRIMARY KEY,
    class_level INTEGER NOT NULL, -- 6, 7, 8, 9, 10
    slug TEXT NOT NULL,           -- e.g. 'science', 'math', 'sindhi'
    title_sindhi TEXT NOT NULL,   -- e.g. 'سائنس', 'رياضي'
    title_english TEXT NOT NULL,  -- e.g. 'Science', 'Mathematics'
    primary_language TEXT DEFAULT 'sindhi',
    curriculum_board TEXT DEFAULT 'Sindh Textbook Board, Jamshoro',
    description_sindhi TEXT,
    learning_objectives TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    UNIQUE(class_level, slug)
);

CREATE INDEX IF NOT EXISTS idx_subjects_class_slug ON subjects(class_level, slug);
CREATE INDEX IF NOT EXISTS idx_subjects_active ON subjects(is_active);

CREATE TABLE IF NOT EXISTS textbooks (
    id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    title_sindhi TEXT NOT NULL,
    title_english TEXT NOT NULL,
    class_level INTEGER NOT NULL,
    language TEXT DEFAULT 'sindhi',
    edition_year TEXT,
    publisher TEXT DEFAULT 'Sindh Textbook Board, Jamshoro',
    original_filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_hash_sha256 TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    page_count INTEGER DEFAULT 0,
    version INTEGER DEFAULT 1,
    is_active INTEGER DEFAULT 0,  -- Admin activates after validation
    processing_status TEXT DEFAULT 'PENDING', -- PENDING, PROCESSING, COMPLETED, FAILED, OCR_REQUIRED
    processing_errors TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_textbooks_subject ON textbooks(subject_id);
CREATE INDEX IF NOT EXISTS idx_textbooks_hash ON textbooks(file_hash_sha256);
CREATE INDEX IF NOT EXISTS idx_textbooks_active ON textbooks(subject_id, is_active);

CREATE TABLE IF NOT EXISTS textbook_pages (
    id TEXT PRIMARY KEY,
    textbook_id TEXT NOT NULL,
    pdf_page_index INTEGER NOT NULL,       -- 0-indexed physical PDF page
    printed_page_number INTEGER,          -- 1-indexed printed textbook page
    lesson_id TEXT,
    raw_sindhi_text TEXT NOT NULL,        -- exact extracted text (preserving presentation forms/diacritics)
    normalized_sindhi_text TEXT NOT NULL, -- NFKC + stripped diacritics for lexical indexing
    character_count INTEGER NOT NULL,
    word_count INTEGER NOT NULL,
    extraction_quality TEXT DEFAULT 'GOOD', -- GOOD, LOW_CONFIDENCE, EMPTY, SCANNED_IMAGE
    has_equations INTEGER DEFAULT 0,
    has_tables INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY(textbook_id) REFERENCES textbooks(id) ON DELETE CASCADE,
    FOREIGN KEY(lesson_id) REFERENCES lessons(id) ON DELETE SET NULL,
    UNIQUE(textbook_id, pdf_page_index)
);

CREATE INDEX IF NOT EXISTS idx_tb_pages_book ON textbook_pages(textbook_id, pdf_page_index);
CREATE INDEX IF NOT EXISTS idx_tb_pages_lesson ON textbook_pages(lesson_id);

CREATE TABLE IF NOT EXISTS textbook_chunks (
    id TEXT PRIMARY KEY,
    textbook_id TEXT NOT NULL,
    page_id TEXT NOT NULL,
    lesson_id TEXT,
    chunk_index INTEGER NOT NULL,
    pdf_page_index INTEGER NOT NULL,
    printed_page_number INTEGER,
    chapter_title_sindhi TEXT,
    original_sindhi_text TEXT NOT NULL,
    normalized_search_text TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    keywords_json TEXT, -- extracted high-idf terminology
    created_at TEXT NOT NULL,
    FOREIGN KEY(textbook_id) REFERENCES textbooks(id) ON DELETE CASCADE,
    FOREIGN KEY(page_id) REFERENCES textbook_pages(id) ON DELETE CASCADE,
    FOREIGN KEY(lesson_id) REFERENCES lessons(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_tb_chunks_book ON textbook_chunks(textbook_id);
CREATE INDEX IF NOT EXISTS idx_tb_chunks_page ON textbook_chunks(page_id);
CREATE INDEX IF NOT EXISTS idx_tb_chunks_lesson ON textbook_chunks(lesson_id);

CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id TEXT PRIMARY KEY,
    textbook_id TEXT NOT NULL,
    stage TEXT NOT NULL, -- UPLOADED, PARSING_PAGES, EXTRACTING_TEXT, CHUNKING, INDEXING, COMPLETED, FAILED
    progress_percentage REAL DEFAULT 0.0,
    total_pages INTEGER DEFAULT 0,
    processed_pages INTEGER DEFAULT 0,
    failed_pages INTEGER DEFAULT 0,
    status TEXT DEFAULT 'IN_PROGRESS', -- IN_PROGRESS, SUCCESS, FAILED, RETRYING
    error_summary TEXT,
    retry_count INTEGER DEFAULT 0,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY(textbook_id) REFERENCES textbooks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_book ON ingestion_jobs(textbook_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_status ON ingestion_jobs(status);
"""
