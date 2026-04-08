// --- UI Toggles ---
function showSignup() {
    document.getElementById("loginForm").style.display = "none";
    document.getElementById("signupForm").style.display = "block";
    document.getElementById("verifyForm").style.display = "none";
}

function showLogin() {
    document.getElementById("loginForm").style.display = "block";
    document.getElementById("signupForm").style.display = "none";
    document.getElementById("verifyForm").style.display = "none";
}

function showVerify(email) {
    document.getElementById("loginForm").style.display = "none";
    document.getElementById("signupForm").style.display = "none";
    document.getElementById("verifyForm").style.display = "block";
    document.getElementById("verify-email-display").textContent = email;
}

function toggleTeacherCode() {
    const role = document.getElementById("reg-role").value;
    const group = document.getElementById("teacher-code-group");
    if (role === "teacher") {
        group.style.display = "block";
        document.getElementById("reg-code").required = true;
    } else {
        group.style.display = "none";
        document.getElementById("reg-code").required = false;
        document.getElementById("reg-code").value = "";
    }
}

// --- Login Handling ---
async function handleLogin(event) {
    event.preventDefault();
    const form = event.target;
    // Fix: explicitly construct object to ensure keys match
    const data = {
        username: form.username.value,
        password: form.password.value
    };
    const errorDiv = document.getElementById("login-error");

    try {
        const response = await fetch("/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(data)
        });

        if (response.redirected) {
            window.location.href = response.url;
        } else {
            const resData = await response.json();
            errorDiv.textContent = resData.error || "Login failed";
        }
    } catch (error) {
        errorDiv.textContent = "An error occurred. Please try again.";
        console.error(error);
    }
}

// --- Registration Handling ---
async function handleRegister(event) {
    event.preventDefault();
    const form = event.target;
    const errorDiv = document.getElementById("signup-error");
    const btn = form.querySelector("button");

    const data = {
        username: form.username.value,
        email: form.email.value,
        role: form.role.value,
        password: form.password.value,
        teacher_code: form.teacher_code ? form.teacher_code.value : null
    };

    btn.disabled = true;
    errorDiv.textContent = "";

    try {
        const response = await fetch("/api/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });

        const resData = await response.json();

        if (response.ok) {
            // Success -> Show Verify
            showVerify(resData.identifier);
        } else {
            errorDiv.textContent = resData.error || "Registration failed";
        }
    } catch (error) {
        errorDiv.textContent = "Network error. Try again.";
    } finally {
        btn.disabled = false;
    }
}

// --- Verification Handling ---
async function handleVerify(event) {
    event.preventDefault();
    const form = event.target;
    const email = document.getElementById("verify-email-display").textContent;
    const otp = form.otp.value;
    const errorDiv = document.getElementById("verify-error");

    try {
        const response = await fetch("/api/confirm_verification", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ identifier: email, otp: otp })
        });

        const resData = await response.json();

        if (response.ok) {
            alert("Verification Successful! Please Login.");
            showLogin();
        } else {
            errorDiv.textContent = resData.error || "Verification failed";
        }
    } catch (error) {
        errorDiv.textContent = "Error during verification.";
    }
}

// --- Topic Handling ---
let currentTopic = null;

function selectTopic(topic) {
    currentTopic = topic;
    const placeholder = document.getElementById("placeholder");
    const input = document.getElementById("userQuestion");
    const btn = document.getElementById("sendBtn");

    if (placeholder) placeholder.style.display = "none";
    input.disabled = false;
    btn.disabled = false;

    // Add a system message indicating topic switch
    addMessage(`Topic switched to: **${topic}**. What would you like to know?`, "assistant");
}

function clearChat() {
    const container = document.getElementById("chat-container");
    container.innerHTML = `<div class="chat-placeholder" id="placeholder">
        <ion-icon name="chatbubbles-outline"></ion-icon>
        <p>Select a topic from the sidebar and start asking questions!</p>
    </div>`;
    currentTopic = null;
    document.getElementById("userQuestion").disabled = true;
    document.getElementById("sendBtn").disabled = true;

    // Reset radio buttons
    document.querySelectorAll('input[name="topic"]').forEach(input => input.checked = false);
}

