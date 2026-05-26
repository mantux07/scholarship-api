// Author: Tim Smith
// Note: All Code owned by Tim

// API Configuration - uses relative URL since frontend and backend are on the same Vercel domain
const API_URL = '';

// Track which tab is active: 'scholarships' | 'research' | 'both'
let currentSearchType = 'scholarships';

function switchTab(type) {
    currentSearchType = type;
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    const active = document.querySelector(`.tab-btn[data-type="${type}"]`);
    if (active) active.classList.add('active');

    const searchBtn = document.getElementById('searchBtn');
    if (type === 'scholarships') searchBtn.innerHTML = '🔍 Search Scholarships';
    else if (type === 'research') searchBtn.innerHTML = '🔬 Search Research Opportunities';
    else searchBtn.innerHTML = '🎯 Search Both';
}

// ── Profile save / load (localStorage) ────────────────────────────────────────

const PROFILE_FIELDS = [
    'university','major','year','gpa','discipline','heritage','gender',
    'state','residency','skills','clubs','athletics','disability'
];
const CHECKBOX_FIELDS = ['first_gen','military','research'];

function saveProfile() {
    const profile = {};
    PROFILE_FIELDS.forEach(id => {
        const el = document.getElementById(id);
        if (el) profile[id] = el.value;
    });
    CHECKBOX_FIELDS.forEach(id => {
        const el = document.getElementById(id);
        if (el) profile[id] = el.checked;
    });
    localStorage.setItem('scholarshipProfile', JSON.stringify(profile));
    const banner = document.getElementById('savedProfileBanner');
    if (banner) { banner.style.display = 'block'; setTimeout(() => banner.style.display = 'none', 3000); }
}

function loadSavedProfile() {
    try {
        const saved = localStorage.getItem('scholarshipProfile');
        if (!saved) return;
        const profile = JSON.parse(saved);
        PROFILE_FIELDS.forEach(id => {
            const el = document.getElementById(id);
            if (el && profile[id] !== undefined) el.value = profile[id];
        });
        CHECKBOX_FIELDS.forEach(id => {
            const el = document.getElementById(id);
            if (el && profile[id] !== undefined) el.checked = profile[id];
        });
    } catch(e) { console.warn('Could not load saved profile:', e); }
}

function clearSavedProfile() {
    localStorage.removeItem('scholarshipProfile');
    document.getElementById('scholarshipForm').reset();
}

// Auto-load profile on page load
window.addEventListener('DOMContentLoaded', loadSavedProfile);

// ── Form submission ────────────────────────────────────────────────────────────

// Keep a reference to the last search formData for the subscription form
let lastFormData = null;

// Form submission handler
document.getElementById('scholarshipForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    // Get form data
    const formData = {
        university: document.getElementById('university').value,
        major: document.getElementById('major').value,
        year: document.getElementById('year').value,
        gpa: parseFloat(document.getElementById('gpa').value),
        discipline: document.getElementById('discipline').value,
        heritage: document.getElementById('heritage').value,
        gender: document.getElementById('gender').value,
        state: document.getElementById('state').value,
        residency: document.getElementById('residency').value,
        first_gen: document.getElementById('first_gen').checked,
        military: document.getElementById('military').checked,
        research: document.getElementById('research').checked,
        skills: document.getElementById('skills').value,
        clubs: document.getElementById('clubs').value,
        athletics: document.getElementById('athletics').value,
        disability: document.getElementById('disability').value,
        sort: document.getElementById('sort').value
    };

    // Show loading, hide results
    document.getElementById('loading').style.display = 'block';
    document.getElementById('results').style.display = 'none';
    const researchSection = document.getElementById('researchResults');
    if (researchSection) researchSection.style.display = 'none';
    document.getElementById('searchBtn').disabled = true;

    lastFormData = formData;
    console.log('Sending to API:', formData, 'searchType:', currentSearchType);

    try {
        if (currentSearchType === 'scholarships') {
            await searchScholarships(formData);
        } else if (currentSearchType === 'research') {
            await searchResearch(formData);
        } else {
            await Promise.all([searchScholarships(formData), searchResearch(formData)]);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to search. Please try again or check your internet connection.');
    } finally {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('searchBtn').disabled = false;
    }
});

