(function () {
  const API = "/api/method/assessflow.api.guest.";
  const TOKEN_KEY = "af_session_token";
  const state = { sections:[], questions:[], answers:{}, marked:{}, current:0, attemptId:null, deadline:null, timerId:null, saveQueue:new Map(), saveInFlight:false, codeMirrors:{}, meta:null, submitted:false };
  
  const $ = (id) => document.getElementById(id);
  const show = (id) => $(id).classList.remove("af-hidden");
  const hide = (id) => $(id).classList.add("af-hidden");

  // LocalStorage Recovery
  function getSaveQueue() {
    if (!state.attemptId) return new Map();
    try { return new Map(JSON.parse(localStorage.getItem(`af_queue_${state.attemptId}`) || "[]")); } catch(e) { return new Map(); }
  }
  function updateLocalStorage() {
    if (!state.attemptId) return;
    if (state.saveQueue.size === 0) localStorage.removeItem(`af_queue_${state.attemptId}`);
    else localStorage.setItem(`af_queue_${state.attemptId}`, JSON.stringify([...state.saveQueue]));
  }

  // Networking
  async function call(method, body) {
    body = Object.assign({}, body || {});
    const tok = sessionStorage.getItem(TOKEN_KEY); if (tok) body.session_token = tok;
    const headers = {"Content-Type":"application/json"}; if (window.CSRF_TOKEN) headers["X-Frappe-CSRF-Token"] = window.CSRF_TOKEN;
    const r = await fetch(API + method, {method:"POST", credentials:"include", headers, body:JSON.stringify(body)});
    const txt = await r.text(); let data = null; try { data = JSON.parse(txt); } catch(_) {}
    if (!r.ok) throw new Error(`HTTP ${r.status}: ${txt.slice(0,300)}`); return data;
  }
  
  function logEvent(type, meta) { if (state.attemptId && !state.submitted) call("log_event", {event_type:type, metadata:meta||""}).catch(()=>{}); }
  function showWarning(title, msg) { 
    if (state.submitted) return; 
    $("af-warning-title").textContent = title; 
    $("af-warning-msg").textContent = msg; 
    show("af-warning-modal"); 
    logEvent("warning_shown", `${title}: ${msg}`); 
  }

  // Anti-Cheat
  function enforceSecurity() {
    document.addEventListener("contextmenu", (e) => { if(state.submitted)return; e.preventDefault(); logEvent("right_click"); showWarning("Right Click Disabled", "Not allowed."); });
    ['copy', 'paste', 'cut'].forEach(evt => { document.addEventListener(evt, (e) => { if(state.submitted)return; e.preventDefault(); logEvent(evt + "_attempt"); showWarning("Action Blocked", "Please type your answers."); }); });
    document.addEventListener("keydown", (e) => { if(state.submitted)return; if (e.key === "F12" || (e.ctrlKey && e.shiftKey && ["I","J","C"].includes(e.key)) || (e.ctrlKey && ["u","s","p"].includes(e.key))) { e.preventDefault(); logEvent("shortcut_blocked", e.key); } });
    document.addEventListener("visibilitychange", () => { if(state.submitted)return; if (document.hidden) logEvent("tab_switch"); else { logEvent("tab_return"); showWarning("Tab Switch Detected", "Recorded and flagged."); } });
    window.addEventListener("blur", () => { if(state.submitted)return; logEvent("window_blur"); });
    document.addEventListener("fullscreenchange", () => { if(state.submitted)return; if (!document.fullscreenElement && state.attemptId) { logEvent("fullscreen_exit"); showWarning("Fullscreen Exited", "Recorded."); } });
  }

  // Rendering Helpers
  function renderLanding(resp) {
    const meta = resp.assessment;
    $("af-title").textContent = meta.title || "Assessment"; 
    $("af-description").innerHTML = meta.description || "";
    $("af-duration").textContent = meta.duration_minutes; 
    $("af-qcount").textContent = meta.question_count; 
    $("af-candidate").textContent = resp.candidate_name || "";
    state.meta = meta;
    
    const instr = $("af-instructions"); 
    if (meta.instructions && meta.instructions.replace(/<[^>]*>/g,"").trim() !== "") { 
        instr.innerHTML = meta.instructions; 
        instr.classList.remove("af-hidden"); 
    }
    
    const accept = $("af-accept"), start = $("af-start"); 
    accept.addEventListener("change", () => { start.disabled = !accept.checked; });
    hide("af-loading"); show("af-landing");
  }

  async function onStart() {
    try { const el = document.documentElement; if (el.requestFullscreen) await el.requestFullscreen(); } catch(e) {}
    hide("af-error"); $("af-start").disabled = true; $("af-start").textContent = "Starting…";
    
    try {
      const r = await call("start_assessment", {token: window.ASSESSFLOW_TOKEN});
      if (!r || !r.message || !r.message.ok) return showError(r?.message?.error || "Unable to start.");
      
      sessionStorage.setItem(TOKEN_KEY, r.message.session_token); 
      state.attemptId = r.message.attempt_id; 
      state.deadline = new Date(r.message.deadline);
      
      const s = await call("get_attempt_state");
      if (!s || !s.message || !s.message.ok) return showError(s?.message?.error || "Load failed.");
      
      state.sections = s.message.sections || []; 
      state.answers = {}; 
      state.marked = {}; 
      state.questions = [];
      
      state.sections.forEach(sec => {
          if (sec.questions && sec.questions.length > 0) {
              sec.questions.forEach(q => {
                  q._section_name = sec.name; 
                  q._section_instructions = sec.instructions;
                  q._is_first_in_section = (sec.questions.indexOf(q) === 0);
                  state.questions.push(q);
              });
          }
      });
      
      if (state.questions.length === 0) return showError("This assessment has no questions.");
      
      Object.entries(s.message.answers || {}).forEach(([q, raw]) => { try { state.answers[q] = JSON.parse(raw); } catch(_) {} });
      Object.entries(s.message.marked_for_review || {}).forEach(([q, v]) => { state.marked[q] = !!v; });
      
      state.saveQueue = getSaveQueue();
      
      hide("af-landing"); 
      show("af-attempt"); 
      $("af-assess-title").textContent = s.message.assessment.title; 
      $("af-progress-total").textContent = state.questions.length;
      
      enforceSecurity(); 
      renderNav(); 
      renderCurrent(); 
      startTimer(); 
      wireNav();
      
      if (state.saveQueue.size > 0) drainSaves();
    } catch (e) { showError(e.message); }
  }

  function startTimer() {
    if (state.timerId) clearInterval(state.timerId);
    const tick = () => {
      const left = Math.max(0, Math.floor((state.deadline - Date.now()) / 1000));
      const h = String(Math.floor(left/3600)).padStart(2,"0"), m = String(Math.floor((left%3600)/60)).padStart(2,"0"), s = String(left%60).padStart(2,"0");
      $("af-timer-text").textContent = `${h}:${m}:${s}`; 
      const t = $("af-timer"); 
      t.classList.toggle("af-timer-warn", left <= 300 && left > 60); 
      t.classList.toggle("af-timer-danger", left <= 60);
      if (left === 0) { clearInterval(state.timerId); doSubmit(true); }
    }; 
    tick(); state.timerId = setInterval(tick, 1000);
  }

  function renderNav() {
    const nav = $("af-nav"); nav.innerHTML = ""; let globalIdx = 0;
    (state.sections || []).forEach(sec => {
        const secWrap = document.createElement("div"); secWrap.className = "af-nav-section";
        const secTitle = document.createElement("div"); secTitle.className = "af-nav-section-title"; secTitle.textContent = sec.name; secWrap.appendChild(secTitle);
        const btnGrid = document.createElement("div"); btnGrid.className = "af-nav-grid";
        (sec.questions || []).forEach(q => {
            const i = globalIdx++;
            const btn = document.createElement("button"); btn.textContent = i + 1; btn.className = "af-nav-btn";
            if (i === state.current) btn.classList.add("af-active"); 
            if (state.marked[q.name]) btn.classList.add("af-marked"); 
            else if (state.answers[q.name] != null) btn.classList.add("af-answered");
            btn.onclick = () => { goTo(i); if(window.innerWidth <= 1024) $("af-sidebar").classList.remove("af-open"); }; 
            btnGrid.appendChild(btn);
        });
        secWrap.appendChild(btnGrid); nav.appendChild(secWrap);
    });
    const answered = (state.questions || []).filter(q => state.answers[q.name] != null).length;
    $("af-progress-current").textContent = answered; 
    $("af-progress-fill").style.width = (answered / Math.max(1, (state.questions || []).length)) * 100 + "%";
  }
  
  function goTo(i) { 
      if (i < 0 || i >= state.questions.length) return; 
      state.current = i; 
      renderCurrent(); 
      renderNav(); 
  }
  
  function wireNav() {
    $("af-prev").onclick = () => goTo(state.current - 1); 
    $("af-next").onclick = () => goTo(state.current + 1); 
    $("af-mark-btn").onclick = () => toggleMark();
    $("af-open-submit").onclick = openSubmitModal; 
    $("af-cancel-submit").onclick = () => hide("af-submit-modal"); 
    $("af-confirm-submit").onclick = () => { hide("af-submit-modal"); doSubmit(false); };
    $("af-warning-close").onclick = () => hide("af-warning-modal");
    $("af-mobile-toggle").onclick = () => $("af-sidebar").classList.add("af-open");
    $("af-close-sidebar").onclick = () => $("af-sidebar").classList.remove("af-open");
    
    document.addEventListener("keydown", (e) => { 
        if (["INPUT","TEXTAREA"].includes(e.target.tagName) || e.target.isContentEditable) return; 
        if (e.key === "ArrowLeft") goTo(state.current - 1); 
        if (e.key === "ArrowRight") goTo(state.current + 1); 
        if (e.key.toLowerCase() === "m") toggleMark(); 
    });
    
    window.addEventListener("beforeunload", (e) => { if (state.attemptId && !state.submitted) { e.preventDefault(); e.returnValue = ""; } });
  }

  function renderCurrent() {
    if (!state.questions || state.questions.length === 0) return;
    
    const q = state.questions[state.current];
    const workspace = $("af-workspace");
    const host = $("af-question");
    const editorHost = $("af-editor-container");
    
    host.innerHTML = ""; 
    editorHost.innerHTML = ""; 
    state.codeMirrors = {};
    workspace.classList.remove("af-coding-layout"); 
    hide("af-pane-right");
    
    $("af-q-num").textContent = state.current + 1; 
    const badges = $("af-q-badges"); badges.innerHTML = "";
    const mk = (t,c) => { const s = document.createElement("span"); s.className = "af-badge " + (c||""); s.textContent = t; return s; };
    badges.appendChild(mk(`${q.marks} mark${q.marks==1?"":"s"}`)); 
    if (q.required) badges.appendChild(mk("Required","af-badge-required")); 
    if (q.question_type==="Coding") badges.appendChild(mk(q.language||"code","af-badge-code"));
    
    const markBtn = $("af-mark-btn"); 
    markBtn.classList.toggle("af-mark-active", !!state.marked[q.name]); 
    $("af-mark-label").textContent = state.marked[q.name] ? "Marked" : "Mark for review";
    
    if (q._is_first_in_section) {
        const secHdr = document.createElement("div"); secHdr.className = "af-section-header";
        secHdr.innerHTML = `<h2>${q._section_name}</h2><div class="af-rich">${q._section_instructions || ""}</div>`;
        host.appendChild(secHdr);
    }

    const bodyDiv = document.createElement("div"); bodyDiv.className = "af-q-text af-rich"; bodyDiv.innerHTML = q.question_html; host.appendChild(bodyDiv); 
    const ans = state.answers[q.name];
    
    if (q.question_type === "Single Choice" || q.question_type === "True/False") {
      const wrap = document.createElement("div"); wrap.className = "af-options";
      (q.options || []).forEach((o, idx) => { 
          const l = document.createElement("label"); l.className = "af-opt"; if (ans === o.name) l.classList.add("af-opt-selected"); 
          l.innerHTML = `<input type="radio" name="opt" value="${o.name}" ${ans===o.name?"checked":""}><span class="af-opt-letter">${String.fromCharCode(65+idx)}</span><span class="af-opt-text">${o.text}</span>`; 
          l.querySelector("input").onchange = () => { 
              document.querySelectorAll(".af-opt").forEach(x=>x.classList.remove("af-opt-selected")); 
              l.classList.add("af-opt-selected"); 
              queueSave(q.name, o.name); 
          }; 
          wrap.appendChild(l); 
      }); 
      host.appendChild(wrap);
    } else if (q.question_type === "Multiple Select") {
      const set = new Set(ans || []); const wrap = document.createElement("div"); wrap.className = "af-options";
      (q.options || []).forEach((o, idx) => { 
          const l = document.createElement("label"); l.className = "af-opt"; if (set.has(o.name)) l.classList.add("af-opt-selected"); 
          l.innerHTML = `<input type="checkbox" value="${o.name}" ${set.has(o.name)?"checked":""}><span class="af-opt-letter">${String.fromCharCode(65+idx)}</span><span class="af-opt-text">${o.text}</span>`; 
          l.querySelector("input").onchange = (e) => { 
              if(e.target.checked){set.add(o.name);l.classList.add("af-opt-selected");}
              else{set.delete(o.name);l.classList.remove("af-opt-selected");} 
              queueSave(q.name, Array.from(set)); 
          }; 
          wrap.appendChild(l); 
      }); 
      host.appendChild(wrap);
    } else if (q.question_type === "Numeric" || q.question_type === "Short Text") {
      const inp = document.createElement("input"); 
      inp.className = "af-input"; 
      inp.type = q.question_type === "Numeric" ? "number" : "text"; 
      inp.step = "any"; 
      inp.value = ans == null ? "" : ans; 
      inp.placeholder = q.question_type === "Numeric" ? "Enter a number" : "Type your answer here"; 
      inp.oninput = debounce(() => queueSave(q.name, q.question_type === "Numeric" ? (inp.value === "" ? null : parseFloat(inp.value)) : inp.value), 600); 
      host.appendChild(inp);
    } else if (q.question_type === "Long Text") {
      const ta = document.createElement("textarea"); 
      ta.className = "af-textarea"; 
      ta.placeholder = "Type your detailed response here"; 
      ta.value = ans || ""; 
      ta.oninput = debounce(() => queueSave(q.name, ta.value), 600); 
      host.appendChild(ta);
    } else if (q.question_type === "Coding") { 
        workspace.classList.add("af-coding-layout"); 
        show("af-pane-right"); 
        renderCoding(host, editorHost, q, ans); 
    }
    
    $("af-prev").disabled = state.current === 0; 
    $("af-next").disabled = state.current === state.questions.length - 1;
  }

  function renderCoding(leftHost, rightHost, q, ans) {
    const problem = document.createElement("div"); problem.className = "af-codeproblem"; 
    const fnName = q.coding_function_name || "solve";
    problem.innerHTML = `<div class="af-codeproblem-title">Expected Function: <code>${fnName}()</code></div>`;
    
    if (q.public_test_cases && q.public_test_cases.length) {
      const list = document.createElement("div"); list.className = "af-test-list";
      q.public_test_cases.forEach((t, i) => { 
          const row = document.createElement("div"); row.className = "af-test-row"; 
          row.innerHTML = `<div class="af-test-num">${i+1}</div><div class="af-test-io"><div><span class="af-test-label">Args</span><code>${escapeHtml(t.input_data || "[]")}</code></div><div><span class="af-test-label">Expected</span><code>${escapeHtml(t.expected_output || "")}</code></div></div>`; 
          list.appendChild(row); 
      }); 
      problem.appendChild(list);
    }
    leftHost.appendChild(problem);

    const toolbar = document.createElement("div"); toolbar.className = "af-code-toolbar"; 
    const runsLeft = q.max_runs > 0 ? q.max_runs - (q.runs_used || 0) : null; 
    const runDisabled = !q.allow_test_run || (runsLeft !== null && runsLeft <= 0);
    toolbar.innerHTML = `<div><span class="af-lang-badge">${q.language || "code"}</span><span class="af-runs-info" id="af-runs-info">${runsLeft === null ? "" : runsLeft > 0 ? `${runsLeft} runs left` : "No runs left"}</span></div><button class="af-btn af-btn-run" id="af-run-btn" ${runDisabled?"disabled":""}>▶ Run code</button>`; 
    rightHost.appendChild(toolbar);

    const ta = document.createElement("textarea"); ta.value = ans || q.starter_code || ""; rightHost.appendChild(ta);
    if (window.CodeMirror) { 
        const mode = q.language === "javascript" ? "javascript" : (q.language === "html" ? "htmlmixed" : "python");
        const cm = CodeMirror.fromTextArea(ta, { lineNumbers:true, mode:mode, autoCloseBrackets:true, matchBrackets:true, indentUnit:4, tabSize:4, theme: "default" }); 
        state.codeMirrors[q.name] = cm; 
        cm.setSize("100%", "100%"); 
        cm.on("change", debounce(() => queueSave(q.name, cm.getValue()), 900)); 
    } else { 
        ta.style.display = "block"; ta.style.width = "100%"; ta.style.height = "100%"; 
        ta.oninput = debounce(() => queueSave(q.name, ta.value), 700); 
    }

    const results = document.createElement("div"); results.className = "af-code-results af-hidden"; results.id = "af-code-results"; rightHost.appendChild(results);
    if (!runDisabled) $("af-run-btn").onclick = () => runCode(q, state.codeMirrors[q.name] ? state.codeMirrors[q.name].getValue() : ta.value);
  }

  async function runCode(q, code) {
    const btn = $("af-run-btn"), results = $("af-code-results"); 
    btn.disabled = true; btn.textContent = "Running…"; 
    results.classList.remove("af-hidden"); 
    results.innerHTML = `<div class="af-run-summary" style="background:#1e1e1e;color:#a3a3a3;"><div class="af-spinner af-spinner-sm"></div> Executing code...</div>`;
    
    try { 
        const r = await call("run_code", {question:q.name, code:code}); 
        if (!r || !r.message || !r.message.ok) { 
            results.innerHTML = `<div class="af-run-summary af-fail">Error: ${escapeHtml(r?.message?.error || "Run failed.")}</div>`; 
            return; 
        } 
        renderRunResults(results, r.message, q); 
        if (r.message.summary) { q.runs_used = (q.runs_used||0) + 1; updateRunsInfo(q); } 
    } catch (e) { 
        results.innerHTML = `<div class="af-run-summary af-fail">Error: ${escapeHtml(e.message)}</div>`; 
    } finally { 
        btn.disabled = false; btn.textContent = "▶ Run code"; 
    }
  }

  function renderRunResults(el, msg, q) {
    if (!q.show_test_results || !msg.tests) { 
        el.innerHTML = `<div class="af-run-summary af-ok">✓ <strong>${msg.summary.passed}/${msg.summary.total}</strong> tests passed</div>`; 
        return; 
    }
    const s = msg.summary, ok = s.passed === s.total; 
    let html = `<div class="af-run-summary ${ok?"af-ok":"af-fail"}">${ok?"✓":"✗"} <strong>${s.passed}/${s.total}</strong> tests passed</div><div class="af-test-results">`;
    msg.tests.forEach((t, i) => { 
        html += `<div class="af-test-result ${t.passed?"af-pass":"af-failed"}"><div class="af-test-result-head"><span class="af-test-icon">${t.passed?"✓":"✗"}</span><span>${escapeHtml(t.description)}</span></div>`; 
        if (!t.passed) { 
            html += `<div class="af-test-detail">${t.timed_out?"<div><strong>Timed out</strong></div>":""}<div><span class="af-test-label">Expected</span><pre>${escapeHtml(t.expected||"")}</pre></div><div><span class="af-test-label">Got</span><pre>${escapeHtml(t.stdout||"")}</pre></div>${t.stderr?`<div><span class="af-test-label">Error</span><pre style="color:#f87171">${escapeHtml(t.stderr)}</pre></div>`:""}</div>`; 
        } 
        html += `</div>`; 
    }); 
    el.innerHTML = html + `</div>`;
  }
  
  function updateRunsInfo(q) { 
      const info = $("af-runs-info"), btn = $("af-run-btn"); 
      if(!info||!btn) return; 
      const runsLeft = q.max_runs > 0 ? q.max_runs - (q.runs_used||0) : null; 
      if (runsLeft === null) return; 
      if (runsLeft <= 0) { info.textContent = "No runs left"; btn.disabled = true; } else { info.textContent = `${runsLeft} runs left`; } 
  }
  
  async function toggleMark() { 
      const q = state.questions[state.current], next = !state.marked[q.name]; 
      state.marked[q.name] = next; 
      renderCurrent(); renderNav(); 
      logEvent("mark_for_review", `q=${q.name} marked=${next}`); 
      try { await call("toggle_mark_for_review", {question:q.name, marked:next?1:0}); } catch(_) {} 
  }
  
  function queueSave(question, payload) { 
      state.answers[question] = payload; 
      state.saveQueue.set(question, payload); 
      updateLocalStorage(); 
      renderNav(); 
      drainSaves(); 
  }
  
  async function drainSaves() {
    if (state.saveInFlight || !state.saveQueue.size) return; 
    state.saveInFlight = true; 
    $("af-save-status").innerHTML = '<span class="af-dot af-dot-saving"></span> Saving…';
    try {
      while (state.saveQueue.size) {
        const [q, p] = state.saveQueue.entries().next().value; state.saveQueue.delete(q); updateLocalStorage();
        const r = await call("save_answer", {question:q, payload:p});
        if (!r || !r.message || !r.message.ok) { 
            state.saveQueue.set(q, p); 
            updateLocalStorage(); 
            $("af-save-status").innerHTML = '<span class="af-dot af-dot-warn"></span> Retrying…'; 
            await new Promise(res => setTimeout(res, 1500)); 
            break; 
        }
      }
      if (!state.saveQueue.size) $("af-save-status").innerHTML = '<span class="af-dot af-dot-ok"></span> Saved';
    } catch(e) { 
        $("af-save-status").innerHTML = '<span class="af-dot af-dot-warn"></span> Offline'; 
    } finally { 
        state.saveInFlight = false; 
    }
    if (state.saveQueue.size) setTimeout(drainSaves, 1500);
  }

  function openSubmitModal() {
    const answered = state.questions.filter(q => state.answers[q.name] != null).length, unanswered = state.questions.length - answered, marked = Object.values(state.marked).filter(Boolean).length;
    $("af-submit-summary").innerHTML = `<div class="af-submit-stat"><span>${answered}</span> Answered</div><div class="af-submit-stat ${unanswered?"af-submit-stat-warn":""}"><span>${unanswered}</span> Unanswered</div>${marked?`<div class="af-submit-stat"><span>${marked}</span> Marked</div>`:""}`; 
    show("af-submit-modal");
  }

  async function doSubmit(auto) {
    if (!auto && !confirm("Submit final answers?")) return;
    if (state.saveQueue.size) await drainSaves();
    state.submitted = true;
    try {
      const r = await call("submit_attempt");
      if (!r || !r.message || !r.message.ok) { state.submitted = false; return alert("Submit failed: " + (r?.message?.error || "unknown")); }
      if (state.timerId) clearInterval(state.timerId); 
      sessionStorage.removeItem(TOKEN_KEY);
      hide("af-attempt"); hide("af-submit-modal"); show("af-done"); 
      $("af-done-ref-value").textContent = state.attemptId;
      if (r.message.show_result && r.message.score !== null) { 
          $("af-done-msg").innerHTML = `Your final score: <strong>${r.message.score}%</strong>`; 
      } else { 
          $("af-done-msg").textContent = "Your submission is pending review. You will be notified when grading is complete."; 
      }
      if (document.fullscreenElement) document.exitFullscreen().catch(()=>{});
    } catch(e) { 
        state.submitted = false; 
        alert("Submit error: " + e.message); 
    }
  }

  function showError(msg) { 
      $("af-error-msg").textContent = msg; 
      hide("af-loading"); hide("af-landing"); show("af-error"); 
  }
  function debounce(fn, ms) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }
  function escapeHtml(s) { return String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;"); }

  (async () => {
    if (!window.ASSESSFLOW_TOKEN) return showError("Missing token.");
    try { 
        const r = await call("verify_invitation", {token: window.ASSESSFLOW_TOKEN}); 
        if (!r || !r.message || !r.message.ok) return showError(r?.message?.error || "Invalid invitation."); 
        renderLanding(r.message); 
        $("af-start").onclick = onStart; 
    } catch(e) { 
        showError(e.message); 
    }
  })();
})();