function addMessage(text, role, isLoading = false) {
    const container = document.getElementById("chat-container");
    if (!container) return;

    // Remove placeholder if present
    const placeholder = document.getElementById("placeholder");
    if (placeholder) placeholder.style.display = "none";

    const div = document.createElement("div");
    div.className = `flex w-full mb-4 ${role === "user" ? "justify-end" : "justify-start"}`;
    if (isLoading) div.id = "msg-" + Date.now(); // ID for removal

    const bubble = document.createElement("div");
    bubble.className = role === "user"
        ? "max-w-[80%] bg-primary-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm shadow-md"
        : "max-w-[80%] bg-white/10 text-slate-200 rounded-2xl rounded-tl-sm px-4 py-3 text-sm border border-white/5";

    if (isLoading) bubble.classList.add("animate-pulse");

    bubble.innerHTML = text; // Enable HTML rendering
    div.appendChild(bubble);
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;

    return div.id;
}

// --- Chat Handling ---
// --- Navigation ---
const views = ['courses', 'community', 'progress', 'collaborate', 'plans'];

function switchView(viewName) {
    // Update Sidebar
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active', 'bg-white/10', 'text-white'));
    const activeNav = document.getElementById(`nav-${viewName}`);
    if (activeNav) activeNav.classList.add('active', 'bg-white/10', 'text-white');

    // Update Main View
    views.forEach(v => {
        const el = document.getElementById(`view-${v}`);
        if (el) {
            if (v === viewName) {
                el.classList.remove('hidden');
                el.classList.add('flex');
            } else {
                el.classList.add('hidden');
                el.classList.remove('flex');
            }
        }
    });

    // Close Chat Overlay if open
    const viewChat = document.getElementById('view-chat');
    if (viewChat && viewChat.style.display !== 'none') {
        viewChat.style.transform = 'translateX(100%)';
        setTimeout(() => {
            viewChat.style.display = 'none';
        }, 300);
    }

    // Ensure courses view is reset if switching to it
    const viewCourses = document.getElementById('view-courses');
    if (viewCourses && viewName === 'courses') {
        viewCourses.style.display = 'flex';
        setTimeout(() => {
            viewCourses.style.transform = 'scale(1)';
            viewCourses.style.opacity = '1';
        }, 100);
    }

    // Trigger Data Load
    if (viewName === 'community' && typeof loadCommunityTopics === 'function') loadCommunityTopics();
    if (viewName === 'progress') {
        if (typeof loadProgress === 'function') loadProgress(); // Existing XP load
        if (typeof loadStudentAnalytics === 'function') loadStudentAnalytics(); // New AI Analytics
    }
    if (viewName === 'plans' && typeof loadStudentPlans === 'function') loadStudentPlans();
    if (viewName === 'collaborate' && typeof loadGroupTopics === 'function') loadGroupTopics();
}

// --- Student Analytics & Plans ---
async function loadStudentAnalytics() {
    const content = document.getElementById('ai-prediction-content');
    if (!content) return;

    content.innerHTML = '<p class="text-slate-500 text-sm animate-pulse">Running AI Analysis...</p>';

    try {
        const res = await fetch('/api/student/analytics');
        if (!res.ok) throw new Error("API returned " + res.status);

        const data = await res.json();
        const pred = data.prediction;

        let colorClass = "text-green-400";
        if (pred.label === "At Risk") colorClass = "text-red-400 animate-pulse";
        if (pred.label === "Stable") colorClass = "text-yellow-400";

        content.innerHTML = `
            <div class="flex items-center gap-3 mb-2">
                <div class="text-3xl font-bold ${colorClass}">${pred.label}</div>
            </div>
            <p class="text-sm text-slate-300 font-medium italic">"${pred.msg}"</p>
            <div class="mt-4 grid grid-cols-2 gap-2 text-xs text-slate-500 border-t border-white/5 pt-2">
                <div>Activity Score: ${data.metrics.active_days}</div>
                <div>Avg Quiz: ${Math.round(data.metrics.avg_quiz_score)}%</div>
            </div>
        `;
    } catch (e) {
        console.error(e);
        content.innerHTML = '<p class="text-red-400 text-sm">Error loading analytics. Please try again later.</p>';
    }
}