async function searchScholarships(formData) {
    const response = await fetch(`${API_URL}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
    });
    if (!response.ok) throw new Error('Scholarship search failed');
    const data = await response.json();
    if (data.success) {
        displayResults(data, formData);
    } else {
        alert('Error: ' + data.error);
    }
}

async function searchResearch(formData) {
    const response = await fetch(`${API_URL}/api/research`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
    });
    if (!response.ok) throw new Error('Research search failed');
    const data = await response.json();
    if (data.success) {
        displayResearchResults(data, formData);
    } else {
        alert('Error: ' + data.error);
    }
}

// Display results
function displayResults(data, formData) {
    const resultsSection = document.getElementById('results');
    const profileSummary = document.getElementById('profileSummary');
    const statsGrid = document.getElementById('statsGrid');
    const scholarshipsList = document.getElementById('scholarshipsList');
    const downloadButtons = document.getElementById('downloadButtons');

    // Profile Summary
    profileSummary.innerHTML = `
        <h3>Your Profile</h3>
        <p><strong>🎓 University:</strong> ${data.profile.university}</p>
        <p><strong>📚 Major:</strong> ${data.profile.major} (${data.profile.year})</p>
        <p><strong>📊 GPA:</strong> ${data.profile.gpa}</p>
        ${data.profile.heritage !== 'Not specified' ? `<p><strong>🌍 Heritage:</strong> ${data.profile.heritage}</p>` : ''}
        ${data.profile.residency !== 'Not specified' ? `<p><strong>📍 Residency:</strong> ${data.profile.residency}</p>` : ''}
        ${data.profile.skills !== 'Not specified' ? `<p><strong>💡 Skills:</strong> ${data.profile.skills}</p>` : ''}
        ${data.profile.clubs !== 'Not specified' ? `<p><strong>🏛️ Clubs:</strong> ${data.profile.clubs}</p>` : ''}
        ${data.profile.athletics !== 'Not specified' ? `<p><strong>⚽ Athletics:</strong> ${data.profile.athletics}</p>` : ''}
        ${data.profile.first_gen ? '<p><strong>✨ First-Generation Student</strong></p>' : ''}
        ${data.profile.military ? '<p><strong>🎖️ Military Affiliated</strong></p>' : ''}
    `;

    // Statistics
    const sources = data.stats.sources || {};
    const sourceBreakdown = [
        sources.database ? `${sources.database} database` : '',
        sources.careeronestop ? `${sources.careeronestop} CareerOneStop` : '',
        sources.ai_suggested ? `${sources.ai_suggested} AI suggested` : '',
    ].filter(Boolean).join(' · ');

    statsGrid.innerHTML = `
        <div class="stat-card">
            <h3>${data.stats.total_scholarships}</h3>
            <p>Total Scholarships</p>
        </div>
        <div class="stat-card">
            <h3>${data.stats.gpa_eligible}</h3>
            <p>GPA Eligible</p>
        </div>
        <div class="stat-card">
            <h3>${data.stats.urgent_deadlines_30_days}</h3>
            <p>Urgent (30 Days)</p>
        </div>
        <div class="stat-card">
            <h3>${data.stats.total_potential_award}</h3>
            <p>Total Potential</p>
        </div>
    `;
    if (sourceBreakdown) {
        const note = document.createElement('p');
        note.style.cssText = 'color:#718096;font-size:0.85em;text-align:center;margin-bottom:16px';
        note.textContent = `Sources: ${sourceBreakdown}`;
        statsGrid.after(note);
    }

    // Download Buttons
    downloadButtons.innerHTML = `
        <button class="download-btn" onclick="downloadFile('csv', ${JSON.stringify(formData).replace(/"/g, '&quot;')})">
            📄 Download CSV
        </button>
        <button class="download-btn" onclick="downloadFile('excel', ${JSON.stringify(formData).replace(/"/g, '&quot;')})">
            📊 Download Excel
        </button>
        <button class="download-btn" onclick="downloadFile('pdf', ${JSON.stringify(formData).replace(/"/g, '&quot;')})">
            📑 Download PDF Report
        </button>
        <button class="download-btn" onclick="downloadFile('calendar', ${JSON.stringify(formData).replace(/"/g, '&quot;')})">
            📅 Download Calendar
        </button>
        <button class="download-btn" onclick="downloadFile('tracker', ${JSON.stringify(formData).replace(/"/g, '&quot;')})">
            ✅ Download Tracker
        </button>
        <button class="download-btn" onclick="downloadFile('html', ${JSON.stringify(formData).replace(/"/g, '&quot;')})">
            🌐 Download HTML Dashboard
        </button>
    `;

    // Scholarships List
    scholarshipsList.innerHTML = '<h2>🎯 Your Scholarship Matches</h2>';

    data.scholarships.forEach(scholarship => {
        const priorityClass = scholarship.priority_score >= 80 ? 'priority-high' :
                            scholarship.priority_score >= 65 ? 'priority-medium' : '';

        const deadlineClass = (scholarship.days_until_deadline !== 'TBD' &&
                              scholarship.days_until_deadline <= 30) ? 'deadline-urgent' : '';

        const competitivenessClass = {
            'Low': 'badge-low',
            'Medium': 'badge-medium',
            'High': 'badge-high',
            'Very High': 'badge-very-high'
        }[scholarship.competitiveness] || 'badge-medium';

        const card = document.createElement('div');
        card.className = `scholarship-card ${priorityClass}`;
        card.innerHTML = `
            <div class="scholarship-header">
                <div class="scholarship-title">
                    ${scholarship.name}
                    ${scholarship.source === 'CareerOneStop' ? '<span class="source-badge source-careeronestop">CareerOneStop</span>' : ''}
                    ${scholarship.source === 'AI Suggested' ? '<span class="source-badge source-ai">AI Suggested ✨</span>' : ''}
                </div>
                <div class="priority-badge">Priority: ${scholarship.priority_score}/100</div>
            </div>

            <div class="scholarship-details">
                <div class="detail-item">
                    <span class="detail-label">Award Amount</span>
                    <span class="detail-value">${scholarship.amount_display}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Deadline</span>
                    <span class="detail-value ${deadlineClass}">${scholarship.deadline}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Days Until Deadline</span>
                    <span class="detail-value ${deadlineClass}">${scholarship.days_until_deadline}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">GPA Requirement</span>
                    <span class="detail-value">${scholarship.min_gpa}+ / Rec: ${scholarship.recommended_gpa}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Competition Level</span>
                    <span class="badge ${competitivenessClass}">${scholarship.competitiveness}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Category</span>
                    <span class="detail-value">${scholarship.category}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Renewable</span>
                    <span class="detail-value">${scholarship.renewable ? '✅ Yes' : '❌ No'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Estimated Time</span>
                    <span class="detail-value">${scholarship.estimated_hours} hours</span>
                </div>
            </div>

            <div class="scholarship-details">
                <div class="detail-item">
                    <span class="detail-label">Essay Required</span>
                    <span class="detail-value">${scholarship.essay_required ? `✅ Yes (${scholarship.essay_word_count} words)` : '❌ No'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Recommendation Letters</span>
                    <span class="detail-value">${scholarship.rec_letters_required}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Interview Required</span>
                    <span class="detail-value">${scholarship.interview_required ? '✅ Yes' : '❌ No'}</span>
                </div>
            </div>

            ${scholarship.notes ? `
                <div class="scholarship-notes">
                    <strong>📝 Notes:</strong> ${scholarship.notes}
                </div>
            ` : ''}

            <a href="${scholarship.application_url}" target="_blank" class="apply-btn">
                🔗 Apply Now
            </a>
        `;

        scholarshipsList.appendChild(card);
    });

    // Show results, scroll to them
    resultsSection.style.display = 'block';
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Download file function
async function downloadFile(format, formData) {
    try {
        const response = await fetch(`${API_URL}/api/download/${format}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });

        if (!response.ok) {
            throw new Error('Download failed');
        }

        // Get filename from Content-Disposition header or use default
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = `scholarships.${format}`;
        if (contentDisposition) {
            const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(contentDisposition);
            if (matches != null && matches[1]) {
                filename = matches[1].replace(/['"]/g, '');
            }
        }

        // Download the file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

    } catch (error) {
        console.error('Download error:', error);
        alert('Failed to download file. Please try again.');
    }
}

