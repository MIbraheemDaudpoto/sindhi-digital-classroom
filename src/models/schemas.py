"""Pydantic models and serialization schemas for SDC.
Authored under agency-api-platform-engineer.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class UserRole(str, Enum):
    STUDENT = "STUDENT"
    PARENT = "PARENT"
    TEACHER = "TEACHER"
    HEAD_TEACHER = "HEAD_TEACHER"
    OFFICER = "OFFICER"
    SUPER_ADMIN = "SUPER_ADMIN"
    # Backward compatibility aliases
    ADMIN = "SUPER_ADMIN"
    SCHOOL_ADMIN = "HEAD_TEACHER"
    DISTRICT_OFFICER = "OFFICER"
    CONTENT_REVIEWER = "TEACHER"


class QuestionStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# 1. Auth Models
class StudentLoginRequest(BaseModel):
    school_code: Optional[str] = Field(default=None, description="School identification code (e.g. SCH-HYD-01)")
    student_code: Optional[str] = Field(default=None, description="Pseudonymous student code (e.g. STU-101)")
    identifier: Optional[str] = Field(default=None, description="Mobile phone number or student ID")
    pin: str = Field(min_length=4, max_length=6, description="4-6 digit authentication PIN")


class TeacherLoginRequest(BaseModel):
    identifier: str = Field(description="Teacher email, phone number, or username")
    password: str = Field(min_length=6, description="Teacher password")


class StudentSignupRequest(BaseModel):
    invite_code: str = Field(min_length=8, max_length=80, description="Single-use code issued by an SDC administrator")
    full_name: Optional[str] = Field(default=None, max_length=100, description="Student full name (e.g. احمد علي)")
    pseudonymous_code: Optional[str] = Field(default=None, min_length=3, max_length=50, description="Optional custom student code or username")
    school_code: Optional[str] = Field(default=None, max_length=50, description="Registered school code (e.g. SCH-HYD-01)")
    school_name: Optional[str] = Field(default=None, max_length=150, description="Student independent school name")
    city: Optional[str] = Field(default=None, max_length=80, description="City or District (e.g. Hyderabad, Sukkur)")
    phone: Optional[str] = Field(default=None, max_length=25, description="Mobile phone number for OTP verification")
    otp: Optional[str] = Field(default=None, description="4-digit OTP code")
    pin: str = Field(min_length=4, max_length=6, description="4-6 digit numeric PIN")
    class_level: int = Field(default=6, ge=6, le=6, description="Currently supported launch class")
    language: str = Field(default="sindhi")
    role: Optional[str] = Field(default=None, description="Privilege escalation guard - rejected if not STUDENT")


class SendOtpRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=20, description="Mobile phone number (e.g. 03001234567)")
    purpose: str = Field(default="REGISTRATION", description="REGISTRATION or RESET_PIN")


class VerifyOtpRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=20, description="Mobile phone number")
    otp: str = Field(min_length=4, max_length=6, description="4-6 digit OTP code")


class ResetPinRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=20, description="Mobile phone number")
    otp: str = Field(min_length=4, max_length=6, description="4-6 digit OTP code")
    new_pin: str = Field(min_length=4, max_length=6, description="New 4-6 digit numeric PIN")


class ForgotPasswordRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=25, description="Registered mobile number (e.g. 03001234567)")


class VerifyPasswordResetOtpRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=25, description="Registered mobile number")
    otp: str = Field(min_length=4, max_length=8, description="Received OTP code")


class ConfirmPasswordResetRequest(BaseModel):
    reset_token: str = Field(min_length=16, description="Single-use password reset authorization token")
    new_password: str = Field(min_length=4, max_length=128, description="New password or 4-digit PIN")


class PasswordResetResponse(BaseModel):
    status: str = "ok"
    message: str
    reset_token: Optional[str] = None


class PublicSchoolResponse(BaseModel):
    id: str
    name: str
    district: str
    code: str


class AuthResponse(BaseModel):
    user_id: str
    role: UserRole
    pseudonymous_code: str
    full_name: Optional[str] = None
    school_id: Optional[str] = None
    school_name: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    language: str = "sindhi"
    token: str


# 2. Curriculum & Lesson Models
class LessonResponse(BaseModel):
    id: str
    course_id: str
    unit_number: int
    title_sindhi: str
    title_english: str
    duration_seconds: int
    status: str
    summary_sindhi: Optional[str] = None
    is_completed: bool = False
    last_position_seconds: float = 0.0


class CourseResponse(BaseModel):
    id: str
    class_level: int
    subject: str
    title_sindhi: str
    title_english: str
    lessons: List[LessonResponse] = Field(default_factory=list)


# 3. Video & Smart Quiz Models
class TranscriptLine(BaseModel):
    line_number: int
    start_time: float
    end_time: float
    text_sindhi: str
    confidence: float
    is_flagged: bool = False


class QuestionResponse(BaseModel):
    id: str
    lesson_id: str
    timestamp_seconds: float
    text_sindhi: str
    options: List[str]
    correct_answer_index: Optional[int] = None # Omitted for student response unless completed
    difficulty: str
    topic: str
    status: QuestionStatus


class QuestionApprovalRequest(BaseModel):
    status: QuestionStatus
    edited_text_sindhi: Optional[str] = None
    edited_options: Optional[List[str]] = None
    edited_correct_answer: Optional[int] = None


class LessonUploadRequest(BaseModel):
    course_id: str = Field(min_length=3, max_length=50)
    unit_number: int = Field(ge=1, le=50, description="Unit number (1-50)")
    title_sindhi: str = Field(min_length=2, max_length=200, description="Sindhi lesson title")
    title_english: str = Field(min_length=2, max_length=200, description="English lesson title")
    duration_seconds: int = Field(ge=10, le=7200, default=600, description="Video duration in seconds (10s to 2 hours)")
    summary_sindhi: Optional[str] = Field(None, max_length=1000)
    video_url: Optional[str] = Field(None, max_length=500)

    @field_validator("video_url")
    @classmethod
    def validate_video_url(cls, v: Optional[str]) -> Optional[str]:
        if v:
            allowed_exts = (".mp4", ".webm", ".mov", ".mkv", ".m3u8")
            clean_v = v.split("?")[0].lower()
            if not any(clean_v.endswith(ext) for ext in allowed_exts):
                raise ValueError("غير منظور ٿيل وڊيو فارميٽ (Invalid video format. Allowed: mp4, webm, mov, mkv, m3u8)")
        return v



class YouTubeVideoResponse(BaseModel):
    id: str
    lesson_id: Optional[str] = None
    youtube_id: str
    title: str
    channel_name: str
    original_url: str
    embed_url: str
    class_level: Optional[int] = None
    subject: Optional[str] = None
    language: str = "sindhi"
    topic: Optional[str] = None
    duration_seconds: Optional[int] = None
    curriculum_status: str
    attribution_text: str
    is_embeddable: bool = True
    is_offline_available: bool = False


class LessonDetailResponse(LessonResponse):
    video_hls_url: str
    video_fallback_url: str
    audio_only_url: str
    video_source_type: str = "LOCAL"  # LOCAL or YOUTUBE
    youtube_video: Optional[YouTubeVideoResponse] = None
    transcripts: List[TranscriptLine] = Field(default_factory=list)
    approved_questions: List[QuestionResponse] = Field(default_factory=list)


# 4. Attempts & Progress Models
class AttemptSubmitRequest(BaseModel):
    question_id: str
    selected_option: int # 0-3, or -1 for skipped
    time_taken_seconds: float = 0.0
    device_sync_time: Optional[str] = None
    is_skipped: bool = False


class AttemptResponse(BaseModel):
    id: str
    question_id: str
    selected_option: int
    is_correct: bool
    correct_answer_index: int
    explanation_sindhi: Optional[str] = None


class ProgressUpdateRequest(BaseModel):
    lesson_id: str
    position_seconds: float
    is_completed: bool = False


# 4b. Real-Time Curriculum & AI Assessment Models
class QuizGenerateRequest(BaseModel):
    class_level: int = Field(default=6, ge=6, le=6, description="Currently supported launch class")
    subject: str = Field(default="Science", description="Currently supported subjects: Science or Math")
    lesson_ids: Optional[List[str]] = Field(default=None, max_length=30, description="One or more specific lesson IDs")
    question_count: int = Field(default=5, ge=1, le=20, description="Number of questions to generate (1-20)")
    mode: str = Field(default="practice", description="Assessment mode: 'practice' (immediate feedback) or 'assessment' (withheld)")
    difficulty: str = Field(default="MEDIUM", description="Difficulty: EASY, MEDIUM, HARD, ALL")
    allow_fallback: bool = Field(default=False, description="Explicitly allow a clearly labeled non-AI curriculum question bank")

    @field_validator("mode")
    @classmethod
    def validate_quiz_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"practice", "assessment"}:
            raise ValueError("Mode must be practice or assessment.")
        return normalized

    @field_validator("difficulty")
    @classmethod
    def validate_quiz_difficulty(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in {"EASY", "MEDIUM", "HARD", "ALL"}:
            raise ValueError("Difficulty must be EASY, MEDIUM, HARD, or ALL.")
        return normalized


class QuizQuestionClientItem(BaseModel):
    id: str
    index: int
    text_sindhi: str
    options: List[str]
    difficulty: str
    lesson_id: str
    lesson_title_sd: str
    lesson_title_en: str
    topic: str


class QuizSessionResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    session_id: str
    class_level: int
    subject: str
    lesson_ids: List[str]
    lessons_meta: List[Dict[str, Any]]
    total_questions: int
    mode: str
    difficulty: str
    provider_type: str
    model_name: Optional[str] = None
    inference_request_id: Optional[str] = None
    inference_status: str = "NOT_RUN"
    is_live_ai: bool
    ai_status_message: str
    status: str
    questions: List[QuizQuestionClientItem]


class QuizAnswerSubmitRequest(BaseModel):
    question_id: str
    selected_option: int = Field(ge=-1, le=3, description="0-3 selected option, or -1 for skipped")
    time_taken_seconds: float = Field(default=0.0, ge=0.0)


class QuizAnswerFeedbackResponse(BaseModel):
    session_id: str
    question_id: str
    selected_option: int
    is_correct: Optional[bool] = None
    correct_answer_index: Optional[int] = None
    explanation_sindhi: Optional[str] = None
    citation: Optional[str] = None
    lesson_id: str
    lesson_title_sd: str
    topic: str
    message: str


class LessonScoreBreakdown(BaseModel):
    lesson_id: str
    lesson_title_sd: str
    total_questions: int
    correct_questions: int
    percentage: float


class QuestionReviewItem(BaseModel):
    question_id: str
    index: int
    text_sindhi: str
    options: List[str]
    selected_option: int
    correct_answer_index: int
    is_correct: bool
    explanation_sindhi: str
    citation: str
    lesson_id: str
    lesson_title_sd: str
    topic: str


class QuizSubmitResponse(BaseModel):
    session_id: str
    user_id: str
    class_level: int
    subject: str
    total_questions: int
    correct_count: int
    incorrect_count: int
    score: float
    percentage: float
    passed: bool
    per_lesson_breakdown: Dict[str, LessonScoreBreakdown]
    topics_to_review: List[str]
    review: List[QuestionReviewItem]
    provider_used: str
    is_live_ai: bool
    submitted_at: str


class TutorAskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    class_level: Optional[int] = 6
    subject_id: Optional[str] = None
    lesson_id: Optional[str] = None
    chapter_id: Optional[int] = Field(default=None, description="Curriculum chapter ID (1-12) if scoped to a specific chapter")
    voice_input_used: bool = False
    previous_turn_context: Optional[str] = Field(default=None, description="Previous turn query or topic context for multi-turn conversational continuity")
    session_id: Optional[str] = Field(default=None, description="Optional conversational session ID")


class TutorCitation(BaseModel):
    lesson_id: Optional[str] = None
    lesson_title_sindhi: str
    textbook_title_sindhi: Optional[str] = None
    page_number: Optional[Any] = None
    citation_formatted: Optional[str] = None
    timestamp_seconds: Optional[float] = None
    text_snippet_sindhi: str


class TutorAskResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    answer_sindhi: str
    is_refused: bool = False
    is_unavailable: bool = False
    citations: List[TutorCitation] = Field(default_factory=list)
    report_id: Optional[str] = None
    request_id: Optional[str] = None
    provider_type: str = Field(default="LOCAL_DETERMINISTIC_FALLBACK", description="LOCAL_DETERMINISTIC_FALLBACK or CLOUD_LLM_INFERENCE")
    model_name: Optional[str] = None
    confidence_score: Optional[float] = None
    latency_seconds: Optional[float] = None
    inference_status: Optional[str] = Field(default="LOCAL_DETERMINISTIC_FALLBACK", description="REAL_LLM_INFERENCE, LLM_INFERENCE_UNAVAILABLE, LOCAL_DETERMINISTIC_FALLBACK, or MOCKED")


# 6. Dashboards & Analytics Models
class StudentDashboardResponse(BaseModel):
    student_code: str
    class_level: int
    school_name: str
    completed_lessons_count: int
    course_id: Optional[str] = "crs-sci-6"
    course_subject: Optional[str] = "Science"
    course_completed_count: Optional[int] = 0
    course_total_count: Optional[int] = 0
    total_quiz_score_pct: float
    total_quiz_attempts: int = 0
    completed_quiz_count: int = 0
    active_streak_days: int = 0
    streak_badge_sindhi: str = "سکيا جو آغاز (Start Learning)"
    next_recommended_lesson: Optional[LessonResponse] = None
    last_activity: Optional[Dict[str, Any]] = None
    recent_attempts: List[Dict[str, Any]] = Field(default_factory=list)
    enrolled_lessons: List[Dict[str, Any]] = Field(default_factory=list)
    weekly_activity: List[Dict[str, Any]] = Field(default_factory=list)


class WeakTopicMetric(BaseModel):
    topic: str
    error_rate_pct: float
    total_attempts: int


class TeacherDashboardResponse(BaseModel):
    school_name: str
    total_students_enrolled: int
    weekly_active_students_pct: float
    average_quiz_score_pct: float
    cohens_d_gain: float
    pending_approval_questions_count: int
    weak_topics: List[WeakTopicMetric] = Field(default_factory=list)


class OfficerDistrictReport(BaseModel):
    district: str
    total_schools: int
    total_students: int
    active_rate_pct: float
    avg_score_pct: float
    offline_sync_count: int


# 7. Assignment Models (FR-28 & AI-Managed Homework)
class AssignmentQuestionItem(BaseModel):
    id: str
    question_type: str = "SHORT_ANSWER" # MCQ, SHORT_ANSWER, DESCRIPTIVE, NUMERICAL
    question_text_sindhi: str
    options: Optional[List[str]] = None # For MCQ
    correct_answer: Optional[str] = None # Key or exact value
    rubric_guidelines: Optional[str] = None # Guidelines for AI grading
    max_marks: float = 5.0
    source_reference: Optional[str] = None # e.g. STBB Class 8 Biology, Chapter 1, p. 14


class AcademicPolicyModel(BaseModel):
    id: str = "default_policy"
    name: str = "Standard STBB Academic Policy"
    default_deadline_days: int = 7
    max_marks_default: int = 20
    allow_late_submissions: bool = True
    late_penalty_pct: float = 10.0
    max_attempts: int = 1
    auto_publish_assignments: bool = True
    auto_grading_enabled: bool = True
    confidence_threshold: float = 0.65
    retry_max_attempts: int = 3
    updated_at: Optional[str] = None


class AssignmentCreateRequest(BaseModel):
    course_id: str = Field(min_length=3, max_length=50)
    lesson_id: Optional[str] = Field(None, max_length=50)
    title_sindhi: str = Field(min_length=2, max_length=200)
    title_english: Optional[str] = Field(None, max_length=200)
    description_sindhi: str = Field(min_length=5, max_length=2000)
    due_date: str = Field(description="ISO-8601 due date string")
    max_marks: int = Field(default=10, ge=1, le=100)
    status: str = "PUBLISHED"
    target_class_level: Optional[int] = None
    subject: Optional[str] = None
    questions: Optional[List[AssignmentQuestionItem]] = None
    source_reference: Optional[str] = None


class AssignmentSubmitRequest(BaseModel):
    submission_text: str = Field(min_length=1, max_length=5000)
    answers: Optional[Dict[str, str]] = None # question_id -> student answer


class AssignmentGradeRequest(BaseModel):
    marks_awarded: float = Field(ge=0.0)
    teacher_feedback: Optional[str] = Field(None, max_length=1000)


class QuestionGradingDetail(BaseModel):
    question_id: str
    marks_awarded: float
    max_marks: float
    feedback_sindhi: str
    is_correct: Optional[bool] = None
    confidence_score: float = 1.0
    source_citation: Optional[str] = None


class AssignmentSubmissionResponse(BaseModel):
    id: str
    assignment_id: str
    user_id: str
    student_code: Optional[str] = None
    submission_text: str
    marks_awarded: Optional[float] = None
    teacher_feedback: Optional[str] = None
    graded_by: Optional[str] = None
    graded_at: Optional[str] = None
    submitted_at: str
    is_graded: bool = False
    grading_status: str = "GRADED" # SUBMITTED, GRADING_IN_PROGRESS, GRADED, NEEDS_RETRY, NEEDS_REVIEW
    grading_confidence: Optional[float] = None
    grading_details: Optional[List[QuestionGradingDetail]] = None
    attempt_number: int = 1
    is_late: bool = False


class AssignmentResponse(BaseModel):
    id: str
    course_id: str
    lesson_id: Optional[str] = None
    title_sindhi: str
    title_english: Optional[str] = None
    description_sindhi: str
    due_date: str
    max_marks: int
    created_by: str
    created_at: str
    status: str = "PUBLISHED"
    generation_source: str = "MANUAL"
    target_class_level: Optional[int] = None
    subject: Optional[str] = None
    questions: Optional[List[AssignmentQuestionItem]] = None
    source_reference: Optional[str] = None
    is_overdue: bool = False
    my_submission: Optional[AssignmentSubmissionResponse] = None
    submissions_count: int = 0


class StudentNotificationResponse(BaseModel):
    id: str
    user_id: str
    title_sindhi: str
    message_sindhi: str
    notification_type: str
    reference_id: Optional[str] = None
    is_read: bool = False
    delivered_channel: str = "IN_APP"
    created_at: str


class AIGenerateAssignmentRequest(BaseModel):
    class_level: int = Field(ge=6, le=10)
    subject: str = Field(min_length=2, max_length=50)
    unit_number: Optional[int] = Field(None, ge=1, le=50)
    lesson_id: Optional[str] = None
    topic: Optional[str] = None
    question_count: int = Field(default=3, ge=1, le=10)
    auto_publish: bool = True



# 8. Content Review Models (Reviewer Workflow)
class LessonReviewRequest(BaseModel):
    action: str = Field(description="Review action: APPROVED, REJECTED, REVISION_REQUESTED")
    comments: Optional[str] = Field(None, max_length=1000)


class LessonReviewResponse(BaseModel):
    id: str
    lesson_id: str
    reviewer_id: str
    action: str
    comments: Optional[str] = None
    created_at: str


# 9. User Administration Models (RBAC)
class UserCreateRequest(BaseModel):
    pseudonymous_code: str = Field(min_length=3, max_length=50)
    role: UserRole
    pin_or_password: str = Field(min_length=4, max_length=50)
    school_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    language: str = "sindhi"


class StudentInviteRequest(BaseModel):
    school_id: Optional[str] = None
    expires_in_days: int = Field(default=7, ge=1, le=30)


class StudentProgressListItem(BaseModel):
    user_id: str
    student_code: str
    school_name: Optional[str] = None
    completed_lessons: int = 0
    total_lessons: int = 0
    completed_quizzes: int = 0
    average_quiz_score_pct: Optional[float] = None
    last_activity: Optional[str] = None


class StudentProgressListResponse(BaseModel):
    items: List[StudentProgressListItem]
    total: int
    limit: int
    offset: int
    summary: Dict[str, Any] = Field(default_factory=dict)


class UserResponse(BaseModel):
    id: str
    role: str
    school_id: Optional[str] = None
    school_name: Optional[str] = None
    pseudonymous_code: str
    email: Optional[str] = None
    phone: Optional[str] = None
    language: str = "sindhi"
    created_at: str


class AuditLogResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details_json: Optional[str] = None
    created_at: str