async function loadStudentPlans() {
    const container = document.getElementById('student-plans-list');
    if (!container) return;

    try {
        const res = await fetch('/api/student/plans');
        const data = await res.json();

        if (data.length === 0) {
            container.innerHTML = '<p class="text-slate-500 col-span-full text-center py-10">No working plans available.</p>';
            return;
        }

        container.innerHTML = data.map(plan => `
            <div class="bg-glass-card rounded-2xl p-6 border border-white/5 hover:border-primary-500/30 transition-all cursor-pointer group">
                <div class="flex justify-between items-start mb-2">
                    <span class="p-2 bg-primary-500/10 rounded-lg text-primary-400"><span class="material-symbols-rounded">article</span></span>
                    <span class="text-[10px] text-slate-500">${new Date(plan.created_at).toLocaleDateString()}</span>
                </div>
                <h3 class="font-bold text-white text-lg group-hover:text-primary-400 transition-colors">${plan.title}</h3>
                <p class="text-xs text-slate-400 mt-2 line-clamp-2">${plan.summary || 'No summary available.'}</p>
                <a href="${plan.content}" target="_blank" class="mt-4 inline-block text-xs font-bold text-primary-400 hover:text-white transition-colors border border-primary-500/20 px-4 py-2 rounded-lg hover:bg-primary-500">Read Document</a>
            </div>
        `).join('');

    } catch (e) {
        container.innerHTML = '<p class="text-red-400 text-center">Error fetching plans.</p>';
    }
}

// --- Chat Handling (Updated with XP) ---
async function handleChat(event) {
    event.preventDefault();
    // Use window.currentTopic if defined (from student.html) or module scope currentTopic
    const topic = window.currentTopic || currentTopic;
    if (!topic) return;

    const input = document.getElementById("userQuestion");
    const question = input.value.trim();
    if (!question) return;

    // Add User Message
    addMessage(question, "user");
    input.value = "";
    input.disabled = true;

    // Show Typing Indicator
    const loadingId = addMessage("Thinking...", "assistant", true);

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: question, namespace: topic })
        });

        const data = await response.json();

        // Remove loading message
        const loadingEl = document.getElementById(loadingId);
        if (loadingEl) loadingEl.remove();

        // Add Assistant Response
        let answer = data.answer.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');
        addMessage(answer, "assistant");

        // Award XP and Update UI
        fetch("/api/progress/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ xp_amount: 10 })
        })
            .then(res => res.json())
            .then(data => {
                console.log("XP Updated:", data);
                // Refresh visuals if function exists
                if (typeof loadProgress === 'function') loadProgress();

                // Show small notification in chat
                const container = document.getElementById("chat-container");
                if (container) {
                    const xpMsg = document.createElement("div");
                    xpMsg.className = "flex justify-center my-2";
                    xpMsg.innerHTML = `<span class="bg-yellow-500/20 text-yellow-200 text-xs px-2 py-1 rounded-full border border-yellow-500/30 flex items-center gap-1">
                    <span class="material-symbols-rounded text-sm">military_tech</span> +10 XP earned!
                </span>`;
                    container.appendChild(xpMsg);
                    container.scrollTop = container.scrollHeight;
                }
            })
            .catch(err => console.error("XP Error:", err));

    } catch (error) {
        const loadingEl = document.getElementById(loadingId);
        if (loadingEl) loadingEl.remove();
        addMessage("Sorry, something went wrong.", "assistant");
    } finally {
        input.disabled = false;
        input.focus();
    }
}

