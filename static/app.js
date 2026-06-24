const state = {
    token: localStorage.getItem('session_token') || null,
    username: localStorage.getItem('session_username') || null,
    role: localStorage.getItem('session_role') || null,
    currentView: 'analysis',
    queueInterval: null,
    dashboardCharts: {
        pie: null,
        bar: null,
        trend: null
    },
    usageChart: null,
    selectedUploadFiles: []
};

if (localStorage.getItem('theme') === 'dark') {
    document.body.classList.add('dark-mode');
}

const API_BASE = window.location.origin;

function escapeHTML(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// ── TOAST SYSTEM ──
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let icon = '<i class="fa-solid fa-circle-info"></i>';
    if (type === 'success') icon = '<i class="fa-solid fa-circle-check"></i>';
    if (type === 'error') icon = '<i class="fa-solid fa-circle-xmark"></i>';
    if (type === 'warning') icon = '<i class="fa-solid fa-triangle-exclamation"></i>';

    toast.innerHTML = `${icon}<span>${escapeHTML(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease-out reverse';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ── API HELPERS ──
async function apiFetch(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...(state.token ? { 'Authorization': `Bearer ${state.token}` } : {}),
        ...options.headers
    };

    const config = {
        ...options,
        headers
    };

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, config);

        if (response.status === 401) {
            // Token expired or invalid -> log out
            logout();
            showToast('Session expired. Please sign in again.', 'warning');
            throw new Error('Unauthorized');
        }

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Server error: ${response.status}`);
        }

        // Handle PDF downloads or binary responses
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/pdf')) {
            return await response.blob();
        }

        return await response.json();
    } catch (err) {
        console.error(`API Fetch Error (${endpoint}):`, err);
        throw err;
    }
}

// ── AUTHENTICATION ──
async function handleLogin(e) {
    e.preventDefault();
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const errorEl = document.getElementById('login-error');

    errorEl.style.display = 'none';

    try {
        const data = await apiFetch('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({
                username: usernameInput.value,
                password: passwordInput.value
            })
        });

        // Set session state
        state.token = data.token;
        state.username = data.username;
        state.role = data.role;

        localStorage.setItem('session_token', data.token);
        localStorage.setItem('session_username', data.username);
        localStorage.setItem('session_role', data.role);

        showToast(`Welcome back, ${data.username}!`, 'success');
        initApp();
    } catch (err) {
        errorEl.textContent = `❌ ${err.message || 'Login failed. Check credentials.'}`;
        errorEl.style.display = 'block';
    }
}

function logout() {
    state.token = null;
    state.username = null;
    state.role = null;

    localStorage.removeItem('session_token');
    localStorage.removeItem('session_username');
    localStorage.removeItem('session_role');

    // Clear interval timers
    if (state.queueInterval) {
        clearInterval(state.queueInterval);
        state.queueInterval = null;
    }

    // Toggle views
    document.getElementById('login-container').style.display = 'flex';
    document.getElementById('app-container').style.display = 'none';

    // Clear forms
    document.getElementById('login-form').reset();
}

// ── APP INITIALIZATION ──
async function initApp() {
    if (!state.token) {
        document.getElementById('login-container').style.display = 'flex';
        document.getElementById('app-container').style.display = 'none';
        return;
    }

    // Toggle view visibility
    document.getElementById('login-container').style.display = 'none';
    document.getElementById('app-container').style.display = 'flex';

    // Update User Info Card in Sidebar
    document.getElementById('user-display-name').textContent = state.username;
    document.getElementById('user-display-role').textContent = state.role;

    const roleIconMap = { admin: '🛡️', supervisor: '👔' };
    document.getElementById('user-role-icon').textContent = roleIconMap[state.role] || '👤';

    // Show/Hide Role-Based navigation links
    const supervisorLinks = document.querySelectorAll('.supervisor-only');
    const adminLinks = document.querySelectorAll('.admin-only');

    if (state.role === 'admin' || state.role === 'supervisor') {
        supervisorLinks.forEach(el => el.style.display = 'flex');
    } else {
        supervisorLinks.forEach(el => el.style.display = 'none');
    }

    if (state.role === 'admin') {
        adminLinks.forEach(el => el.style.display = 'flex');
    } else {
        adminLinks.forEach(el => el.style.display = 'none');
    }

    // Router default view load
    showView(state.currentView);
}

// ── NAVIGATION ROUTER ──
function showView(viewId) {
    state.currentView = viewId;

    // Clear auto-refresh if switching away from Analysis view
    if (viewId !== 'analysis' && state.queueInterval) {
        clearInterval(state.queueInterval);
        state.queueInterval = null;
        document.getElementById('queue-auto-refresh').checked = false;
    }

    // Hide all views
    document.querySelectorAll('.app-view').forEach(view => {
        view.style.display = 'none';
    });

    // Show selected view
    const viewEl = document.getElementById(`view-${viewId}`);
    if (viewEl) viewEl.style.display = 'block';

    // Set active link class in sidebar
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.getAttribute('data-view') === viewId) {
            item.classList.add('active');
        }
    });

    // Load page data
    if (viewId === 'analysis') loadQueue();
    else if (viewId === 'review') loadReviewList();
    else if (viewId === 'dashboard') loadDashboard();
    else if (viewId === 'manage') loadHistoryManage();
    else if (viewId === 'settings') loadSettings();
    else if (viewId === 'logs') loadLogs();
    else if (viewId === 'usage') loadUsageTracker();
}

