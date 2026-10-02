// SkillMatch — LocalStorage Persistence Layer
// Manages student profile, bookmarks, and application status

const SK = {
  STUDENT: 'skillmatch_student_v1',
  BOOKMARKS: 'skillmatch_bookmarks_v1',
  APPLICATIONS: 'skillmatch_applications_v1',
  FILTERS: 'skillmatch_filters_v1'
};

// ── Student Profile ──────────────────────────────────────────
function getStudent() {
  try {
    const d = localStorage.getItem(SK.STUDENT);
    return d ? JSON.parse(d) : null;
  } catch { return null; }
}

function saveStudent(student) {
  localStorage.setItem(SK.STUDENT, JSON.stringify({
    ...student,
    updatedAt: new Date().toISOString()
  }));
}

function clearStudent() {
  localStorage.removeItem(SK.STUDENT);
}

// ── Bookmarks ────────────────────────────────────────────────
function getBookmarks() {
  try {
    const d = localStorage.getItem(SK.BOOKMARKS);
    return d ? JSON.parse(d) : [];
  } catch { return []; }
}

function addBookmark(oppId) {
  const bm = getBookmarks();
  if (!bm.includes(oppId)) {
    bm.push(oppId);
    localStorage.setItem(SK.BOOKMARKS, JSON.stringify(bm));
  }
}

function removeBookmark(oppId) {
  const bm = getBookmarks().filter(id => id !== oppId);
  localStorage.setItem(SK.BOOKMARKS, JSON.stringify(bm));
}

function toggleBookmark(oppId) {
  if (isBookmarked(oppId)) { removeBookmark(oppId); return false; }
  else { addBookmark(oppId); return true; }
}

function isBookmarked(oppId) {
  return getBookmarks().includes(oppId);
}

// ── Applications / Status Tracking ───────────────────────────
const APP_STATUSES = [
  { key: 'saved',       label: 'Saved',       icon: '🔖', color: '#7c3aed' },
  { key: 'applied',     label: 'Applied',     icon: '📤', color: '#06b6d4' },
  { key: 'shortlisted', label: 'Shortlisted', icon: '⭐', color: '#f59e0b' },
  { key: 'selected',    label: 'Selected',    icon: '🎉', color: '#10b981' },
  { key: 'rejected',    label: 'Not Selected',icon: '❌', color: '#ef4444' }
];

function getApplications() {
  try {
    const d = localStorage.getItem(SK.APPLICATIONS);
    return d ? JSON.parse(d) : {};
  } catch { return {}; }
}

function updateApplicationStatus(oppId, status) {
  const apps = getApplications();
  apps[oppId] = {
    status,
    updatedAt: new Date().toISOString(),
    history: [
      ...((apps[oppId] && apps[oppId].history) || []),
      { status, at: new Date().toISOString() }
    ]
  };
  localStorage.setItem(SK.APPLICATIONS, JSON.stringify(apps));
  // Auto-bookmark when applying
  if (status !== 'saved') addBookmark(oppId);
}

function getApplicationStatus(oppId) {
  const apps = getApplications();
  return apps[oppId] || null;
}

// ── Filters ──────────────────────────────────────────────────
function saveFilters(filters) {
  localStorage.setItem(SK.FILTERS, JSON.stringify(filters));
}

function getFilters() {
  try {
    const d = localStorage.getItem(SK.FILTERS);
    return d ? JSON.parse(d) : { type: 'all', skill: '', search: '' };
  } catch { return { type: 'all', skill: '', search: '' }; }
}

// ── Auth Guard ───────────────────────────────────────────────
function requireProfile(redirectTo = 'index.html') {
  const student = getStudent();
  if (!student || !student.name) {
    window.location.href = redirectTo;
    return null;
  }
  return student;
}

// ── Utilities ────────────────────────────────────────────────
function getInitials(name) {
  return (name || 'U')
    .split(' ')
    .map(w => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

function formatDeadline(deadlineStr) {
  const d = new Date(deadlineStr);
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

function getTimeAgo(dateStr) {
  const d = new Date(dateStr);
  const diff = Date.now() - d.getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 30) return `${days}d ago`;
  return `${Math.floor(days / 30)}mo ago`;
}