// --- Teacher Upload Handling ---
function switchTab(tabName) {
    // Buttons
    document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
    if (event && event.target) event.target.classList.add("active"); // Fix potential null event

    // Content
    document.querySelectorAll(".tab-content").forEach(content => content.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(content => content.classList.add("hidden")); // Explicit hide

    if (tabName === 'text') {
        const el = document.getElementById("textTab");
        el.classList.add("active");
        el.classList.remove("hidden");
    } else if (tabName === 'url') {
        const el = document.getElementById("urlTab");
        el.classList.add("active");
        el.classList.remove("hidden");
    } else if (tabName === 'file') {
        const el = document.getElementById("fileTab");
        el.classList.add("active");
        el.classList.remove("hidden");
    }
}

/* 
async function handleUpload(event) {
    event.preventDefault();
    const btn = document.getElementById("uploadBtn");
    const statusArea = document.getElementById("status-area");
    const spinner = document.getElementById("loadingSpinner");
    const msg = document.getElementById("status-message");
    const jsonPreview = document.getElementById("json-preview");

    const contentName = document.getElementById("contentName").value;
    const manualText = document.getElementById("manualText").value;
    const urlInput = document.getElementById("urlInput").value;
    const fileInput = document.getElementById("fileInput");

    if (!contentName) return alert("Please enter a content name.");
    // if (!manualText && !urlInput && (!fileInput.files || fileInput.files.length === 0)) return alert("Please provide text, URL, or File.");

    // UI Updates
    btn.disabled = true;
    statusArea.classList.remove("hidden");
    statusArea.style.display = "block"; // Ensure it's visible if hidden class removal isn't enough
    if(spinner) spinner.style.display = "block";
    msg.textContent = "Processing vectors and extracting knowledge graph...";
    jsonPreview.textContent = "";

    try {
        const formData = new FormData();
        formData.append("content_name", contentName);

        if (manualText) formData.append("text", manualText);
        else if (urlInput) formData.append("url", urlInput);
        else if (fileInput.files.length > 0) formData.append("file", fileInput.files[0]);

        const response = await fetch("/api/upload", {
            method: "POST",
            body: formData // No Content-Type header; browser sets it for FormData
        });

        const data = await response.json();

        if (response.ok) {
            msg.textContent = "Upload Complete!";
            msg.style.color = "#2ecc71";
            jsonPreview.textContent = JSON.stringify(data.graph_preview || {}, null, 2);
        } else {
            msg.textContent = "Error: " + data.error;
            msg.style.color = "#e74c3c";
        }

    } catch (error) {
        console.error(error);
    } finally {
        const spinner = document.getElementById("loadingSpinner");
        const btn = document.getElementById("uploadBtn");
        if (spinner) spinner.style.display = "none";
        if (btn) btn.disabled = false;
    }
} 
*/

// --- Helper ---
async function fetchAPI(endpoint, method = 'GET', body = null) {
    try {
        const options = { method, headers: { 'Content-Type': 'application/json' } };
        if (body) options.body = JSON.stringify(body);
        const res = await fetch(endpoint, options);

        // Try to parse JSON response
        const data = await res.json().catch(() => null);

        if (!res.ok) {
            const errorMsg = (data && data.error) ? data.error : `API Error: ${res.statusText}`;
            throw new Error(errorMsg);
        }
        return data; // Return successful data
    } catch (e) {
        console.error(e);
        // Alert the user so they know something went wrong
        alert(e.message || "An unexpected error occurred.");
        return null;
    }
}

// --- Student View Navigation & Logic ---

// Courses & Chat
// Courses & Chat
function openTopic(topicName) {
    console.log("Redirecting to chat for:", topicName);
    window.location.href = `/student/chat?course=${encodeURIComponent(topicName)}`;
}

async function loadTopicDetails(topic) {
    // Clear previous
    const summaryEl = document.getElementById("topic-summary-content");
    const pdfBtn = document.getElementById("view-pdf-btn");
    const quizBtn = document.getElementById("take-quiz-btn");

    if (summaryEl) summaryEl.innerHTML = "<span class='animate-pulse'>Loading summary...</span>";
    if (pdfBtn) pdfBtn.classList.add("hidden");

    try {
        const data = await fetchAPI(`/api/topic/${topic}`);
        if (data) {
            if (summaryEl) summaryEl.innerHTML = data.summary || "No summary available.";
            if (pdfBtn) {
                if (data.pdf_path) {
                    pdfBtn.onclick = () => window.open(data.pdf_path, '_blank');
                    pdfBtn.classList.remove("hidden");
                } else {
                    pdfBtn.classList.add("hidden");
                }
            }
        }
    } catch (e) {
        console.error("Error loading topic details", e);
    }
}

async function startQuiz() {
    const topic = window.currentTopic;
    if (!topic) return;

    // Show Modal or Overlay?
    // Quick alert quiz for MVP
    const confirmStart = confirm(`Start a quick quiz for ${topic}?`);
    if (!confirmStart) return;

    try {
        const questions = await fetchAPI(`/api/quiz/${topic}`);
        if (questions && questions.length > 0) {
            let score = 0;
            for (let i = 0; i < questions.length; i++) {
                const q = questions[i];
                const opts = q.options.map((o, idx) => `${idx + 1}. ${o}`).join("\n");
                const userAns = prompt(`Q${i + 1}: ${q.question}\n\n${opts}\n\nEnter option number (1-${q.options.length}):`);

                if (userAns) {
                    const selected = q.options[parseInt(userAns) - 1];
                    if (selected === q.answer) score++;
                }
            }
            alert(`Quiz Complete!\nYou scored ${score}/${questions.length}`);

            // Award XP
            if (score > 0) {
                fetch("/api/progress/update", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ xp_amount: score * 10 })
                }).then(() => {
                    if (typeof loadProgress === 'function') loadProgress();
                    alert(`You earned +${score * 10} XP!`);
                });
            }
        } else {
            alert("No quiz questions available for this topic.");
        }
    } catch (e) {
        alert("Failed to load quiz.");
    }
}