// ── VIEW: ANALYSIS STAGE ──
function loadQueue() {
    apiFetch('/api/analysis/queue')
        .then(data => {
            const container = document.getElementById('queue-items-container');
            container.innerHTML = '';

            if (data.length === 0) {
                container.innerHTML = '<div class="info-msg">Queue is empty. Upload recordings to get started.</div>';
                return;
            }

            data.forEach(item => {
                const badgeClass = `badge-${item.status.toLowerCase()}`;
                let errText = '';
                if (item.status === 'Failed' && item.error_msg) {
                    errText = `<div style="font-size:0.75rem; color:var(--danger-color); margin-top:4px;">⚠️ ${escapeHTML(item.error_msg)}</div>`;
                }

                const card = document.createElement('div');
                card.className = 'queue-card';
                card.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center; gap: 8px;">
                        <span style="font-size:0.88rem; font-weight:600; color:var(--secondary-color); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:260px;" title="${escapeHTML(item.filename)}">${escapeHTML(item.filename)}</span>
                        <span class="badge ${badgeClass}">${escapeHTML(item.status)}</span>
                    </div>
                    ${errText}
                `;
                container.appendChild(card);
            });
        })
        .catch(err => {
            showToast('Failed to load queue: ' + err.message, 'error');
        });
}

function handleAutoRefreshChange(e) {
    if (e.target.checked) {
        state.queueInterval = setInterval(loadQueue, 5000);
        showToast('Auto-refresh activated.', 'success');
    } else {
        if (state.queueInterval) {
            clearInterval(state.queueInterval);
            state.queueInterval = null;
            showToast('Auto-refresh deactivated.', 'info');
        }
    }
}

function setupDropZone() {
    const zone = document.getElementById('file-drop-zone');
    const input = document.getElementById('audio-files');
    const preview = document.getElementById('file-list-preview');
    const launchBtn = document.getElementById('launch-analysis-btn');

    zone.addEventListener('click', () => input.click());

    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('dragover');
    });

    zone.addEventListener('dragleave', () => {
        zone.classList.remove('dragover');
    });

    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            addSelectedFiles(e.dataTransfer.files);
        }
    });

    input.addEventListener('change', () => {
        if (input.files.length > 0) {
            addSelectedFiles(input.files);
        }
    });

    function addSelectedFiles(filesList) {
        for (let i = 0; i < filesList.length; i++) {
            const f = filesList[i];
            const nameLower = f.name.toLowerCase();
            if (nameLower.endsWith('.mp3') || nameLower.endsWith('.wav')) {
                // Check if already in list
                if (!state.selectedUploadFiles.some(file => file.name === f.name)) {
                    state.selectedUploadFiles.push(f);
                }
            } else {
                showToast(`Unsupported file type: ${f.name}. Only MP3/WAV supported.`, 'warning');
            }
        }
        renderFilePreviews();
    }

    function renderFilePreviews() {
        preview.innerHTML = '';
        if (state.selectedUploadFiles.length === 0) {
            launchBtn.disabled = true;
            return;
        }

        state.selectedUploadFiles.forEach((file, index) => {
            const item = document.createElement('div');
            item.className = 'file-preview-item';
            item.innerHTML = `
                <span>${escapeHTML(file.name)} (${(file.size / (1024 * 1024)).toFixed(2)} MB)</span>
                <button type="button" data-index="${index}"><i class="fa-solid fa-trash-can"></i></button>
            `;

            item.querySelector('button').addEventListener('click', (e) => {
                const idx = parseInt(e.currentTarget.getAttribute('data-index'));
                state.selectedUploadFiles.splice(idx, 1);
                renderFilePreviews();
            });
            preview.appendChild(item);
        });

        launchBtn.disabled = false;
    }

    launchBtn.addEventListener('click', async () => {
        if (state.selectedUploadFiles.length === 0) return;

        launchBtn.disabled = true;
        launchBtn.textContent = '🚀 Launching...';

        const formData = new FormData();
        state.selectedUploadFiles.forEach(file => {
            formData.append('files', file);
        });

        try {
            await apiFetch('/api/analysis/upload', {
                method: 'POST',
                headers: {
                    // Omit Content-Type header to let browser configure Multipart boundary correctly
                    'Content-Type': undefined
                },
                body: formData
            });

            showToast('Analysis launched successfully!', 'success');
            state.selectedUploadFiles = [];
            renderFilePreviews();
            loadQueue();
        } catch (err) {
            showToast('Failed to start analysis: ' + err.message, 'error');
        } finally {
            launchBtn.textContent = '🚀 Launch Analysis';
            launchBtn.disabled = false;
        }
    });
}

// ── VIEW: REVIEW & AUDIT ──
let currentAuditTaskId = null;

async function loadReviewList() {
    const showVerified = document.getElementById('show-verified-checkbox').checked;
    const select = document.getElementById('review-task-select');
    const search = document.getElementById('review-search-filename').value.toLowerCase();

    try {
        const data = await apiFetch(`/api/review/list?show_verified=${showVerified}`);
        select.innerHTML = '<option value="">-- Choose a report to audit --</option>';

        const filtered = data.filter(t => t.filename.toLowerCase().includes(search));

        filtered.forEach(task => {
            const opt = document.createElement('option');
            opt.value = task.id;
            const statusText = task.is_verified ? ' [VERIFIED]' : '';
            opt.textContent = `${task.filename} (${task.created_at})${statusText}`;
            select.appendChild(opt);
        });

        // Restore selection if relevant
        if (currentAuditTaskId) {
            select.value = currentAuditTaskId;
        }
    } catch (err) {
        showToast('Failed to load completed reports: ' + err.message, 'error');
    }
}

async function handleReviewTaskSelect(e) {
    const taskId = e.target.value;
    currentAuditTaskId = taskId || null;

    const workspace = document.getElementById('review-workspace');
    const msg = document.getElementById('no-reports-msg');

    if (!taskId) {
        workspace.style.display = 'none';
        msg.style.display = 'block';
        return;
    }

    try {
        const data = await apiFetch(`/api/review/report/${taskId}`);

        msg.style.display = 'none';
        workspace.style.display = 'grid';

        renderAuditWorkspace(data);
    } catch (err) {
        showToast('Failed to load report detail: ' + err.message, 'error');
        workspace.style.display = 'none';
        msg.style.display = 'block';
    }
}

function renderAuditWorkspace(taskReport) {
    const res = taskReport.report;
    const isVerified = !!taskReport.call_id;

    // Header Status Card
    const callStatus = res.Call_Status || 'PENDING';
    const overallStatus = res.Overall_Status || (res.Score >= 70 ? 'Pass' : 'Fail');
    const isPass = String(overallStatus).trim().toUpperCase() === 'PASS' || String(callStatus).trim().toUpperCase().includes('PASS');

    const scoreColor = isPass ? 'var(--success-color)' : 'var(--danger-color)';

    const headerCard = document.getElementById('rev-header-card');
    headerCard.style.borderLeft = `5px solid ${scoreColor}`;

    document.getElementById('rev-agent-name').textContent = res.Agent_Name || 'N/A';
    
    const totalScoreEl = document.getElementById('rev-total-score');
    totalScoreEl.textContent = isPass ? 'PASS' : 'FAIL';
    totalScoreEl.style.color = scoreColor;
    totalScoreEl.style.fontSize = '2.2rem';
    totalScoreEl.style.fontWeight = '800';

    const statusBadge = document.getElementById('rev-call-status');
    statusBadge.textContent = isPass ? 'CLEAN PASS' : 'FAILED AUDIT';
    statusBadge.className = 'badge';
    if (isPass) {
        statusBadge.classList.add('badge-completed');
    } else {
        statusBadge.classList.add('badge-failed');
    }

    // Toggle Auto-Fail Banner
    const autofailBanner = document.getElementById('rev-autofail-banner');
    if (!isPass) {
        const reason = res.Auto_Fail_Reason || res.Compliance_Checklist?.Behavior_Flag || 'General compliance failure.';
        const rootcause = res.Root_Cause_Analysis || res.Detailed_Analysis?.Main_Problem || 'Root cause and quotes are detailed below.';
        
        document.getElementById('rev-autofail-reason').textContent = reason;
        document.getElementById('rev-autofail-rootcause').textContent = rootcause;
        autofailBanner.style.display = 'block';
    } else {
        autofailBanner.style.display = 'none';
    }

    document.getElementById('rev-patient-name').textContent = res.Customer_Name || res.Patient_Name || 'N/A';
    document.getElementById('rev-patient-phone').textContent = res.Customer_Phone || res.Patient_Phone || 'N/A';
    document.getElementById('rev-campaign-name').textContent = res.Campaign || 'N/A';
    document.getElementById('rev-call-type').textContent = res.Call_Type || 'N/A';
    document.getElementById('rev-fcr-status').textContent = res.FCR || 'N/A';
    document.getElementById('rev-customer-feedback').textContent = res.Customer_Feedback || 'N/A';

    // Detailed Narratives
    const analysis = res.Detailed_Analysis || {};
    document.getElementById('rev-narrative').textContent = analysis.Human_Narrative || 'N/A';
    document.getElementById('rev-problem').textContent = analysis.Main_Problem || 'N/A';
    document.getElementById('rev-coaching').textContent = analysis.Proposed_Solution || 'N/A';

    // Strengths list
    const strengthsContainer = document.getElementById('rev-strengths-list');
    strengthsContainer.innerHTML = '';
    const strengths = analysis.Strengths || [];
    if (strengths.length === 0) {
        strengthsContainer.innerHTML = '<em style="color:#94a3b8;">No strengths recorded</em>';
    } else {
        strengths.forEach(pt => {
            const d = document.createElement('div');
            d.style.padding = '6px 0';
            d.style.borderBottom = '1px solid #f8fafc';
            d.innerHTML = `✅ ${escapeHTML(pt)}`;
            strengthsContainer.appendChild(d);
        });
    }

    // Weaknesses list
    const weaknessesContainer = document.getElementById('rev-weaknesses-list');
    weaknessesContainer.innerHTML = '';
    const weaknesses = analysis.Weaknesses || [];
    if (weaknesses.length === 0) {
        weaknessesContainer.innerHTML = '<em style="color:#94a3b8;">No weaknesses recorded</em>';
    } else {
        weaknesses.forEach(pt => {
            const d = document.createElement('div');
            d.style.padding = '6px 0';
            d.style.borderBottom = '1px solid #f8fafc';
            d.innerHTML = `❌ ${escapeHTML(pt)}`;
            weaknessesContainer.appendChild(d);
        });
    }

    // Form settings
    const callIdInput = document.getElementById('audit-call-id');
    const agentInput = document.getElementById('audit-agent-name');
    const approveBtn = document.getElementById('approve-audit-btn');
    const downloadBtn = document.getElementById('download-pdf-btn');
    const successBanner = document.getElementById('verified-success-banner');

    callIdInput.value = taskReport.call_id || '';
    agentInput.value = res.Agent_Name || '';

    if (isVerified) {
        callIdInput.disabled = true;
        agentInput.disabled = true;
        approveBtn.style.display = 'none';
        downloadBtn.style.display = 'block';
        successBanner.style.display = 'flex';
    } else {
        callIdInput.disabled = false;
        agentInput.disabled = false;
        approveBtn.style.display = 'block';
        downloadBtn.style.display = 'none';
        successBanner.style.display = 'none';
    }

    // Detailed Categories (Status Badges)
    const categoriesContainer = document.getElementById('rev-categories-container');
    categoriesContainer.innerHTML = '';
    const scoringData = res.Detailed_Scoring || {};

    Object.keys(scoringData).forEach(cat => {
        const catData = scoringData[cat];
        const resVal = String(catData.result || 'Pass').trim();
        const resUpper = resVal.toUpperCase();

        let badgeBg, badgeColor, badgeText;
        if (resUpper === 'PASS') {
            badgeBg = '#DEF7EC';
            badgeColor = '#03543F';
            badgeText = 'Pass';
        } else if (resUpper === 'FAIL') {
            badgeBg = '#FDE8E8';
            badgeColor = '#9B1C1C';
            badgeText = 'Fail';
        } else {
            badgeBg = '#E5E7EB';
            badgeColor = '#374151';
            badgeText = 'N/A';
        }

        const label = cat.replace(/_/g, ' ');

        const card = document.createElement('div');
        card.style.marginBottom = '12px';
        card.style.border = '1px solid var(--border-color)';
        card.style.padding = '12px';
        card.style.borderRadius = '8px';
        card.style.background = 'white';
        card.style.boxShadow = '0 1px 2px rgba(0, 0, 0, 0.05)';
        
        let feedbackHtml = '';
        if (catData.feedback) {
            feedbackHtml = `
                <div style="font-size:0.75rem; color:#475569; margin-top:8px; line-height:1.4; padding-top:8px; border-top:1px dashed #f1f5f9; font-style:italic;">
                    "${escapeHTML(catData.feedback)}"
                </div>
            `;
        }

        card.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:600; font-size:0.82rem; color:var(--secondary-color);">${escapeHTML(label)}</span>
                <span style="font-weight:600; font-size:0.75rem; padding:3px 8px; border-radius:12px; background:${badgeBg}; color:${badgeColor}; text-transform:uppercase; letter-spacing:0.025em;">${badgeText}</span>
            </div>
            ${feedbackHtml}
        `;
        categoriesContainer.appendChild(card);
    });

    // Compliance Checklist
    const complianceContainer = document.getElementById('rev-compliance-container');
    complianceContainer.innerHTML = '';
    const checklist = res.Compliance_Checklist || {};

    Object.keys(checklist).forEach(key => {
        const val = checklist[key];
        const label = key.replace(/_/g, ' ');
        const valUpper = String(val).trim().toUpperCase();

        let badgeHtml = `<span style="color:var(--text-light); font-weight:700; font-size:0.8rem;">${escapeHTML(val)}</span>`;
        if (["YES", "PASS", "TRUE", "✅"].includes(valUpper)) {
            badgeHtml = `<span style="color:var(--success-color); font-weight:700; font-size:0.8rem;">✅ ${escapeHTML(val)}</span>`;
        } else if (["NO", "FAIL", "FALSE", "❌"].includes(valUpper)) {
            badgeHtml = `<span style="color:var(--danger-color); font-weight:700; font-size:0.8rem;">❌ ${escapeHTML(val)}</span>`;
        }

        const row = document.createElement('div');
        row.style.display = 'flex';
        row.style.justifyContent = 'space-between';
        row.style.alignItems = 'center';
        row.style.padding = '8px 0';
        row.style.borderBottom = '1px solid #f1f5f9';
        row.style.fontSize = '0.8rem';
        row.innerHTML = `
            <span style="color:var(--secondary-color); font-weight:500;">${escapeHTML(label)}</span>
            ${badgeHtml}
        `;
        complianceContainer.appendChild(row);
    });

    // Verification Audits (checks)
    const verificationSection = document.getElementById('rev-verification-audits-section');
    const verificationContainer = document.getElementById('rev-verification-container');
    verificationContainer.innerHTML = '';

    const verif = res.Verification_Audit || {};
    const verifItems = Object.entries(verif);

    if (verifItems.length > 0) {
        verificationSection.style.display = 'block';
        verifItems.forEach(([vkey, vdata]) => {
            const status = vdata.status || 'N/A';
            const evidence = vdata.evidence || 'N/A';
            const vcolor = status.toLowerCase().includes('confirm') ? 'var(--success-color)' : 'var(--danger-color)';

            const card = document.createElement('div');
            card.className = 'report-section';
            card.style.padding = '12px';
            card.style.borderTop = `3px solid ${vcolor}`;
            card.style.marginBottom = '10px';
            card.innerHTML = `
                <div style="font-weight:700; color:var(--secondary-color); font-size:0.8rem; margin-bottom:2px;">${escapeHTML(vkey.replace(/_/g,' '))}</div>
                <div style="font-size:0.78rem; color:${vcolor}; font-weight:600; margin-bottom:4px;">${escapeHTML(status)}</div>
                <div style="font-size:0.74rem; color:var(--text-light); font-style:italic;">"${escapeHTML(evidence)}"</div>
            `;
            verificationContainer.appendChild(card);
        });
    } else {
        verificationSection.style.display = 'none';
    }
}

async function handleAuditFormSubmit(e) {
    e.preventDefault();
    if (!currentAuditTaskId) return;

    const callId = document.getElementById('audit-call-id').value.trim();
    const agentName = document.getElementById('audit-agent-name').value.trim();
    const approveBtn = document.getElementById('approve-audit-btn');

    approveBtn.disabled = true;
    approveBtn.textContent = 'Saving...';

    try {
        await apiFetch('/api/review/approve', {
            method: 'POST',
            body: JSON.stringify({
                task_id: parseInt(currentAuditTaskId),
                call_id: callId,
                agent_name: agentName
            })
        });

        showToast(`Audit saved successfully under Call ID: ${callId}`, 'success');
        // Reload list and refresh selection report details
        await loadReviewList();

        // Reload report data
        const data = await apiFetch(`/api/review/report/${currentAuditTaskId}`);
        renderAuditWorkspace(data);
    } catch (err) {
        showToast('Failed to approve audit: ' + err.message, 'error');
    } finally {
        approveBtn.disabled = false;
        approveBtn.textContent = '✅ Approve & Save to History';
    }
}

async function handlePDFDownload() {
    if (!currentAuditTaskId) return;
    try {
        const blob = await apiFetch(`/api/review/download/${currentAuditTaskId}`);
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Audit_Report_${currentAuditTaskId}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    } catch (err) {
        showToast('Download PDF failed: ' + err.message, 'error');
    }
}

// ── VIEW: PERFORMANCE DASHBOARD ──
async function loadDashboard() {
    const period = document.getElementById('dashboard-period').value;

    try {
        // 1. Fetch Stats
        const stats = await apiFetch(`/api/dashboard/stats?period=${period}`);
        document.getElementById('kpi-total-audits').textContent = stats.total_audits;
        const avgScoreEl = document.getElementById('kpi-avg-score');
        if (avgScoreEl) {
            avgScoreEl.textContent = stats.avg_score;
        }
        document.getElementById('kpi-sales').textContent = stats.sales_closed;
        document.getElementById('kpi-pass-rate').textContent = `${stats.pass_rate}%`;
        document.getElementById('kpi-transfers').textContent = stats.transfers;

        // 2. Fetch Compliance rates
        const complianceData = await apiFetch(`/api/dashboard/compliance?period=${period}`);
        const compGrid = document.getElementById('compliance-rates-grid');
        compGrid.innerHTML = '';

        complianceData.forEach(item => {
            let color = 'var(--danger-color)';
            if (item.rate >= 80) color = 'var(--success-color)';
            else if (item.rate >= 60) color = 'var(--warning-color)';

            const card = document.createElement('div');
            card.className = 'compliance-metric-card';
            card.innerHTML = `
                <div style="font-size: 0.75rem; color:var(--text-light); font-weight:700; text-transform:uppercase; height:36px; display:flex; align-items:center; justify-content:center; line-height:1.2;">${escapeHTML(item.label)}</div>
                <div style="font-size: 1.8rem; font-weight:900; color: ${color}; margin-top:8px;">${escapeHTML(item.rate)}%</div>
            `;
            compGrid.appendChild(card);
        });

        // 3. Fetch Leaderboard
        const leaderboardData = await apiFetch(`/api/dashboard/leaderboard?period=${period}`);
        const leadContainer = document.getElementById('leaderboard-container');
        leadContainer.innerHTML = '';

        if (leaderboardData.length === 0) {
            leadContainer.innerHTML = '<div class="info-msg" style="padding: 12px;">No leaderboard data available for the period.</div>';
        } else {
            const medals = { 1: "🥇", 2: "🥈", 3: "🥉" };
            leaderboardData.forEach(row => {
                const medal = medals[row.rank] || `#${row.rank}`;
                let scoreColor = 'var(--danger-color)';
                if (row.avg_score >= 80) scoreColor = 'var(--success-color)';
                else if (row.avg_score >= 70) scoreColor = 'var(--warning-color)';

                const card = document.createElement('div');
                card.className = 'leader-card';
                card.innerHTML = `
                    <div style="font-size:1.3rem; min-width:32px;">${escapeHTML(medal)}</div>
                    <div style="flex:1; margin-left:14px;">
                        <div style="font-weight:700; color:var(--secondary-color); font-size:0.95rem;">${escapeHTML(row.agent_name)}</div>
                        <div style="font-size:0.78rem; color:var(--text-light);">${escapeHTML(row.total_calls)} calls &nbsp;|&nbsp; ${escapeHTML(row.sales_closed)} sales</div>
                    </div>
                    <div style="font-size:1.6rem; font-weight:900; color:${scoreColor};">${escapeHTML(row.avg_score)}</div>
                `;
                leadContainer.appendChild(card);
            });
        }

        // 4. Load Charts
        const chartsData = await apiFetch(`/api/dashboard/charts?period=${period}`);
        renderDashboardCharts(chartsData);

    } catch (err) {
        showToast('Dashboard loading failed: ' + err.message, 'error');
    }
}

function getChartThemeColors() {
    const isDark = document.body.classList.contains('dark-mode');
    return {
        text: isDark ? '#94a3b8' : '#546e7a',
        grid: isDark ? '#1e293b' : '#e2e8f0'
    };
}

function renderDashboardCharts(data) {
    // Destroy existing chart instances to prevent canvas re-use crashes
    if (state.dashboardCharts.pie) state.dashboardCharts.pie.destroy();
    if (state.dashboardCharts.bar) state.dashboardCharts.bar.destroy();
    if (state.dashboardCharts.trend) state.dashboardCharts.trend.destroy();

    const colors = getChartThemeColors();

    // ── Status Pie Chart ──
    const ctxPie = document.getElementById('chart-status-pie').getContext('2d');
    const pieLabels = data.pie.map(d => d.name);
    const pieValues = data.pie.map(d => d.value);

    state.dashboardCharts.pie = new Chart(ctxPie, {
        type: 'doughnut',
        data: {
            labels: pieLabels,
            datasets: [{
                data: pieValues,
                backgroundColor: ['#28a745', '#dc3545', '#f59e0b', '#6366f1', '#a855f7'],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        boxWidth: 12,
                        color: colors.text,
                        font: { family: 'Outfit', size: 11 }
                    }
                }
            }
        }
    });

    // ── Agent Bar Chart ──
    const ctxBar = document.getElementById('chart-agent-bar').getContext('2d');
    const barLabels = data.bar.map(d => d.agent);
    const barValues = data.bar.map(d => d.score);

    state.dashboardCharts.bar = new Chart(ctxBar, {
        type: 'bar',
        data: {
            labels: barLabels,
            datasets: [{
                label: 'Pass Rate (%)',
                data: barValues,
                backgroundColor: 'rgba(237, 66, 36, 0.75)',
                borderColor: 'var(--primary-color)',
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: { color: colors.grid },
                    ticks: { color: colors.text, font: { family: 'Outfit' } }
                },
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: colors.grid },
                    ticks: { color: colors.text, font: { family: 'Outfit' } }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });

    // ── Score Trend Line Chart ──
    const ctxTrend = document.getElementById('chart-trend-line').getContext('2d');
    const trendLabels = data.trend.map(d => d.date);
    const trendValues = data.trend.map(d => d.score);

    state.dashboardCharts.trend = new Chart(ctxTrend, {
        type: 'line',
        data: {
            labels: trendLabels,
            datasets: [{
                label: 'Daily Pass Rate (%)',
                data: trendValues,
                fill: false,
                borderColor: 'var(--primary-color)',
                tension: 0.15,
                borderWidth: 2,
                pointBackgroundColor: 'var(--primary-color)',
                pointRadius: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: { color: colors.grid },
                    ticks: { color: colors.text, font: { family: 'Outfit' } }
                },
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: colors.grid },
                    ticks: { color: colors.text, font: { family: 'Outfit' } }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

// ── VIEW: MANAGE HISTORY ──
let cachedHistoryRecords = [];

async function loadHistoryManage() {
    const search = document.getElementById('history-search').value.toLowerCase();
    const select = document.getElementById('history-select');
    const tableBody = document.querySelector('#history-data-table tbody');

    try {
        const data = await apiFetch('/api/history/list');
        cachedHistoryRecords = data;

        // Populate dropdown list
        select.innerHTML = '<option value="">-- Choose Call Record --</option>';
        tableBody.innerHTML = '';

        const filtered = data.filter(row =>
            row.agent_name.toLowerCase().includes(search) ||
            row.call_id.toLowerCase().includes(search)
        );

        if (filtered.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center">No history matching search query.</td></tr>';
            return;
        }

        filtered.forEach(row => {
            // Dropdown
            const opt = document.createElement('option');
            opt.value = row.call_id;
            opt.textContent = `${row.call_id} - ${row.agent_name} (${(row.status || '').toUpperCase()})`;
            select.appendChild(opt);

            // Table
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><b>${escapeHTML(row.call_id)}</b></td>
                <td>${escapeHTML(row.agent_name)}</td>
                <td>${escapeHTML(row.customer_phone || row.patient_phone || 'N/A')}</td>
                <td>${escapeHTML(row.campaign || 'N/A')}</td>
                <td>${escapeHTML(row.call_type || 'N/A')}</td>
                <td>${escapeHTML(row.status)}</td>
            `;
            tableBody.appendChild(tr);
        });

        // Hide Edit Form by default
        document.getElementById('history-edit-box').style.display = 'none';

    } catch (err) {
        showToast('Failed to load audit history: ' + err.message, 'error');
    }
}

function handleHistorySelect(e) {
    const callId = e.target.value;
    const editBox = document.getElementById('history-edit-box');

    if (!callId) {
        editBox.style.display = 'none';
        return;
    }

    const row = cachedHistoryRecords.find(r => r.call_id === callId);
    if (!row) return;

    editBox.style.display = 'block';
    document.getElementById('edit-call-display-id').textContent = callId;
    document.getElementById('edit-history-agent').value = row.agent_name;
    document.getElementById('edit-history-score').value = row.score;
    document.getElementById('edit-history-status').value = row.status;

    // Show/hide admin confirm delete checkbox
    const adminDeleteSection = editBox.querySelector('.admin-only');
    if (state.role === 'admin') {
        adminDeleteSection.style.display = 'block';
        document.getElementById('confirm-history-delete').checked = false;
    } else {
        adminDeleteSection.style.display = 'none';
    }
}

async function handleHistoryEditSubmit(e) {
    e.preventDefault();
    const callId = document.getElementById('edit-call-display-id').textContent;
    const agent = document.getElementById('edit-history-agent').value.trim();
    const statusVal = document.getElementById('edit-history-status').value;
    const score = (statusVal.toLowerCase().includes('pass')) ? 100 : 0;

    try {
        await apiFetch(`/api/history/${callId}`, {
            method: 'PUT',
            body: JSON.stringify({
                agent_name: agent,
                score: score,
                status: statusVal
            })
        });

        showToast(`Record ${callId} updated successfully.`, 'success');
        loadHistoryManage();
    } catch (err) {
        showToast('Update failed: ' + err.message, 'error');
    }
}

async function handleHistoryDeleteClick() {
    const callId = document.getElementById('edit-call-display-id').textContent;
    const isConfirmed = document.getElementById('confirm-history-delete').checked;

    if (!isConfirmed) {
        showToast('Please check the confirmation box before deleting.', 'warning');
        return;
    }

    try {
        await apiFetch(`/api/history/${callId}`, {
            method: 'DELETE'
        });

        showToast(`Record ${callId} deleted successfully.`, 'success');
        loadHistoryManage();
    } catch (err) {
        showToast('Delete failed: ' + err.message, 'error');
    }
}

function handleDownloadCSV() {
    if (cachedHistoryRecords.length === 0) return;

    // Manual CSV generation
    const headers = ['call_id', 'agent_name', 'customer_phone', 'call_date', 'campaign', 'call_type', 'fcr', 'customer_feedback', 'score', 'status'];
    const rows = cachedHistoryRecords.map(row =>
        headers.map(header => `"${(row[header] || '').toString().replace(/"/g, '""')}"`).join(',')
    );

    const csvContent = "data:text/csv;charset=utf-8,"
        + [headers.join(','), ...rows].join('\n');

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "audit_history_export.csv");
    document.body.appendChild(link);
    link.click();
    link.remove();
}

// ── VIEW: SETTINGS & PROFILE ──
async function loadSettings() {
    // Trigger Admin tab configs
    const adminTabs = document.querySelectorAll('.settings-tab-btn.admin-only');
    if (state.role === 'admin') {
        adminTabs.forEach(el => el.style.display = 'block');
    } else {
        adminTabs.forEach(el => el.style.display = 'none');
    }

    // Default password tab
    switchSettingsTab('tab-password');
}

function switchSettingsTab(tabId) {
    document.querySelectorAll('.settings-tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.getAttribute('data-tab') === tabId) btn.classList.add('active');
    });

    document.querySelectorAll('.settings-tab-content').forEach(content => {
        content.classList.remove('active');
    });

    const activeContent = document.getElementById(tabId);
    if (activeContent) activeContent.classList.add('active');

    // Load tab-specific logic
    if (tabId === 'tab-users') loadSettingsUsers();
    else if (tabId === 'tab-prompt') loadSettingsPrompt();
}

async function handlePasswordSubmit(e) {
    e.preventDefault();
    const curr = document.getElementById('password-curr').value;
    const newPass = document.getElementById('password-new').value;
    const confPass = document.getElementById('password-conf').value;

    if (newPass !== confPass) {
        showToast('New passwords do not match.', 'error');
        return;
    }
    if (newPass.length < 6) {
        showToast('Password must be at least 6 characters.', 'warning');
        return;
    }

    try {
        await apiFetch('/api/settings/password', {
            method: 'POST',
            body: JSON.stringify({
                current_password: curr,
                new_password: newPass
            })
        });
        showToast('Password updated successfully!', 'success');
        document.getElementById('settings-password-form').reset();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// User Management Sub-Tab
async function loadSettingsUsers() {
    const listEl = document.getElementById('settings-users-list');
    const select = document.getElementById('settings-edit-user-select');
    const editForm = document.getElementById('settings-edit-user-form');

    try {
        const users = await apiFetch('/api/settings/users');
        listEl.innerHTML = '';
        select.innerHTML = '<option value="">-- Choose User --</option>';
        editForm.style.display = 'none';

        users.forEach(u => {
            // Dropdown selection
            const opt = document.createElement('option');
            opt.value = u.username;
            opt.textContent = `${u.username} (${u.role.toUpperCase()})`;
            select.appendChild(opt);

            // Card list item
            const roleColorMap = { admin: 'var(--primary-color)', supervisor: '#6366f1', user: 'var(--text-light)' };
            const roleColor = roleColorMap[u.role] || 'var(--text-light)';
            const icon = u.role === 'admin' ? '🛡️' : (u.role === 'supervisor' ? '👔' : '👤');

            const card = document.createElement('div');
            card.className = 'report-section';
            card.style.display = 'flex';
            card.style.justifyContent = 'space-between';
            card.style.alignItems = 'center';
            card.style.padding = '12px 18px';
            card.style.marginBottom = '8px';
            card.innerHTML = `
                <div style="display:flex; align-items:center; gap:12px;">
                    <div style="width:36px; height:36px; border-radius:50%; background:${escapeHTML(roleColor)}15; display:flex; align-items:center; justify-content:center; font-size:1.1rem;">${icon}</div>
                    <div>
                        <div style="font-weight:700; color:var(--secondary-color); font-size:0.95rem;">${escapeHTML(u.username)}</div>
                        <div style="font-size:0.72rem; padding:2px 8px; border-radius:10px; background:${escapeHTML(roleColor)}15; color:${escapeHTML(roleColor)}; font-weight:600; display:inline-block; margin-top:2px;">${escapeHTML(u.role.toUpperCase())}</div>
                    </div>
                </div>
                <div style="font-size:0.78rem; color:var(--text-light);">ID #${escapeHTML(u.id)}</div>
            `;
            listEl.appendChild(card);
        });
    } catch (err) {
        showToast('Failed to load accounts: ' + err.message, 'error');
    }
}

async function handleAddUserSubmit(e) {
    e.preventDefault();
    const user = document.getElementById('new-user-username').value.trim();
    const pass = document.getElementById('new-user-password').value;
    const role = document.getElementById('new-user-role').value;

    try {
        await apiFetch('/api/settings/users', {
            method: 'POST',
            body: JSON.stringify({ username: user, password: pass, role: role })
        });
        showToast(`Account ${user} created successfully!`, 'success');
        document.getElementById('settings-add-user-form').reset();
        loadSettingsUsers();
    } catch (err) {
        showToast('Failed to create account: ' + err.message, 'error');
    }
}

async function handleSettingsEditUserSelect(e) {
    const username = e.target.value;
    const form = document.getElementById('settings-edit-user-form');
    if (!username) {
        form.style.display = 'none';
        return;
    }

    form.style.display = 'block';

    // Clear inputs
    document.getElementById('edit-user-username').value = '';
    document.getElementById('edit-user-password').value = '';

    // Retrieve selected user role config
    const users = await apiFetch('/api/settings/users');
    const selected = users.find(u => u.username === username);
    if (selected) {
        document.getElementById('edit-user-role').value = selected.role;
    }
}

async function handleEditUserSubmit(e) {
    e.preventDefault();
    const targetUser = document.getElementById('settings-edit-user-select').value;
    const newUser = document.getElementById('edit-user-username').value.trim();
    const newPass = document.getElementById('edit-user-password').value;
    const role = document.getElementById('edit-user-role').value;

    try {
        await apiFetch(`/api/settings/users/${targetUser}`, {
            method: 'PUT',
            body: JSON.stringify({
                username: newUser || undefined,
                password: newPass || undefined,
                role: role
            })
        });

        showToast('User credentials updated successfully!', 'success');
        loadSettingsUsers();
    } catch (err) {
        showToast('Edit failed: ' + err.message, 'error');
    }
}

async function handleUserDeleteClick() {
    const targetUser = document.getElementById('settings-edit-user-select').value;
    if (targetUser === state.username) {
        showToast('You cannot delete your own account.', 'error');
        return;
    }

    if (!confirm(`Are you sure you want to permanently delete user "${targetUser}"?`)) return;

    try {
        await apiFetch(`/api/settings/users/${targetUser}`, {
            method: 'DELETE'
        });

        showToast(`User ${targetUser} deleted successfully.`, 'success');
        loadSettingsUsers();
    } catch (err) {
        showToast('Delete failed: ' + err.message, 'error');
    }
}

// AI Scorecard Config Sub-Tab
let cachedPromptDefaults = {};

async function loadSettingsPrompt() {
    try {
        const data = await apiFetch('/api/settings/prompt');
        cachedPromptDefaults = data.defaults;

        document.getElementById('settings-prompt-text').value = data.prompt_text;

        // Render category weight fields
        const container = document.getElementById('settings-weights-container');
        container.innerHTML = '';

        const categories = Object.keys(data.defaults);
        categories.forEach(cat => {
            const display = cat.replace(/_/g, ' ');
            const currentVal = data.section_max[cat] || data.defaults[cat];

            const field = document.createElement('div');
            field.className = 'form-group';
            field.innerHTML = `
                <label for="weight-input-${escapeHTML(cat)}">${escapeHTML(display)} (Max)</label>
                <input type="number" id="weight-input-${escapeHTML(cat)}" min="1" max="100" class="form-control weight-input-field" data-cat="${escapeHTML(cat)}" value="${escapeHTML(currentVal)}" required>
            `;
            container.appendChild(field);
        });

    } catch (err) {
        showToast('Failed to load Prompt settings: ' + err.message, 'error');
    }
}

async function handleWeightsFormSubmit(e) {
    e.preventDefault();
    const promptText = document.getElementById('settings-prompt-text').value;

    // Gather weight inputs
    const weights = {};
    document.querySelectorAll('.weight-input-field').forEach(input => {
        const cat = input.getAttribute('data-cat');
        weights[cat] = parseInt(input.value);
    });

    try {
        await apiFetch('/api/settings/prompt', {
            method: 'POST',
            body: JSON.stringify({
                prompt_text: promptText,
                section_max: weights
            })
        });

        showToast('AI Scorecard config saved successfully!', 'success');
        loadSettingsPrompt();
    } catch (err) {
        showToast('Failed to save config: ' + err.message, 'error');
    }
}

async function handlePromptResetClick() {
    if (!confirm('Are you sure you want to reset the prompt and scorecard weights to system defaults?')) return;
    try {
        await apiFetch('/api/settings/prompt/reset', { method: 'POST' });
        showToast('AI config reset to default.', 'success');
        loadSettingsPrompt();
    } catch (err) {
        showToast('Reset failed: ' + err.message, 'error');
    }
}

// ── VIEW: ACTIVITY LOGS ──
async function loadLogs() {
    const tableBody = document.querySelector('#activity-logs-table tbody');
    try {
        const logs = await apiFetch('/api/logs');
        tableBody.innerHTML = '';

        if (logs.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="text-center">No activity logs recorded yet.</td></tr>';
            return;
        }

        logs.forEach(log => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>#${escapeHTML(log.id)}</td>
                <td>${escapeHTML(log.timestamp)}</td>
                <td><b>${escapeHTML(log.username)}</b></td>
                <td>${escapeHTML(log.action)}</td>
                <td><code>${escapeHTML(log.ip_address)}</code></td>
            `;
            tableBody.appendChild(tr);
        });
    } catch (err) {
        showToast('Failed to load logs: ' + err.message, 'error');
    }
}

// ── VIEW: USAGE & COST TRACKER ──
let activeUsagePeriod = 'Today';
let cachedUsageRecords = [];

function switchUsagePeriod(period) {
    activeUsagePeriod = period;
    document.querySelectorAll('#usage-period-headers button').forEach(btn => {
        btn.classList.remove('active');
        if (btn.getAttribute('data-period') === period) btn.classList.add('active');
    });

    loadUsageTracker();
}

async function loadUsageTracker() {
    const searchVal = document.getElementById('usage-log-search').value.toLowerCase();
    const tableBody = document.querySelector('#usage-logs-table tbody');

    try {
        const records = await apiFetch('/api/usage');
        cachedUsageRecords = records;

        // Perform date calculations
        const now = new Date();
        let limitDate = null;
        if (activeUsagePeriod === 'Today') {
            limitDate = new Date();
            limitDate.setHours(0,0,0,0);
        } else if (activeUsagePeriod === 'This Week') {
            limitDate = new Date();
            limitDate.setDate(now.getDate() - 7);
        } else if (activeUsagePeriod === 'This Month') {
            limitDate = new Date();
            limitDate.setDate(now.getDate() - 30);
        }

        // Filter by Date Period
        let filtered = records;
        if (limitDate) {
            filtered = records.filter(r => new Date(r.created_at) >= limitDate);
        }

        // Apply KPI sums
        const costSum = filtered.reduce((acc, r) => acc + (r.cost || 0), 0);
        const inputSum = filtered.reduce((acc, r) => acc + (r.input_tokens || 0), 0);
        const outputSum = filtered.reduce((acc, r) => acc + (r.output_tokens || 0), 0);

        document.getElementById('usage-total-cost').textContent = `$${costSum.toFixed(4)}`;
        document.getElementById('usage-input-tokens').textContent = inputSum.toLocaleString();
        document.getElementById('usage-output-tokens').textContent = outputSum.toLocaleString();
        document.getElementById('usage-total-analyses').textContent = filtered.length;

        // Apply table search filters
        const searchFiltered = filtered.filter(r => r.filename.toLowerCase().includes(searchVal));
        tableBody.innerHTML = '';

        if (searchFiltered.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center">No usage records matched.</td></tr>';
        } else {
            searchFiltered.forEach(row => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>#${escapeHTML(row.id)}</td>
                    <td>${escapeHTML(row.filename)}</td>
                    <td>${escapeHTML(row.created_at)}</td>
                    <td>${escapeHTML(row.input_tokens.toLocaleString())}</td>
                    <td>${escapeHTML(row.output_tokens.toLocaleString())}</td>
                    <td><b>$${escapeHTML(row.cost.toFixed(4))}</b></td>
                `;
                tableBody.appendChild(tr);
            });
        }

        // Render Usage Daily Cost Chart
        renderUsageCostChart(filtered);

    } catch (err) {
        showToast('Usage load failed: ' + err.message, 'error');
    }
}

function renderUsageCostChart(filteredRecords) {
    if (state.usageChart) state.usageChart.destroy();

    // Group costs by date
    const dailyCosts = {};
    filteredRecords.forEach(r => {
        const dateStr = r.created_at.split(' ')[0]; // YYYY-MM-DD
        dailyCosts[dateStr] = (dailyCosts[dateStr] || 0) + (r.cost || 0);
    });

    const dates = Object.keys(dailyCosts).sort();
    const costs = dates.map(d => parseFloat(dailyCosts[d].toFixed(4)));

    const colors = getChartThemeColors();

    const ctx = document.getElementById('chart-daily-costs').getContext('2d');
    state.usageChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: dates,
            datasets: [{
                label: 'Cost (USD)',
                data: costs,
                backgroundColor: 'rgba(237, 66, 36, 0.75)',
                borderColor: 'var(--primary-color)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    grid: { color: colors.grid },
                    ticks: { color: colors.text, font: { family: 'Outfit' } }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: colors.grid },
                    ticks: { color: colors.text, font: { family: 'Outfit' } }
                }
            }
        }
    });
}

