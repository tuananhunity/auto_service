(function () {
    const state = {
        user: window.__INITIAL_STATE__.user,
        browserSession: window.__INITIAL_STATE__.browserSession,
        activeJob: null,
        groupSets: [],
        commentSets: [],
    };

    const socket = io();
    const logStream = document.getElementById("logStream");

    function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }

    function appendLog(message, level) {
        const entry = document.createElement("div");
        entry.className = "entry";
        entry.textContent = `[${level}] ${message}`;
        logStream.prepend(entry);
    }

    function renderSession(session, viewerUrl) {
        state.browserSession = session;
        setText("browserSessionStatus", session ? session.status : "offline");
        setText("displayInfo", session ? `${session.runtime_mode} / ${session.viewer_type}` : "-");

        const closeBtn = document.getElementById("closeBrowserBtn");
        const startBtn = document.getElementById("startJobBtn");
        const link = document.getElementById("remoteBrowserLink");
        const wrap = document.querySelector(".browser-frame-wrap");

        closeBtn.disabled = !session;
        startBtn.disabled = !session || session.status !== "ready";

        if (!session) {
            wrap.innerHTML = '<div class="empty-browser">Open a browser session to access the current runtime viewer.</div>';
            link.href = "#";
            link.classList.add("is-disabled");
            return;
        }

        link.href = `/remote-browser/${session.id}`;
        link.classList.remove("is-disabled");
        if (session.viewer_type === "novnc" && viewerUrl) {
            wrap.innerHTML = `<iframe id="remoteBrowserFrame" src="${viewerUrl}" title="Remote Browser"></iframe>`;
            return;
        }
        if (session.viewer_type === "external") {
            wrap.innerHTML = `
                <div class="empty-browser local-browser-card">
                    <div>
                        <strong>Local Chrome dev session is running.</strong>
                        <p>Chrome was opened directly on this Windows machine. Use the local Chrome window while this dashboard handles status and jobs.</p>
                        <p>Debug port: <code>${session.debug_port}</code></p>
                        <p>Profile path: <code>${session.profile_path}</code></p>
                    </div>
                </div>
            `;
            return;
        }
        wrap.innerHTML = '<div class="empty-browser">No embeddable viewer is available for this session.</div>';
    }

    function renderJob(job) {
        state.activeJob = job;
        setText("activeJobStatus", job ? job.status : "idle");
        document.getElementById("stopJobBtn").disabled = !job || !["starting", "running", "stopping"].includes(job.status);
    }

    function renderDataSets() {
        const groupList = document.getElementById("groupSetList");
        const commentList = document.getElementById("commentSetList");
        groupList.innerHTML = "";
        commentList.innerHTML = "";

        state.groupSets.forEach((item) => {
            const li = document.createElement("li");
            li.textContent = `${item.name} (${item.items.length})`;
            li.onclick = () => {
                document.getElementById("groupSetName").value = item.name;
                document.getElementById("groupItems").value = item.items.join("\n");
                document.getElementById("groupSetName").dataset.recordId = item.id;
            };
            groupList.appendChild(li);
        });

        state.commentSets.forEach((item) => {
            const li = document.createElement("li");
            li.textContent = `${item.name} (${item.items.length})`;
            li.onclick = () => {
                document.getElementById("commentSetName").value = item.name;
                document.getElementById("commentItems").value = item.items.join("\n");
                document.getElementById("commentSetName").dataset.recordId = item.id;
            };
            commentList.appendChild(li);
        });
    }

    async function fetchJson(url, options) {
        const response = await fetch(url, {
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            ...options,
        });
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.error || "Request failed");
        }
        return payload;
    }

    async function refreshSets() {
        const [groupPayload, commentPayload] = await Promise.all([
            fetchJson("/api/group-sets"),
            fetchJson("/api/comment-sets"),
        ]);
        state.groupSets = groupPayload.items || [];
        state.commentSets = commentPayload.items || [];
        renderDataSets();
    }

    async function saveSets() {
        const groupNameEl = document.getElementById("groupSetName");
        const commentNameEl = document.getElementById("commentSetName");

        const groupPayload = {
            id: groupNameEl.dataset.recordId || undefined,
            name: groupNameEl.value || "Default Target Set",
            items: document.getElementById("groupItems").value.split("\n"),
        };
        const commentPayload = {
            id: commentNameEl.dataset.recordId || undefined,
            name: commentNameEl.value || "Default Comment Set",
            items: document.getElementById("commentItems").value.split("\n"),
        };

        const [savedGroup, savedComment] = await Promise.all([
            fetchJson("/api/group-sets", { method: "POST", body: JSON.stringify(groupPayload) }),
            fetchJson("/api/comment-sets", { method: "POST", body: JSON.stringify(commentPayload) }),
        ]);

        groupNameEl.dataset.recordId = savedGroup.item.id;
        commentNameEl.dataset.recordId = savedComment.item.id;
        appendLog("Saved current data sets.", "info");
        await refreshSets();
    }

    async function openBrowserSession() {
        const payload = await fetchJson("/api/browser-sessions/open", { method: "POST", body: "{}" });
        const session = payload.browser_session;
        const details = await fetchJson(`/api/browser-sessions/${session.id}`);
        renderSession(details.browser_session, details.viewer_url);
        appendLog(`Opened browser session #${session.id}.`, "success");
    }

    async function closeBrowserSession() {
        if (!state.browserSession) return;
        const payload = await fetchJson(`/api/browser-sessions/${state.browserSession.id}/close`, {
            method: "POST",
            body: "{}",
        });
        renderSession(payload.browser_session.status === "stopped" ? null : payload.browser_session, payload.browser_session?.viewer_url || null);
        appendLog(`Closed browser session #${payload.browser_session.id}.`, "warning");
    }

    async function startJob() {
        if (!state.browserSession) {
            throw new Error("Browser session is required.");
        }
        await saveSets();
        const groupId = document.getElementById("groupSetName").dataset.recordId || state.groupSets[0]?.id;
        const commentId = document.getElementById("commentSetName").dataset.recordId || state.commentSets[0]?.id;
        const payload = await fetchJson("/api/jobs/start", {
            method: "POST",
            body: JSON.stringify({
                browser_session_id: state.browserSession.id,
                group_set_id: groupId,
                comment_set_id: commentId,
                delay: Number(document.getElementById("delayInput").value || 5),
                max_posts: Number(document.getElementById("maxPostsInput").value || 5),
            }),
        });
        renderJob(payload.job);
        appendLog(`Started job #${payload.job.id}.`, "success");
    }

    async function stopJob() {
        if (!state.activeJob) return;
        const payload = await fetchJson(`/api/jobs/${state.activeJob.id}/stop`, {
            method: "POST",
            body: "{}",
        });
        renderJob(payload.job);
        appendLog(`Stop requested for job #${payload.job.id}.`, "warning");
    }

    document.getElementById("openBrowserBtn").addEventListener("click", () => openBrowserSession().catch((error) => appendLog(error.message, "error")));
    document.getElementById("closeBrowserBtn").addEventListener("click", () => closeBrowserSession().catch((error) => appendLog(error.message, "error")));
    document.getElementById("saveSetsBtn").addEventListener("click", () => saveSets().catch((error) => appendLog(error.message, "error")));
    document.getElementById("startJobBtn").addEventListener("click", () => startJob().catch((error) => appendLog(error.message, "error")));
    document.getElementById("stopJobBtn").addEventListener("click", () => stopJob().catch((error) => appendLog(error.message, "error")));
    document.getElementById("refreshDataBtn").addEventListener("click", () => refreshSets().catch((error) => appendLog(error.message, "error")));
    document.getElementById("clearLogsBtn").addEventListener("click", () => { logStream.innerHTML = ""; });

    socket.on("status_update", (payload) => {
        if (payload.browser_session !== undefined) {
            if (payload.browser_session) {
                fetchJson(`/api/browser-sessions/${payload.browser_session.id}`)
                    .then((details) => renderSession(details.browser_session, details.viewer_url))
                    .catch(() => renderSession(payload.browser_session, null));
            } else {
                renderSession(null, null);
            }
        }
        if (payload.active_job !== undefined) {
            renderJob(payload.active_job);
        }
    });

    socket.on("browser_session_update", (payload) => {
        if (["stopped", "failed"].includes(payload.status)) {
            renderSession(null, null);
            return;
        }
        fetchJson(`/api/browser-sessions/${payload.id}`)
            .then((details) => renderSession(details.browser_session, details.viewer_url))
            .catch(() => renderSession(payload, null));
    });

    socket.on("job_update", (payload) => renderJob(payload));
    socket.on("job_log", (payload) => appendLog(payload.message, payload.level));

    renderSession(window.__INITIAL_STATE__.browserSession, window.__INITIAL_STATE__.viewerUrl);
    refreshSets().catch((error) => appendLog(error.message, "error"));
})();