// Form validation
document.getElementById('gpa').addEventListener('input', function(e) {
    const value = parseFloat(e.target.value);
    if (value > 4.0) {
        e.target.value = 4.0;
    } else if (value < 0) {
        e.target.value = 0;
    }
});

// ── Email alert subscription ───────────────────────────────────────────────────

async function subscribeAlerts() {
    const emailEl = document.getElementById('alertEmail');
    const msgEl = document.getElementById('alertMessage');
    const email = emailEl.value.trim();

    if (!email || !email.includes('@')) {
        msgEl.style.display = 'block';
        msgEl.style.background = '#fff5f5';
        msgEl.style.color = '#c53030';
        msgEl.textContent = 'Please enter a valid email address.';
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/subscribe`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, profile: lastFormData || {} })
        });
        const data = await response.json();

        msgEl.style.display = 'block';
        if (data.success) {
            msgEl.style.background = '#c6f6d5';
            msgEl.style.color = '#22543d';
            msgEl.textContent = '✅ Subscribed! Check your email for confirmation.';
            emailEl.value = '';
        } else {
            msgEl.style.background = '#fff5f5';
            msgEl.style.color = '#c53030';
            msgEl.textContent = 'Subscription failed. Please try again.';
        }
    } catch (err) {
        msgEl.style.display = 'block';
        msgEl.style.background = '#fff5f5';
        msgEl.style.color = '#c53030';
        msgEl.textContent = 'Could not connect. Please try again.';
    }
}

// ── Add chip value to field ────────────────────────────────────────────────────

// Add chip value to field
function addToField(fieldId, value, buttonElement) {
    const field = document.getElementById(fieldId);
    const currentValue = field.value.trim();

    if (currentValue === '' || currentValue === 'Not specified') {
        field.value = value;
    } else if (!currentValue.includes(value)) {
        field.value = currentValue + ', ' + value;
    }

    // Visual feedback
    buttonElement.style.background = '#48bb78';
    buttonElement.style.color = 'white';
    setTimeout(() => {
        buttonElement.style.background = '';
        buttonElement.style.color = '';
    }, 300);
}

// ── Research opportunity display ───────────────────────────────────────────────

function displayResearchResults(data, formData) {
    const section = document.getElementById('researchResults');
    const profileSummary = document.getElementById('researchProfileSummary');
    const statsGrid = document.getElementById('researchStatsGrid');
    const list = document.getElementById('opportunitiesList');
    const downloadButtons = document.getElementById('researchDownloadButtons');

    profileSummary.innerHTML = `
        <h3>Your Profile</h3>
        <p><strong>🎓 University:</strong> ${data.profile.university}</p>
        <p><strong>📚 Major:</strong> ${data.profile.major} (${data.profile.year})</p>
        <p><strong>📊 GPA:</strong> ${data.profile.gpa}</p>
        ${data.profile.discipline ? `<p><strong>🔬 Discipline:</strong> ${data.profile.discipline}</p>` : ''}
    `;

    statsGrid.innerHTML = `
        <div class="stat-card"><h3>${data.stats.total_opportunities}</h3><p>Total Opportunities</p></div>
        <div class="stat-card"><h3>${data.stats.paid_opportunities}</h3><p>Paid Programs</p></div>
        <div class="stat-card"><h3>${data.stats.average_stipend}</h3><p>Avg. Stipend</p></div>
        <div class="stat-card"><h3>${data.stats.with_housing}</h3><p>With Housing</p></div>
    `;

    if (downloadButtons && formData) {
        const fd = JSON.stringify(formData).replace(/"/g, '&quot;');
        downloadButtons.innerHTML = `
            <button class="download-btn" onclick="downloadResearchFile('csv', ${fd})">📄 Download CSV</button>
            <button class="download-btn" onclick="downloadResearchFile('excel', ${fd})">📊 Download Excel</button>
            <button class="download-btn" onclick="downloadResearchFile('pdf', ${fd})">📑 Download PDF Report</button>
            <button class="download-btn" onclick="downloadResearchFile('calendar', ${fd})">📅 Download Calendar</button>
            <button class="download-btn" onclick="downloadResearchFile('tracker', ${fd})">✅ Download Tracker</button>
        `;
    }

    list.innerHTML = '<h2>🎯 Your Research Matches</h2>';

    data.opportunities.forEach(opp => {
        const priorityClass = opp.priority_score >= 80 ? 'priority-high' :
                              opp.priority_score >= 65 ? 'priority-medium' : '';
        const competitivenessClass = {
            'Low': 'badge-low', 'Medium': 'badge-medium',
            'High': 'badge-high', 'Very High': 'badge-very-high'
        }[opp.competitiveness] || 'badge-medium';

        const card = document.createElement('div');
        card.className = `scholarship-card ${priorityClass}`;
        card.innerHTML = `
            <div class="scholarship-header">
                <div class="scholarship-title">${opp.name}</div>
                <div class="priority-badge">Priority: ${opp.priority_score}/100</div>
            </div>

            <div class="research-meta">
                <span class="research-org">🏛️ ${opp.organization}</span>
                <span class="research-category">${opp.category}</span>
            </div>

            <div class="scholarship-details">
                <div class="detail-item"><span class="detail-label">Compensation</span><span class="detail-value">${opp.stipend_display}</span></div>
                <div class="detail-item"><span class="detail-label">Duration</span><span class="detail-value">${opp.duration}</span></div>
                <div class="detail-item"><span class="detail-label">Location</span><span class="detail-value">${opp.location}</span></div>
                <div class="detail-item"><span class="detail-label">Deadline</span><span class="detail-value">${opp.deadline}</span></div>
                <div class="detail-item"><span class="detail-label">GPA Requirement</span><span class="detail-value">${opp.gpa_min}+ / Preferred: ${opp.gpa_preferred}</span></div>
                <div class="detail-item"><span class="detail-label">Competition Level</span><span class="badge ${competitivenessClass}">${opp.competitiveness}</span></div>
            </div>

            <div class="research-benefits">
                ${opp.housing_provided ? '<span class="benefit-badge">🏠 Housing Provided</span>' : ''}
                ${opp.travel_covered ? '<span class="benefit-badge">✈️ Travel Covered</span>' : ''}
            </div>

            <div class="research-details">
                <p><strong>🔬 Research Area:</strong> ${opp.research_area}</p>
                <p><strong>📝 Description:</strong> ${opp.description}</p>
                <p><strong>💡 Application Tips:</strong> ${opp.application_tips}</p>
            </div>

            <a href="${opp.application_url}" target="_blank" class="apply-btn">🔗 Apply Now</a>
        `;
        list.appendChild(card);
    });

    section.style.display = 'block';
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function downloadResearchFile(format, formData) {
    try {
        const response = await fetch(`${API_URL}/api/research/download/${format}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        if (!response.ok) throw new Error('Download failed');

        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = `research_opportunities.${format}`;
        if (contentDisposition) {
            const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(contentDisposition);
            if (matches != null && matches[1]) filename = matches[1].replace(/['"]/g, '');
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = filename;
        document.body.appendChild(a); a.click();
        window.URL.revokeObjectURL(url); document.body.removeChild(a);
    } catch (error) {
        console.error('Research download error:', error);
        alert('Failed to download research file. Please try again.');
    }
}
