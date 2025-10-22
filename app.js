// Author: Tim Smith
// Note: All Code owned by Tim

// API Configuration - UPDATE THIS URL after deploying backend
const API_URL = 'https://scholarship-api-6j7w.onrender.com'; // TODO: Update this after backend deployment

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
        skills: document.getElementById('skills').value,
        clubs: document.getElementById('clubs').value,
        athletics: document.getElementById('athletics').value,
        sort: document.getElementById('sort').value
    };

    // Show loading, hide results
    document.getElementById('loading').style.display = 'block';
    document.getElementById('results').style.display = 'none';
    document.getElementById('searchBtn').disabled = true;

    // DEBUG: Log what we're sending
    console.log('🔍 Sending to API:', formData);

    try {
        // Call API
        const response = await fetch(`${API_URL}/api/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });

        if (!response.ok) {
            throw new Error('Search failed');
        }

        const data = await response.json();

        // DEBUG: Log what we received
        console.log('✅ Received from API:', data.profile);

        if (data.success) {
            displayResults(data, formData);
        } else {
            alert('Error: ' + data.error);
        }

    } catch (error) {
        console.error('Error:', error);
        alert('Failed to search scholarships. Please try again or check your internet connection.');
    } finally {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('searchBtn').disabled = false;
    }
});

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
                <div class="scholarship-title">${scholarship.name}</div>
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