function closeTopic() {
    const viewCourses = document.getElementById('view-courses');
    const viewChat = document.getElementById('view-chat');
    if (viewCourses && viewChat) {
        viewChat.style.transform = 'translateX(100%)';

        // Ensure it's hidden after transition to prevent blocking clicks
        setTimeout(() => {
            viewChat.style.display = 'none';
        }, 300);

        viewCourses.style.display = 'flex';
        // Small delay to allow display:flex to apply before transition
        setTimeout(() => {
            viewCourses.style.transform = 'scale(1)';
            viewCourses.style.opacity = '1';
        }, 50);

        // Clear current topic
        window.currentTopic = null;
    }
}

// Attach to window for global access
window.openTopic = openTopic;
window.closeTopic = closeTopic;

// Community
async function loadCommunityTopics() {
    const topics = await fetchAPI('/api/topics');
    const select = document.getElementById('communityTopicSelect');
    if (!select) return;
    select.innerHTML = '<option value="">Select Topic...</option>';
    if (topics) topics.forEach(t => {
        select.innerHTML += `<option value="${t}">${t}</option>`;
    });
}

async function loadCommunity() {
    const select = document.getElementById('communityTopicSelect');
    if (!select) return;
    const topic = select.value;
    const container = document.getElementById('community-posts-container');
    if (!topic || !container) return;

    container.innerHTML = '<p class="text-center text-slate-500">Loading...</p>';
    try {
        const posts = await fetchAPI(`/api/community/${topic}`);

        container.innerHTML = '';
        if (posts && posts.length > 0) {
            posts.forEach(post => {
                const date = new Date(post.created_at).toLocaleDateString();
                container.innerHTML += `
                <div class="bg-glass-card rounded-xl p-4 border border-white/5">
                    <div class="flex justify-between items-start mb-2">
                        <span class="font-bold text-white text-lg">${post.title}</span>
                        <span class="text-xs text-slate-500">${date}</span>
                    </div>
                    <p class="text-sm text-slate-300 mb-3">${post.content}</p>
                    <div class="flex items-center gap-2 text-xs text-slate-500">
                        <span class="font-medium text-primary-400">@${post.username}</span>
                        <span>•</span>
                        <span>0 mentions</span>
                    </div>
                </div>`;
            });
        } else {
            container.innerHTML = '<p class="text-center text-slate-500">No posts yet. Be the first!</p>';
        }
    } catch (e) {
        console.error("Community Load Error:", e);
        container.innerHTML = '<p class="text-center text-red-400">Failed to load posts.</p>';
    }
}