// ── DOM ACTIONS BINDINGS ──
document.addEventListener('DOMContentLoaded', () => {
    // 1. Auth bindings
    document.getElementById('login-form').addEventListener('submit', handleLogin);
    document.getElementById('logout-btn').addEventListener('click', logout);

    // 2. Sidebar router bindings
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const view = e.currentTarget.getAttribute('data-view');
            showView(view);
        });
    });

    // 3. Analysis view bindings
    document.getElementById('queue-auto-refresh').addEventListener('change', handleAutoRefreshChange);
    document.getElementById('refresh-queue-btn').addEventListener('click', loadQueue);
    setupDropZone();

    // 4. Review view bindings
    document.getElementById('show-verified-checkbox').addEventListener('change', loadReviewList);
    document.getElementById('review-search-filename').addEventListener('input', loadReviewList);
    document.getElementById('review-task-select').addEventListener('change', handleReviewTaskSelect);
    document.getElementById('audit-verification-form').addEventListener('submit', handleAuditFormSubmit);
    document.getElementById('download-pdf-btn').addEventListener('click', handlePDFDownload);

    // 5. Dashboard view bindings
    document.getElementById('dashboard-period').addEventListener('change', loadDashboard);

    // 6. Manage History bindings
    document.getElementById('history-search').addEventListener('input', loadHistoryManage);
    document.getElementById('history-select').addEventListener('change', handleHistorySelect);
    document.getElementById('history-edit-form').addEventListener('submit', handleHistoryEditSubmit);
    document.getElementById('delete-history-record-btn').addEventListener('click', handleHistoryDeleteClick);
    document.getElementById('download-history-csv-btn').addEventListener('click', handleDownloadCSV);

    // 7. Settings view bindings
    document.getElementById('settings-tab-headers').addEventListener('click', (e) => {
        if (e.target.classList.contains('settings-tab-btn')) {
            const tabId = e.target.getAttribute('data-tab');
            switchSettingsTab(tabId);
        }
    });
    document.getElementById('settings-password-form').addEventListener('submit', handlePasswordSubmit);
    document.getElementById('settings-add-user-form').addEventListener('submit', handleAddUserSubmit);
    document.getElementById('settings-edit-user-select').addEventListener('change', handleSettingsEditUserSelect);
    document.getElementById('settings-edit-user-form').addEventListener('submit', handleEditUserSubmit);
    document.getElementById('settings-delete-user-btn').addEventListener('click', handleUserDeleteClick);
    document.getElementById('settings-weights-form').addEventListener('submit', handleWeightsFormSubmit);
    document.getElementById('settings-reset-prompt-btn').addEventListener('click', handlePromptResetClick);

    // 8. Cost Tracker bindings
    document.getElementById('usage-period-headers').addEventListener('click', (e) => {
        if (e.target.classList.contains('settings-tab-btn')) {
            const period = e.target.getAttribute('data-period');
            switchUsagePeriod(period);
        }
    });
    document.getElementById('usage-log-search').addEventListener('input', loadUsageTracker);

    // 9. Theme toggle bindings
    const themeToggleBtn = document.getElementById('theme-toggle');
    if (themeToggleBtn) {
        const isDark = document.body.classList.contains('dark-mode');
        updateThemeToggleButton(isDark);

        themeToggleBtn.addEventListener('click', () => {
            const currentDark = document.body.classList.toggle('dark-mode');
            localStorage.setItem('theme', currentDark ? 'dark' : 'light');
            updateThemeToggleButton(currentDark);

            // Redraw charts to update their colors
            if (state.currentView === 'dashboard') {
                loadDashboard();
            } else if (state.currentView === 'usage') {
                loadUsageTracker();
            }
        });
    }

    function updateThemeToggleButton(isDark) {
        const icon = themeToggleBtn.querySelector('i');
        const label = themeToggleBtn.querySelector('span');
        if (isDark) {
            icon.className = 'fa-solid fa-sun';
            label.textContent = 'Light Mode';
        } else {
            icon.className = 'fa-solid fa-moon';
            label.textContent = 'Dark Mode';
        }
    }

    // 10. Startup check
    initApp();
});
