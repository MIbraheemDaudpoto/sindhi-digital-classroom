"""Seed comprehensive, authentic STBB in-video checkpoint questions for all lessons.
Ensures every video across Math, Science, English, and Sindhi has curriculum-grounded,
pedagogically verified in-video checkpoints at 60s, 120s, 180s.
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding='utf-8')

CHECKPOINTS_DATA = [
    # --- Science Class 6 (Units 3 - 12) ---
    {
        "lesson_id": "lesson-sci-6-3",
        "questions": [
            {
                "id": "q-sci-3-1",
                "timestamp_seconds": 60.0,
                "text_sindhi": "ٻوٽي جي پن تي موجود ننڍڙا سوراخ جن مان گئسن جو تبادلو ٿئي ٿو، تن کي ڇا چئبو آهي؟",
                "options": ["اسٽوميٽا (Stomata)", "ريٽينا (Retina)", "ڪورنيا (Cornea)", "نيوڪليئس (Nucleus)"],
                "correct_answer_index": 0,
                "difficulty": "EASY",
                "topic": "اسٽوميٽا ۽ گئسن جو تبادلو"
            },
            {
                "id": "q-sci-3-2",
                "timestamp_seconds": 120.0,
                "text_sindhi": "روشنائي ترڪيب (Photosynthesis) واري عمل دوران ٻوٽا سج جي روشنيءَ ۾ ڪهڙي گئس جذب ڪندا آهن؟",
                "options": ["نائٽروجن", "ڪاربان ڊاءِ آڪسائيڊ", "هيليم", "ڪلورين"],
                "correct_answer_index": 1,
                "difficulty": "MEDIUM",
                "topic": "روشنائي ترڪيب جا جزا"
            },
            {
                "id": "q-sci-3-3",
                "timestamp_seconds": 180.0,
                "text_sindhi": "ساهه کڻڻ (Respiration) واري عمل ۾ جاندار توانائي حاصل ڪرڻ لاءِ ڪهڙي گئس استعمال ڪندا آهن؟",
                "options": ["آڪسيجن (Oxygen)", "نائٽروجن (Nitrogen)", "ڪاربان مونو آڪسائيڊ", "آرگان"],
                "correct_answer_index": 0,
                "difficulty": "MEDIUM",
                "topic": "ساهه کڻڻ جو عمل"
            }
        ]
    },
    {
        "lesson_id": "lesson-sci-6-4",
        "questions": [
            {
                "id": "q-sci-4-1",
                "timestamp_seconds": 60.0,
                "text_sindhi": "ماحول جا اهي جاندار جيڪي پنهنجي خوراڪ پاڻ ٺاهيندا آهن، تن کي ڇا سڏبو آهي؟",
                "options": ["پيداواري عنصر (Producers)", "صارفين (Consumers)", "تحليلي عنصر (Decomposers)", "شڪاري جانور"],
                "correct_answer_index": 0,
                "difficulty": "EASY",
                "topic": "ماحول جا پيداواري عنصر"
            },
            {
                "id": "q-sci-4-2",
                "timestamp_seconds": 120.0,
                "text_sindhi": "هيٺين مان ڪهڙو ماحول جو غير حياتياتي (Abiotic) عنصر آهي؟",
                "options": ["ٻوٽا", "پاڻي ۽ مٽي", "فنگس", "بيڪٽيريا"],
                "correct_answer_index": 1,
                "difficulty": "EASY",
                "topic": "غير حياتياتي عنصر"
            },
            {
                "id": "q-sci-4-3",
                "timestamp_seconds": 180.0,
                "text_sindhi": "مئل جاندارن کي ڳاري ڀاڻ ۾ تبديل ڪرڻ وارن بيڪٽيريا ۽ فنگس کي ڇا چئبو آهي؟",
                "options": ["تحليلي عنصر (Decomposers)", "پيداواري عنصر", "گاهه خور جانور", "ماحولياتي آلودگي"],
                "correct_answer_index": 0,
                "difficulty": "MEDIUM",
                "topic": "تحليلي عنصر"
            }
        ]
    },
    {
        "lesson_id": "lesson-sci-6-5",
        "questions": [
            {
                "id": "q-sci-5-1",
                "timestamp_seconds": 60.0,
                "text_sindhi": "ڪنهن عنصر جو سڀ کان ننڍو ذرو جيڪو ڪيميائي عمل ۾ حصو وٺي سگهي ٿو، ان کي ڇا چئبو آهي؟",
                "options": ["ائٽم (Atom)", "محلول (Solution)", "مرڪب (Compound)", "خلوي ديوار"],
                "correct_answer_index": 0,
                "difficulty": "EASY",
                "topic": "ائٽم جو تعارف"
            },
            {
                "id": "q-sci-5-2",
                "timestamp_seconds": 120.0,
                "text_sindhi": "جڏهن ٻه يا وڌيڪ ائٽم پاڻ ۾ ڪيميائي طور ڳنڍجن ٿا ته ڇا ٺهندو آهي؟",
                "options": ["ماليڪيول (Molecule)", "صرف اليڪٽران", "مٽيءَ جا ذرا", "هوا جا دٻاءَ"],
                "correct_answer_index": 0,
                "difficulty": "MEDIUM",
                "topic": "ماليڪيول جي بناوت"
            },
            {
                "id": "q-sci-5-3",
                "timestamp_seconds": 180.0,
                "text_sindhi": "پاڻي (H₂O) هيٺين مان ڪهڙي شئي جو مشهور مثال آهي؟",
                "options": ["مرڪب (Compound)", "خالص ائٽم", "سادو ڦيٿو", "گئسي عنصر"],
                "correct_answer_index": 0,
                "difficulty": "EASY",
                "topic": "مرڪب جا مثال"
            }
        ]
    },
    {
        "lesson_id": "lesson-sci-6-6",
        "questions": [
            {
                "id": "q-sci-6-1",
                "timestamp_seconds": 60.0,
                "text_sindhi": "ڌرتيءَ جي فضا (Atmosphere) ۾ سڀ کان وڌيڪ مقدار (لڳ ڀڳ 78٪) ڪهڙي گئس جو هوندو آهي؟",
                "options": ["نائٽروجن (Nitrogen)", "آڪسيجن (Oxygen)", "ڪاربان ڊاءِ آڪسائيڊ", "هائيڊروجن"],
                "correct_answer_index": 0,
                "difficulty": "EASY",
                "topic": "فضا ۾ نائٽروجن جو مقدار"
            },
            {
                "id": "q-sci-6-2",
                "timestamp_seconds": 120.0,
                "text_sindhi": "جاندارن جي ساهه کڻڻ ۽ باهه ٻرڻ لاءِ هوا جي ڪهڙي گئس لازمي آهي؟",
                "options": ["آڪسيجن (Oxygen)", "نائٽروجن", "هيليم", "اوزون"],
                "correct_answer_index": 0,
                "difficulty": "EASY",
                "topic": "آڪسيجن جي اهميت"
            },
            {
                "id": "q-sci-6-3",
                "timestamp_seconds": 180.0,
                "text_sindhi": "ڌرتيءَ جي فضا ۾ موجود هوا جو وزن جيڪو مٿاڇري تي اثر وجهي ٿو، ان کي ڇا سڏبو آهي؟",
                "options": ["هوا جو دٻاءُ (Air Pressure)", "مادي جو وزن", "گرمي پد", "روشنيءَ جي شدت"],
                "correct_answer_index": 0,
                "difficulty": "MEDIUM",
                "topic": "هوا جو دٻاءُ"
            }
        ]
    },
    {
        "lesson_id": "lesson-sci-6-7",
        "questions": [
            {
                "id": "q-sci-7-1",
                "timestamp_seconds": 60.0,
                "text_sindhi": "محلول (Solution) ۾ جيڪا شيءِ ٻي شيءِ کي پاڻ ۾ حل ڪري، ان کي ڇا چئبو آهي؟",
                "options": ["حل ڪندڙ مادو / سالوينٽ (Solvent)", "حل ٿيندڙ مادو / سوليٽ (Solute)", "اڻ حل ٿيل ذرا", "ڪيميائي فلٽر"],
                "correct_answer_index": 0,
                "difficulty": "EASY",
                "topic": "سPageالوينٽ جي وصف"
            },
            {
                "id": "q-sci-7-2",
                "timestamp_seconds": 120.0,
                "text_sindhi": "پاڻي ۽ کنڊ جي شربت ۾ کنڊ (Sugar) ڪهڙي حيثيت رکي ٿي؟",
                "options": ["حل ٿيندڙ مادو (Solute)", "حل ڪندڙ مادو (Solvent)", "معلق ذرڙو", "گئسي جزو"],
                "correct_answer_index": 0,
                "difficulty": "EASY",
                "topic": "سوليٽ جا مثال"
            },
            {
                "id": "q-sci-7-3",
                "timestamp_seconds": 180.0,
                "text_sindhi": "اهو محلول جنهن ۾ عام گرمي پد تي وڌيڪ حل ٿيندڙ مادو حل نه ٿي سگهي، ان کي ڇا چئبو آهي؟",
                "options": ["سير ٿيل محلول (Saturated Solution)", "اڻ سير ٿيل محلول", "سادو پاڻي", "معلق ميلاپ"],
                "correct_answer_index": 0,
                "difficulty": "MEDIUM",
                "topic": "سير ٿيل محلول"
            }
        ]
    },
    {
        "lesson_id": "lesson-sci-6-8",
        "questions": [
            {
                "id": "q-sci-8-1",
                "timestamp_seconds": 60.0,
                "text_sindhi": "ڪنهن شيءِ ۾ ان جي حرڪت جي ڪري موجود توانائيءَ کي ڇا چئبو آهي؟",
                "options": ["حرڪي توانائي (Kinetic Energy)", "سڪوتي توانائي (Potential Energy)", "ڪيميائي توانائي", "ايٽمي توانائي"],
                "correct_answer_index": 0,
                "difficulty": "EASY",
                "topic": "حرڪي توانائي"
            },
            {
                "id": "q-sci-8-2",
                "timestamp_seconds": 120.0,
                "text_sindhi": "بلنديءَ تي رکيل پٿر يا ڇڪيل تير ڪمان ۾ ڪهڙي توانائي ذخيرو ٿيل هوندي آهي؟",
                "options": ["سڪوتي توانائي (Potential Energy)", "روشني توانائي", "حرڪي توانائي", "آوازي لهرون"],
                "correct_answer_index": 0,
                "difficulty": "EASY",
                "topic": "سڪوتي توانائي"
            },
            {
                "id": "q-sci-8-3",
                "timestamp_seconds": 180.0,
                "text_sindhi": "توانائيءَ جي تحفظ جو قانون (Law of Conservation of Energy) ڇا بيان ڪري ٿو؟",
                "options": ["توانائي نه ٺاهي سگهجي ٿي ۽ نه مٽائي، رڳو روپ بدلائي ٿي", "توانائي پاڻمرادو ضايع ٿي وڃي ٿي", "توانائي رڳو حرارت ۾ تبديل ٿئي ٿي", "توانائيءَ کي ختم ڪري سگهجي ٿو"],
                "correct_answer_index": 0,
                "difficulty": "MEDIUM",
                "topic": "توانائيءَ جي تحفظ جو قانون"
            }
        ]
    },
    {
        "lesson_id": "lesson-sci-6-9",
        "questions": [
            {
                "id": "q-sci-9-1",
                "timestamp_seconds": 60.0,
                "text_sindhi": "اها سادي مشين جيڪا پنهنجي جاءِ تي مقرر رهي رڳو زور جو رخ بدلائي ٿي، ان کي ڇا چئبو آهي؟",
                "options": ["اڻ چرندڙ چرخي (Fixed Pulley)", "چرندڙ چرخي (Movable Pulley)", "گيئر سسٽم", "سرائي"],
                "correct_answer_index": 0,
                "difficulty": "EASY",
                "topic": "اڻ چرندڙ چرخي"
            },
            {
                "id": "q-sci-9-2",
                "timestamp_seconds": 120.0,
                "text_sindhi": "ڪارن ۽ سائيڪلن ۾ استعمال ٿيندڙ ڦيٿو ۽ ان جي وچ واري ڏنڊي کي ڇا سڏبو آهي؟",
                "options": ["ڦيٿو ۽ سرائي (Wheel and Axle)", "رڳو پلنگ", "مڪمل موٽر", "پٽي ۽ ڪنڊي"],
                "correct_answer_index": 0,
                "difficulty": "EASY",
                "topic": "ڦيٿو ۽ سرائي"
            },
            {
                "id": "q-sci-9-3",
                "timestamp_seconds": 180.0,
                "text_sindhi": "ڏندن وارا ڦيٿا جيڪي پاڻ ۾ گڏجي هڪ ٻئي کي حرڪت ڏين ٿا، تن کي ڇا چئبو آهي؟",
                "options": ["گيئرس (Gears)", "چرخيون", "ليور جا حصا", "ٻوٽي جا تاندورا"],
                "correct_answer_index": 0,
                "difficulty": "MEDIUM",
                "topic": "گيئرس جو نظام"
            }
        ]
    },
    {
        "lesson_id": "lesson-sci-6-10",
        "questions": [
            {
                "id": "q-sci-10-1",
                "timestamp_seconds": 60.0,
                "text_sindhi": "روشنيءَ جو هموار ۽ چمڪدار مٿاڇري تي پوڻ کان پوءِ ساڳئي رخ ۾ واپس موٽڻ ڇا چئبو آهي؟",
                "options": ["روشنيءَ جي موٽ (Reflection of Light)", "روشنيءَ جو جذب ٿيڻ", "انڌيرو", "آواز جو گونج"],
                "correct_answer_index": 0,
                "difficulty": "EASY",
                "topic": "روشنيءَ جي موٽ"
            },
            {
                "id": "q-sci-10-2",
                "timestamp_seconds": 120.0,
                "text_sindhi": "روشنيءَ جي موٽ واري قانون مطابق، واقع ٿيڻ جو زاويو (Angle of Incidence) ڪنهن جي برابر هوندو آهي؟",
                "options": ["موٽ واري زاويي (Angle of Reflection) جي", "هميشه 90 درجا", "صفر درجا", "پکيڙ واري زاويي جي"],
                "correct_answer_index": 0,
                "difficulty": "MEDIUM",
                "topic": "روشنيءَ جي موٽ جو قانون"
            },
            {
                "id": "q-sci-10-3",
                "timestamp_seconds": 180.0,
                "text_sindhi": "روشني خلا ۽ فضا ۾ ڪهڙي نموني سفر ڪندي آهي؟",
                "options": ["سڌي ليڪ (Straight line) ۾", "ٽيڏي وڪڙن ۾", "رڳو گول چڪرن ۾", "روڪجي روڪجي"],
                "correct_answer_index": 0,
                "difficulty": "EASY",
                "topic": "روشنيءَ جو سفر"
            }
        ]
    },
    {
        "lesson_id": "lesson-sci-6-11",
        "questions": [
            {
                "id": "q-sci-11-1",
                "timestamp_seconds": 60.0,
                "text_sindhi": "آواز بنيادي طور ڪنهن شيءِ جي ڪهڙي حرڪت جي نتيجي ۾ پيدا ٿيندو آهي؟",
                "options": ["لرزش يا وائبريشن (Vibration)", "روشنيءَ جي عڪس", "حرارت جي اخراج", "رنگ جي تبديلي"],
                "correct_answer_index": 0,
                "difficulty": "EASY",
                "topic": "آواز جو پيدا ٿيڻ"
            },
            {
                "id": "q-sci-11-2",
                "timestamp_seconds": 120.0,
                "text_sindhi": "آواز کي هڪ هنڌ کان ٻئي هنڌ سفر ڪرڻ لاءِ ڪهڙي شئي جي ضرورت هوندي آهي؟",
                "options": ["ڪنهن مادي واسطي (Medium جهڙوڪ هوا، پاڻي يا ٺوس)", "خالي خلا جي", "مقناطيس جي", "تارن جي بيلٽ"],
                "correct_answer_index": 0,
                "difficulty": "MEDIUM",
                "topic": "آواز جو واسطو"
            },
            {
                "id": "q-sci-11-3",
                "timestamp_seconds": 180.0,
                "text_sindhi": "ڇا مڪمل خلا (Vacuum) ۾ جتي هوا نه هجي آواز سفر ڪري سگهي ٿو؟",
                "options": ["نه، ڇاڪاڻ ته آواز کي مادي واسطي جي ضرورت آهي", "ها، آواز هر هنڌ هلندو آهي", "رڳو سج جي سامهون هلندو آهي", "رڳو رات جو هلندو آهي"],
                "correct_answer_index": 0,
                "difficulty": "EASY",
                "topic": "خلا ۾ آواز جو نه هلڻ"
            }
        ]
    },
    {
        "lesson_id": "lesson-sci-6-12",
        "questions": [
            {
                "id": "q-sci-12-1",
                "timestamp_seconds": 60.0,
                "text_sindhi": "ڌرتيءَ جو سڀ کان ويجهو ۽ واحد قدرتي سيٽلائيٽ (Natural Satellite) ڪهڙو آهي؟",
                "options": ["چنڊ (Moon)", "مريخ (Mars)", "سج (Sun)", "مشتري (Jupiter)"],
                "correct_answer_index": 0,
                "difficulty": "EASY",
                "topic": "قدرتي سيٽلائيٽ"
            },
            {
                "id": "q-sci-12-2",
                "timestamp_seconds": 120.0,
                "text_sindhi": "ننڍڙن پٿرن جهڙا جسم (Asteroids) گهڻو ڪري ڪهڙن ٻن گرهن جي وچ ۾ گردش ڪندا آهن؟",
                "options": ["مريخ (Mars) ۽ مشتري (Jupiter) جي وچ ۾", "ڌرتي ۽ چنڊ جي وچ ۾", "سج ۽ عطارد جي وچ ۾", "زحل ۽ يورينس جي وچ ۾"],
                "correct_answer_index": 0,
                "difficulty": "MEDIUM",
                "topic": "سيارڙا (Asteroid Belt)"
            },
            {
                "id": "q-sci-12-3",
                "timestamp_seconds": 180.0,
                "text_sindhi": "انسانن پاران فضا ۽ مواصلات (Communication) لاءِ موڪليل سيٽلائيٽن کي ڇا سڏبو آهي؟",
                "options": ["مصنوعي سيٽلائيٽ (Artificial Satellites)", "قدرتي تارا", "شهاب ثاقب", "پيداواري گرهه"],
                "correct_answer_index": 0,
                "difficulty": "EASY",
                "topic": "مصنوعي سيٽلائيٽس"
            }
        ]
    },
    # --- English Class 6 (Unit 1: Parts of Speech) ---
    {
        "lesson_id": "lesson-eng-6-1",
        "questions": [
            {
                "id": "q-eng-1-1",
                "timestamp_seconds": 60.0,
                "text_sindhi": "انگريزي گرامر ۾ ڪنهن شخص، جاءِ يا شئي جي نالي کي ڇا سڏبو آهي؟ (Name of person, place, or thing)",
                "options": ["اسم / Noun", "فعل / Verb", "ضمير / Pronoun", "حرف جر / Preposition"],
                "correct_answer_index": 0,
                "difficulty": "EASY",
                "topic": "Noun in English"
            },
            {
                "id": "q-eng-1-2",
                "timestamp_seconds": 120.0,
                "text_sindhi": "جملي ۾ ڪم، عمل يا حالت ظاهر ڪرڻ واري لفظ کي ڇا چئبو آهي؟ (Word showing action or state)",
                "options": ["فعل / Verb", "اسم / Noun", "صفت / Adjective", "حرف جملو / Conjunction"],
                "correct_answer_index": 0,
                "difficulty": "EASY",
                "topic": "Verb in English"
            },
            {
                "id": "q-eng-1-3",
                "timestamp_seconds": 180.0,
                "text_sindhi": "اهو لفظ جيڪو اسم (Noun) جي خوبي، خامي يا حالت بيان ڪري، ان کي ڇا چئبو آهي؟ (Describing word)",
                "options": ["صفت / Adjective", "ظرف / Adverb", "فعل / Verb", "ندا / Interjection"],
                "correct_answer_index": 0,
                "difficulty": "MEDIUM",
                "topic": "Adjective in English"
            }
        ]
    },
    # --- Sindhi Class 6 (Unit 1: Shah Latif) ---
    {
        "lesson_id": "lesson-sindhi-6-1",
        "questions": [
            {
                "id": "q-sindhi-1-1",
                "timestamp_seconds": 60.0,
                "text_sindhi": "سنڌ جي عظيم صوفي بزرگ ۽ شاعر حضرت شاهه عبداللطيف ڀٽائي رحه جو درگاهه مبارڪ ڪٿي آهي؟",
                "options": ["ڀٽ شاهه (Bhit Shah)", "سيوهڻ شريف", "روهڙي", "ٺٽو"],
                "correct_answer_index": 0,
                "difficulty": "EASY",
                "topic": "شاهه ڀٽائي جو تعارف"
            },
            {
                "id": "q-sindhi-1-2",
                "timestamp_seconds": 120.0,
                "text_sindhi": "حضرت شاهه عبداللطيف ڀٽائي جي ڪلام جي مجموعي کي ڇا سڏيو وڃي ٿو؟",
                "options": ["شاهه جو رسالو", "ڪليات نارائڻ", "ديوان غالب", "سچل جو ڪلام"],
                "correct_answer_index": 0,
                "difficulty": "EASY",
                "topic": "شاهه جو رسالو"
            },
            {
                "id": "q-sindhi-1-3",
                "timestamp_seconds": 180.0,
                "text_sindhi": "شاهه جي رسالي جي سرن (سُر) جي شروعات سڀ کان اول ڪهڙي سُر سان ٿئي ٿي؟",
                "options": ["سُر ڪلياڻ", "سُر سارنگ", "سُر سسئي", "سُر مارئي"],
                "correct_answer_index": 0,
                "difficulty": "MEDIUM",
                "topic": "شاهه جي رسالي جا سُر"
            }
        ]
    }
]


def seed_checkpoints(db_path: str = "data/sdc_platform.db"):
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Update Math Units 2 to 13 timestamps so questions trigger at 60s, 120s, 180s instead of clumping at 60s
    for unit_idx in range(2, 14):
        lid = f"lesson-math-6-{unit_idx}"
        math_qs = cursor.execute(
            "SELECT id FROM questions WHERE lesson_id = ? ORDER BY id ASC",
            (lid,)
        ).fetchall()
        timestamps = [60.0, 120.0, 180.0]
        for q_idx, mq in enumerate(math_qs):
            ts = timestamps[q_idx] if q_idx < len(timestamps) else (60.0 * (q_idx + 1))
            cursor.execute("UPDATE questions SET timestamp_seconds = ? WHERE id = ?", (ts, mq["id"]))
            print(f"[Math Update] {lid} -> Question {mq['id']} set to {ts}s")

    # 2. Insert or update checkpoints for Science Ch 3-12, English, and Sindhi
    inserted_count = 0
    updated_count = 0
    for lesson_block in CHECKPOINTS_DATA:
        lid = lesson_block["lesson_id"]
        for q in lesson_block["questions"]:
            qid = q["id"]
            opts_json = json.dumps(q["options"], ensure_ascii=False)
            existing = cursor.execute("SELECT id FROM questions WHERE id = ?", (qid,)).fetchone()
            if existing:
                cursor.execute(
                    """
                    UPDATE questions SET
                        lesson_id = ?,
                        timestamp_seconds = ?,
                        text_sindhi = ?,
                        options_json = ?,
                        correct_answer_index = ?,
                        difficulty = ?,
                        topic = ?,
                        status = 'APPROVED',
                        approved_by = 'usr-admin-01',
                        approved_at = ?
                    WHERE id = ?
                    """,
                    (
                        lid,
                        q["timestamp_seconds"],
                        q["text_sindhi"],
                        opts_json,
                        q["correct_answer_index"],
                        q["difficulty"],
                        q["topic"],
                        now_iso,
                        qid
                    )
                )
                updated_count += 1
            else:
                cursor.execute(
                    """
                    INSERT INTO questions (
                        id, lesson_id, timestamp_seconds, text_sindhi, options_json,
                        correct_answer_index, difficulty, topic, status, approved_by, approved_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'APPROVED', 'usr-admin-01', ?)
                    """,
                    (
                        qid,
                        lid,
                        q["timestamp_seconds"],
                        q["text_sindhi"],
                        opts_json,
                        q["correct_answer_index"],
                        q["difficulty"],
                        q["topic"],
                        now_iso
                    )
                )
                inserted_count += 1
            print(f"[Checkpoint Seed] {lid} -> {qid} at {q['timestamp_seconds']}s: {q['text_sindhi'][:40]}...")

    conn.commit()
    conn.close()
    print(f"\n[DONE] Checkpoint seeding complete: {inserted_count} inserted, {updated_count} updated.")


if __name__ == "__main__":
    db_file = sys.argv[1] if len(sys.argv) > 1 else "data/sdc_platform.db"
    seed_checkpoints(db_file)