async function openPostModal() {
    const select = document.getElementById('communityTopicSelect');
    if (!select) return;

    // Auto-retry loading topics if empty
    if (select.options.length <= 1) { // Only default option
        await loadCommunityTopics();
    }

    const topic = select.value;
    if (!topic) {
        alert("Please select a topic from the dropdown list first.");
        return;
    }

    const title = prompt("Post Title:");
    if (!title) return; // User cancelled

    const content = prompt("Post Content:");
    if (!content) return; // User cancelled

    if (title && content) {
        try {
            const res = await fetchAPI('/api/community/post', 'POST', { topic, title, content });
            if (!res) return; // Stop if failed

            await loadCommunity(); // Refresh posts

            // Award XP
            fetch("/api/progress/update", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ xp_amount: 20 })
            })
                .then(res => res.json())
                .then(data => {
                    if (typeof loadProgress === 'function') loadProgress();
                    alert(`Post created! You earned +20 XP.`);
                });

        } catch (e) {
            console.error("Post Error:", e);
            alert("Failed to create post. Please try again.");
        }
    }
}

// Progress
async function loadProgress() {
    const data = await fetchAPI('/api/progress');
    if (data) {
        const xpEl = document.getElementById('display-xp');
        const lvlEl = document.getElementById('display-level');
        const lbEl = document.getElementById('leaderboard-my-xp');
        if (xpEl) xpEl.innerText = data.total_xp;
        if (lvlEl) lvlEl.innerText = data.level;
        if (lbEl) lbEl.innerText = `${data.total_xp} XP`;
    }
}

// Collaborate (Jigsaw)
async function loadGroupTopics() {
    const topics = await fetchAPI('/api/topics');
    const select = document.getElementById('groupFromTopic');
    if (!select) return;
    select.innerHTML = '<option value="">Choose Topic...</option>';
    if (topics) topics.forEach(t => {
        select.innerHTML += `<option value="${t}">${t}</option>`;
    });
}

async function joinGroup() {
    const select = document.getElementById('groupFromTopic');
    if (!select) return;
    const topic = select.value;
    if (!topic) return;

    const res = await fetchAPI('/api/groups/join', 'POST', { topic });
    if (res) {
        showGroupView(topic);
    }
}

async function showGroupView(topic) {
    document.getElementById('no-group-view').classList.add('hidden');
    document.getElementById('group-active-view').classList.remove('hidden');
    document.getElementById('group-active-view').classList.add('flex');

    window.currentGroupTopic = topic;
    refreshGroupData();
}

async function refreshGroupData() {
    if (!window.currentGroupTopic) return;
    try {
        const data = await fetchAPI(`/api/groups/current?topic=${window.currentGroupTopic}`);
        if (data && !data.error) {
            const nameEl = document.getElementById('group-name');
            const topicEl = document.getElementById('group-topic');
            if (nameEl) nameEl.innerText = data.name;
            if (topicEl) topicEl.innerText = window.currentGroupTopic;
            window.currentGroupId = data.group_id;

            const artifact = document.getElementById('group-artifact');
            if (artifact && document.activeElement !== artifact) {
                artifact.value = data.artifact_content;
                artifact.disabled = false; // Enable if it was disabled
            }

            const mData = document.getElementById('group-members');
            if (mData) {
                mData.innerHTML = '';
                data.members.forEach(m => {
                    mData.innerHTML += `<div class="flex items-center gap-2 text-sm text-slate-300">
                        <div class="size-6 rounded-full bg-slate-700 flex items-center justify-center text-xs">${m[0]}</div>
                        <span>${m}</span>
                    </div>`;
                });
            }
        } else {
            // Handle case where user is not in group yet but view is open (shouldn't happen via join, but via refresh)
            // Maybe reset view or show empty state? For now, just log.
            console.log("Group data unavailable or user not in group");
        }
    } catch (e) {
        console.error("Error refreshing group:", e);
    }
}

