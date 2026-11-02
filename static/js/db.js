// Client-side IndexedDB Storage for Sindhi Digital Classroom (SDC)
// Stores downloaded unit packs, offline video quiz questions, and queued attempts.
// Partitions records by student ID to protect shared-device privacy (FR-03, FR-19, FR-32).
// Authored under agency-frontend-developer and agency-application-security-engineer.

const DB_NAME = 'SDC_Offline_Store';
const DB_VERSION = 2;

function openSDCDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;

      if (!db.objectStoreNames.contains('unit_packs')) {
        db.createObjectStore('unit_packs', { keyPath: 'lesson_id' });
      }

      let queueStore;
      if (!db.objectStoreNames.contains('sync_queue')) {
        queueStore = db.createObjectStore('sync_queue', { keyPath: 'id', autoIncrement: true });
      } else {
        queueStore = event.target.transaction.objectStore('sync_queue');
      }
      if (queueStore && !queueStore.indexNames.contains('user_id')) {
        queueStore.createIndex('user_id', 'user_id', { unique: false });
      }

      if (db.objectStoreNames.contains('offline_progress')) {
        db.deleteObjectStore('offline_progress');
      }
      db.createObjectStore('offline_progress', { keyPath: 'user_lesson_key' });
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

// 1. Save Unit Pack (FR-32)
async function saveUnitPackOffline(pack) {
  const db = await openSDCDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('unit_packs', 'readwrite');
    const store = tx.objectStore('unit_packs');
    const item = {
      lesson_id: pack.lesson.id,
      pack: pack,
      downloaded_at: new Date().toISOString()
    };
    const req = store.put(item);
    req.onsuccess = () => resolve(true);
    req.onerror = () => reject(req.error);
  });
}

// 2. Retrieve Unit Pack Offline
async function getOfflineUnitPack(lessonId) {
  const db = await openSDCDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('unit_packs', 'readonly');
    const store = tx.objectStore('unit_packs');
    const req = store.get(lessonId);
    req.onsuccess = () => resolve(req.result ? req.result.pack : null);
    req.onerror = () => reject(req.error);
  });
}

// 3. Queue Offline Quiz Attempt with Student Isolation (FR-03, FR-19)
async function queueOfflineAttempt(attemptData, userId) {
  const db = await openSDCDatabase();
  const effectiveUserId = userId || (window.currentUser && window.currentUser.user_id) || 'usr-stu-101';
  return new Promise((resolve, reject) => {
    const tx = db.transaction('sync_queue', 'readwrite');
    const store = tx.objectStore('sync_queue');
    const item = {
      type: 'attempt',
      user_id: effectiveUserId,
      ...attemptData,
      queued_at: new Date().toISOString()
    };
    const req = store.add(item);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

// 4. Retrieve Queued Sync Items for the Active Student (FR-03 Account Isolation)
async function getSyncQueue(userId) {
  const db = await openSDCDatabase();
  const effectiveUserId = userId || (window.currentUser && window.currentUser.user_id);
  return new Promise((resolve, reject) => {
    const tx = db.transaction('sync_queue', 'readonly');
    const store = tx.objectStore('sync_queue');
    const req = store.getAll();
    req.onsuccess = () => {
      const items = req.result || [];
      if (!effectiveUserId) {
        resolve(items);
      } else {
        // Return only records belonging to this specific student
        resolve(items.filter(item => item.user_id === effectiveUserId));
      }
    };
    req.onerror = () => reject(req.error);
  });
}

// 5. Clear Sync Queue Only for the Synchronized Student (FR-03 Shared-Device Protection)
async function clearSyncQueue(userId) {
  const db = await openSDCDatabase();
  const effectiveUserId = userId || (window.currentUser && window.currentUser.user_id);
  return new Promise((resolve, reject) => {
    const tx = db.transaction('sync_queue', 'readwrite');
    const store = tx.objectStore('sync_queue');

    if (!effectiveUserId) {
      const req = store.clear();
      req.onsuccess = () => resolve(true);
      req.onerror = () => reject(req.error);
      return;
    }

    const req = store.openCursor();
    req.onsuccess = (event) => {
      const cursor = event.target.result;
      if (cursor) {
        if (cursor.value.user_id === effectiveUserId) {
          cursor.delete();
        }
        cursor.continue();
      } else {
        resolve(true);
      }
    };
    req.onerror = () => reject(req.error);
  });
}

// 6. Save Offline Progress Partitioned by Student
async function saveOfflineProgress(userId, lessonId, positionSeconds, isCompleted) {
  const db = await openSDCDatabase();
  const effectiveUserId = userId || (window.currentUser && window.currentUser.user_id) || 'usr-stu-101';
  return new Promise((resolve, reject) => {
    const tx = db.transaction('offline_progress', 'readwrite');
    const store = tx.objectStore('offline_progress');
    const item = {
      user_lesson_key: `${effectiveUserId}_${lessonId}`,
      user_id: effectiveUserId,
      lesson_id: lessonId,
      position_seconds: positionSeconds,
      is_completed: isCompleted,
      updated_at: new Date().toISOString()
    };
    const req = store.put(item);
    req.onsuccess = () => resolve(true);
    req.onerror = () => reject(req.error);
  });
}

// 7. Get Offline Progress Partitioned by Student
async function getOfflineProgress(userId, lessonId) {
  const db = await openSDCDatabase();
  const effectiveUserId = userId || (window.currentUser && window.currentUser.user_id) || 'usr-stu-101';
  return new Promise((resolve, reject) => {
    const tx = db.transaction('offline_progress', 'readonly');
    const store = tx.objectStore('offline_progress');
    const req = store.get(`${effectiveUserId}_${lessonId}`);
    req.onsuccess = () => resolve(req.result || null);
    req.onerror = () => reject(req.error);
  });
}
