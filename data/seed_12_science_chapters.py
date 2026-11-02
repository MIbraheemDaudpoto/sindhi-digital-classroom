import sqlite3
import sys

def seed_science_chapters():
    con = sqlite3.connect('data/sdc_platform.db')
    cur = con.cursor()

    chapters = [
        (1, 'جيو گهرڙو (The Cell - Basic Unit of Life)', 'The Cell - Basic Unit of Life', 'PDF 5-22'),
        (2, 'حواسن وارا عضوا (Sense Organs)', 'Sense Organs', 'PDF 23-36'),
        (3, 'روشنائي ترڪيب ۽ ساهه کڻڻ جو عمل (Photosynthesis & Respiration)', 'Photosynthesis and Respiration in Plants', 'PDF 37-44'),
        (4, 'ماحول ۽ ايڪوسسٽم (Environment and Ecosystem)', 'Environment and Ecosystem', 'PDF 45-58'),
        (5, 'ائٽمن ۽ ماليڪيولن جو تعارف (Atoms and Molecules)', 'Atoms, Molecules, Mixtures and Compounds', 'PDF 59-73'),
        (6, 'هوا ۽ ان جي اهميت (Air and Atmosphere)', 'Air and its Importance', 'PDF 74-82'),
        (7, 'محلول ۽ معلق ميلاپ (Solutions and Suspensions)', 'Solutions and Suspensions', 'PDF 83-95'),
        (8, 'توانائي ۽ ان جا قسم (Energy and Its Forms)', 'Energy and Its Forms', 'PDF 96-112'),
        (9, 'ساديون مشينون (Simple Machines)', 'Simple Machines: Pulleys, Wheels and Gears', 'PDF 113-126'),
        (10, 'روشنيءَ جو سفر ۽ موٽ (Transmission and Reflection of Light)', 'Transmission and Reflection of Light', 'PDF 127-141'),
        (11, 'آواز جو سفر ۽ خاصيتون (Sound and Its Propagation)', 'Sound and Its Properties', 'PDF 142-155'),
        (12, 'خلا ۽ مصنوعي سيارا (Space and Satellites)', 'Space, Satellites and Astronomy', 'PDF 156-170')
    ]

    # Delete previous science youtube entries
    cur.execute("DELETE FROM youtube_videos WHERE lesson_id LIKE 'lesson-sci-%';")

    for ch_id, title_sd, title_en, pdf in chapters:
        lesson_id = f'lesson-sci-6-{ch_id}'
        cur.execute('''
            INSERT INTO lessons (id, course_id, unit_number, title_sindhi, title_english, version, duration_seconds, status, summary_sindhi, created_at)
            VALUES (?, 'crs-sci-6', ?, ?, ?, 1, 720, 'PUBLISHED', ?, datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
                title_sindhi = excluded.title_sindhi,
                title_english = excluded.title_english,
                unit_number = excluded.unit_number,
                summary_sindhi = excluded.summary_sindhi,
                status = 'PUBLISHED'
        ''', (lesson_id, ch_id, title_sd, title_en, f'سنڌ ٽيڪسٽ بڪ بورڊ ڪلاس 6 عام سائنس، باب {ch_id} ({pdf}).'))

        # Link primary official video from sdc_videos
        cur.execute('SELECT id, watch_url, title, duration FROM sdc_videos WHERE chapter_id = ? ORDER BY id ASC LIMIT 1', (ch_id,))
        vrow = cur.fetchone()
        if vrow:
            vid_num, wurl, vtitle, vdur = vrow
            yt_id = wurl.split('v=')[-1] if 'v=' in wurl else wurl
            embed_url = f'https://www.youtube-nocookie.com/embed/{yt_id}'
            yt_record_id = f'yt-sci-6-{ch_id}'
            cur.execute('''
                INSERT INTO youtube_videos (id, lesson_id, youtube_id, title, channel_name, original_url, embed_url, class_level, subject, language, topic, duration_seconds, curriculum_status, attribution_text, is_embeddable, created_at)
                VALUES (?, ?, ?, ?, 'Sindh Online School (Nana Abid)', ?, ?, 6, 'Science', 'Sindhi', ?, 720, 'STBB_VERIFIED', 'سنڌ آن لائن اسڪول - نانا عابد (Sindh Online School)', 1, datetime('now'))
                ON CONFLICT(id) DO UPDATE SET
                    youtube_id = excluded.youtube_id,
                    title = excluded.title,
                    original_url = excluded.original_url,
                    embed_url = excluded.embed_url,
                    is_embeddable = 1
            ''', (yt_record_id, lesson_id, yt_id, vtitle, wurl, embed_url, title_sd))

    con.commit()
    con.close()
    print('SUCCESS: Seeded 12 Science chapters!')

if __name__ == '__main__':
    seed_science_chapters()