// Global Event Listeners setup when DOM is ready or file is loaded
// --- Group Chat ---
async function sendGroupMessage() {
    const input = document.getElementById('group-chat-input');
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;

    input.value = '';
    input.focus();

    try {
        await fetchAPI('/api/groups/artifact', 'POST', {
            group_id: window.currentGroupId,
            content: text,
            append: true
        });
        // Immediate refresh to show message
        refreshGroupData();
    } catch (e) {
        console.error("Send failed:", e);
        alert("Failed to send message.");
    }
}

async function refreshGroupData() {
    if (!window.currentGroupTopic) return;
    try {
        const data = await fetchAPI(`/api/groups/current?topic=${window.currentGroupTopic}`);
        if (data && !data.error) {
            const nameEl = document.getElementById('group-name');
            const topicEl = document.getElementById('group-topic');
            if (nameEl) nameEl.innerText = data.name;
            if (topicEl) topicEl.innerText = window.currentGroupTopic;
            window.currentGroupId = data.group_id;

            // Members
            const mData = document.getElementById('group-members');
            if (mData) {
                mData.innerHTML = '';
                data.members.forEach(m => {
                    mData.innerHTML += `<div class="flex items-center gap-2 text-sm text-slate-300">
                        <div class="size-6 rounded-full bg-slate-700 flex items-center justify-center text-xs">${m[0]}</div>
                        <span>${m}</span>
                    </div>`;
                });
            }

            // Chat Messages
            const container = document.getElementById('group-chat-messages');
            if (container) {
                // Determine if we should scroll (only if already at bottom)
                const shouldScroll = container.scrollTop + container.clientHeight >= container.scrollHeight - 50;

                let html = '';
                if (data.artifact_content) {
                    const lines = data.artifact_content.split('\n');
                    lines.forEach(line => {
                        if (!line.trim()) return;
                        try {
                            const msg = JSON.parse(line);
                            // Check user
                            const isMe = msg.user === window.currentUser;
                            const align = isMe ? 'justify-end' : 'justify-start';
                            const bg = isMe ? 'bg-primary-600' : 'bg-white/10';
                            const label = isMe ? 'myself' : msg.user;
                            const radius = isMe ? 'rounded-tr-sm' : 'rounded-tl-sm';

                            html += `
                                <div class="flex w-full ${align}">
                                    <div class="max-w-[80%] ${bg} rounded-2xl ${radius} px-4 py-2 text-sm text-white shadow-sm">
                                        <div class="text-[10px] opacity-70 mb-0.5 font-bold uppercase tracking-wider text-slate-200">${label}</div>
                                        <div class="leading-relaxed break-words">${msg.text}</div>
                                    </div>
                                </div>
                             `;
                        } catch (e) {
                            // Legacy plain text support
                            html += `
                                <div class="flex w-full justify-start">
                                     <div class="max-w-[80%] bg-white/5 rounded-xl px-3 py-2 text-sm text-slate-300 italic border border-white/5">
                                        ${line}
                                     </div>
                                </div>
                            `;
                        }
                    });
                } else {
                    html = '<div class="text-center text-slate-500 text-xs mt-10">No messages yet. Start the conversation!</div>';
                }

                // Only update if changed to avoid jitter? Or just naive replacement.
                // Naive replacement is safer for consistency.
                if (container.innerHTML !== html) {
                    container.innerHTML = html;
                    if (shouldScroll || container.scrollTop === 0) {
                        container.scrollTop = container.scrollHeight;
                    }
                }
            }

        } else {
            console.log("Group data unavailable or user not in group");
        }
    } catch (e) {
        console.error("Error refreshing group:", e);
    }
}

// Global Event Listeners setup when DOM is ready or file is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Polling for Chat
    setInterval(() => {
        const el = document.getElementById('view-collaborate');
        // Check if element exists and is visible
        if (el && !el.classList.contains('hidden') && window.currentGroupTopic) {
            refreshGroupData();
        }
    }, 3000); // 3 seconds polling for chat
});
