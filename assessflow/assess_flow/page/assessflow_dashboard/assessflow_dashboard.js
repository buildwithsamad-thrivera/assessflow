frappe.pages['assessflow-dashboard'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'AssessFlow | Command Center',
        single_column: true
    });

    if (!window.Chart) {
        let script = document.createElement('script');
        script.src = "https://cdn.jsdelivr.net/npm/chart.js";
        document.head.appendChild(script);
    }

    let style = document.createElement('style');
    style.innerHTML = `
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
        .af-dash { padding: 30px; background: #f7f9fc; min-height: 100vh; font-family: 'Inter', sans-serif; color: #1e293b; }
        .af-header { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 24px; }
        .af-header h1 { margin: 0; font-size: 26px; font-weight: 800; letter-spacing: -0.5px; }
        
        /* Tabs */
        .af-tabs { display: flex; gap: 24px; border-bottom: 2px solid #e2e8f0; margin-bottom: 24px; }
        .af-tab { padding: 12px 4px; font-weight: 600; font-size: 15px; color: #64748b; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -2px; transition: 0.2s; }
        .af-tab:hover { color: #1e293b; }
        .af-tab.active { color: #2563eb; border-bottom-color: #2563eb; }
        
        .af-tab-content { display: none; }
        .af-tab-content.active { display: block; animation: fadeIn 0.3s ease; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }

        /* Grid & Cards */
        .af-grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 20px; margin-bottom: 20px; }
        .af-card { background: #fff; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 4px 20px -2px rgba(0,0,0,0.03); }
        .af-card-header { padding: 20px 24px; border-bottom: 1px solid #f1f5f9; font-weight: 700; font-size: 15px; display: flex; justify-content: space-between; align-items: center; }
        .af-card-body { padding: 24px; }
        
        /* KPIs */
        .af-kpi { grid-column: span 3; display: flex; align-items: center; justify-content: space-between; padding: 24px; background: #fff; border-radius: 16px; border: 1px solid #e2e8f0; }
        @media (max-width: 1200px) { .af-kpi { grid-column: span 6; } }
        .af-kpi-info h3 { margin: 0; font-size: 13px; font-weight: 700; color: #64748b; text-transform: uppercase; }
        .af-kpi-info .val { font-size: 32px; font-weight: 800; margin-top: 8px; line-height: 1; }
        
        /* Tables */
        .af-table { width: 100%; border-collapse: collapse; }
        .af-table th { text-align: left; padding: 12px 16px; font-size: 12px; font-weight: 700; color: #64748b; text-transform: uppercase; border-bottom: 1px solid #e2e8f0; background: #f8fafc; }
        .af-table td { padding: 16px; border-bottom: 1px solid #f1f5f9; font-size: 14px; vertical-align: middle; }
        .af-table tr:hover { background: #f8fafc; }
        
        .af-btn { padding: 8px 16px; border-radius: 6px; font-weight: 600; font-size: 13px; cursor: pointer; transition: 0.2s; border: none; display: inline-flex; align-items: center; gap: 6px; }
        .af-btn-primary { background: #2563eb; color: #fff; }
        .af-btn-primary:hover { background: #1d4ed8; }
        .af-btn-danger { background: #fee2e2; color: #dc2626; }
        .af-btn-danger:hover { background: #fecaca; }
        
        .af-timer { font-family: 'JetBrains Mono', monospace; background: #dcfce7; color: #166534; padding: 4px 8px; border-radius: 6px; font-weight: 700; font-size: 13px; }
        .af-timer.warning { background: #fef3c7; color: #92400e; }
        .af-timer.danger { background: #fee2e2; color: #dc2626; animation: pulse 1s infinite; }
        @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }
    `;
    document.head.appendChild(style);

    let $app = $('<div class="af-dash"></div>').appendTo(page.body);
    let countdownInterval = null;

    function render(data) {
        let html = `
            <div class="af-header">
                <div>
                    <h1>Command Center</h1>
                    <p>System operational. Real-time monitoring active.</p>
                </div>
                <a href="/app/assessment/new" class="af-btn af-btn-primary" style="text-decoration:none;">+ New Assessment</a>
            </div>

            <div class="af-tabs">
                <div class="af-tab active" data-tab="overview">Overview</div>
                <div class="af-tab" data-tab="live">Live Monitor <span style="background:#ef4444;color:#fff;padding:2px 6px;border-radius:10px;font-size:11px;margin-left:6px;">${data.live.length}</span></div>
                <div class="af-tab" data-tab="candidates">All Candidates</div>
            </div>

            <!-- OVERVIEW TAB -->
            <div class="af-tab-content active" id="tab-overview">
                <div class="af-grid">
                    <div class="af-kpi"><div class="af-kpi-info"><h3>Assessments</h3><div class="val">${data.kpi.assessments}</div></div></div>
                    <div class="af-kpi"><div class="af-kpi-info"><h3>Candidates</h3><div class="val" style="color:#2563eb">${data.kpi.attempts}</div></div></div>
                    <div class="af-kpi"><div class="af-kpi-info"><h3>Pending Reviews</h3><div class="val" style="color:#ea580c">${data.kpi.pending}</div></div></div>
                    <div class="af-kpi"><div class="af-kpi-info"><h3>Avg. Score</h3><div class="val" style="color:#16a34a">${data.kpi.avg_score}%</div></div></div>
                </div>
                
                <div class="af-grid">
                    <div class="af-card" style="grid-column: span 8;">
                        <div class="af-card-header">Performance Trend (14 Days)</div>
                        <div class="af-card-body"><canvas id="chart-trend" height="100"></canvas></div>
                    </div>
                    <div class="af-card" style="grid-column: span 4;">
                        <div class="af-card-header">Security Feed</div>
                        <div class="af-card-body" style="max-height:300px;overflow-y:auto;" id="af-security-feed"></div>
                    </div>
                </div>
            </div>

            <!-- LIVE MONITOR TAB -->
            <div class="af-tab-content" id="tab-live">
                <div class="af-card">
                    <div class="af-card-header">Active Candidates</div>
                    <div class="af-card-body" style="padding:0;">
                        <table class="af-table">
                            <thead><tr><th>Candidate</th><th>Assessment</th><th>Time Left</th><th style="text-align:right;">Actions</th></tr></thead>
                            <tbody id="live-tbody"></tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- CANDIDATES TAB -->
            <div class="af-tab-content" id="tab-candidates">
                <div class="af-card">
                    <div class="af-card-header">All Candidates <input type="text" id="search-cand" class="form-control" placeholder="Search by name..." style="width:200px;display:inline-block;margin-left:20px;"></div>
                    <div class="af-card-body" style="padding:0;">
                        <table class="af-table">
                            <thead><tr><th>Candidate</th><th>Assessment</th><th>Status</th><th>Score</th><th style="text-align:right;">Action</th></tr></thead>
                            <tbody id="cand-tbody"></tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
        $app.html(html);

        // Tab Switching
        $('.af-tab').click(function() {
            $('.af-tab').removeClass('active');
            $('.af-tab-content').removeClass('active');
            $(this).addClass('active');
            $('#tab-' + $(this).data('tab')).addClass('active');
        });

        // Render Chart
        new Chart(document.getElementById('chart-trend'), {
            type: 'line',
            data: {
                labels: data.trend.labels,
                datasets: [
                    { label: 'Attempts', data: data.trend.attempts, borderColor: '#2563eb', backgroundColor: 'rgba(37,99,235,0.1)', fill: true, tension: 0.4, borderWidth: 2, yAxisID: 'y' },
                    { label: 'Avg Score (%)', data: data.trend.scores, borderColor: '#16a34a', borderDash: [5, 5], borderWidth: 2, tension: 0.4, yAxisID: 'y1' }
                ]
            },
            options: { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false }, scales: { y: { position: 'left', beginAtZero: true, ticks: {stepSize: 1} }, y1: { position: 'right', beginAtZero: true, max: 100, grid: {drawOnChartArea: false} } } }
        });

        // Security Feed
        let $sec = $('#af-security-feed');
        if (!data.events.length) $sec.html('<div style="text-align:center;color:#94a3b8;padding:20px;">No events.</div>');
        else {
            data.events.forEach(e => {
                $sec.append(`<div style="padding:12px;border-bottom:1px solid #f1f5f9;">
                    <div style="color:#dc2626;font-weight:600;font-size:13px;">⚠ ${e.event_type.replace('_',' ').toUpperCase()}</div>
                    <div style="font-size:12px;color:#64748b;margin-top:4px;">${e.attempt} • ${frappe.datetime.prettyDate(e.occurred_at)}</div>
                </div>`);
            });
        }

        // Live Monitor Table
        let $live = $('#live-tbody');
        if (!data.live.length) $live.html('<tr><td colspan="4" style="text-align:center;padding:40px;color:#94a3b8;">No active sessions.</td></tr>');
        else {
            data.live.forEach(a => {
                $live.append(`<tr>
                    <td><strong>${a.candidate || 'Unknown'}</strong></td>
                    <td>${a.assessment}</td>
                    <td><span class="af-timer" data-deadline="${a.deadline_ts}">--:--</span></td>
                    <td style="text-align:right;">
                        <button class="af-btn af-btn-danger btn-force-submit" data-name="${a.name}">Force Submit</button>
                    </td>
                </tr>`);
            });
            startCountdowns();
            
            $('.btn-force-submit').click(function() {
                let name = $(this).data('name');
                frappe.confirm('Are you sure you want to force submit this attempt?', () => {
                    frappe.call({ method: 'assessflow.api.admin.force_submit_attempt', args: { attempt_name: name }, callback: function(r) {
                        if(r.message.ok) { frappe.show_alert({message:'Attempt submitted.',indicator:'green'}); location.reload(); }
                        else { frappe.msgprint(r.message.error); }
                    }});
                });
            });
        }

        // All Candidates Table
        let $cand = $('#cand-tbody');
        if (!data.recent_attempts.length) $cand.html('<tr><td colspan="5" style="text-align:center;padding:40px;color:#94a3b8;">No candidates found.</td></tr>');
        else {
            data.recent_attempts.forEach(a => {
                let badgeColor = a.status === 'Evaluated' ? '#dcfce7' : (a.status === 'Under Review' ? '#fef3c7' : '#f1f5f9');
                let textColor = a.status === 'Evaluated' ? '#166534' : (a.status === 'Under Review' ? '#92400e' : '#475569');
                let score = a.percentage !== null ? a.percentage + '%' : '-';
                $cand.append(`<tr>
                    <td><strong>${a.candidate_name || 'Unknown'}</strong></td>
                    <td>${a.assessment}</td>
                    <td><span style="background:${badgeColor};color:${textColor};padding:4px 8px;border-radius:4px;font-weight:600;font-size:12px;">${a.status}</span></td>
                    <td><strong>${score}</strong></td>
                    <td style="text-align:right;"><button class="af-btn" style="background:#f1f5f9;" onclick="frappe.set_route('Form', 'Candidate Attempt', '${a.name}')">View</button></td>
                </tr>`);
            });
        }
        
        $('#search-cand').on('keyup', function() {
            let val = $(this).val().toLowerCase();
            $("#cand-tbody tr").filter(function() { $(this).toggle($(this).text().toLowerCase().indexOf(val) > -1) });
        });
    }

    function startCountdowns() {
        if (countdownInterval) clearInterval(countdownInterval);
        countdownInterval = setInterval(() => {
            $('.af-timer').each(function() {
                let diff = Math.floor((parseInt($(this).attr('data-deadline')) - Date.now()) / 1000);
                if (diff <= 0) { $(this).text('Expired').addClass('danger'); }
                else {
                    let h = Math.floor(diff / 3600), m = Math.floor((diff % 3600) / 60), s = diff % 60;
                    $(this).text(h > 0 ? `${h}h ${m}m` : `${m}m ${s}s`);
                    if(diff < 300) $(this).addClass('danger'); else if (diff < 600) $(this).addClass('warning');
                }
            });
        }, 1000);
    }

    frappe.call({
        method: 'assessflow.api.admin.get_dashboard_data',
        callback: function(r) { if (r.message) render(r.message); }
    });
};
