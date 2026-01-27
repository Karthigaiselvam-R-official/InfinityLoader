let scanTimeout;
let ws;
let currentUrl = "";
let selectedPath = "Default";
let currentData = null; // Store data for tab switching
let activeTab = 'video'; // Default tab

// Debounce logic for auto-scan
document.getElementById('urlInput').addEventListener('input', function (e) {
    const url = e.target.value.trim();
    // if (url === currentUrl) return; // Allow re-scan forcing

    clearTimeout(scanTimeout);

    // Hide previous content
    document.getElementById('contentArea').classList.add('hidden');
    document.getElementById('statusDock').classList.remove('active');

    // Show Showcase (Home) while scanning/typing
    document.getElementById('showcaseBox').classList.remove('hidden');

    // Basic YouTube check
    if (url === "") {
        // Reset to Home State
        document.getElementById('showcaseBox').classList.remove('hidden');
        document.getElementById('contentArea').classList.add('hidden');
        document.getElementById('scanLine').classList.remove('active');
        return;
    }

    if (url.match(/youtu.?be/)) {
        // Show scan line immediately
        document.getElementById('scanLine').classList.add('active');
        scanTimeout = setTimeout(() => {
            currentUrl = url;
            fetchInfo(url);
        }, 800);
    } else {
        document.getElementById('scanLine').classList.remove('active');
    }
});

function initWS() {
    if (ws && ws.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

    ws.onmessage = handleMessage;
    ws.onclose = () => { setTimeout(initWS, 1000); };
}

initWS();

async function choosePath() {
    const btn = document.getElementById('folderBtn');
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i>`;
    btn.classList.add('pulse');

    try {
        const res = await fetch('/api/choose-path');
        const data = await res.json();
        if (data.path && data.path !== "Default") {
            selectedPath = data.path;
            btn.style.color = "var(--secondary)";
            btn.title = `Saved to: ${selectedPath}`;
        }
    } catch (err) { console.error(err); }
    btn.classList.remove('pulse');
    btn.innerHTML = `<i class="fa-regular fa-folder-open"></i>`;
}

function fetchInfo(url) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        initWS();
        setTimeout(() => fetchInfo(url), 500);
        return;
    }
    // Ensure scan line is active
    document.getElementById('scanLine').classList.add('active');
    ws.send(JSON.stringify({ action: "fetch_info", url: url }));
}

function switchTab(type) {
    activeTab = type;

    // Update Buttons
    const btnVideo = document.getElementById('tabVideo');
    const btnAudio = document.getElementById('tabAudio');

    if (type === 'video') {
        btnVideo.classList.add('active');
        btnAudio.classList.remove('active');
    } else {
        btnVideo.classList.remove('active');
        btnAudio.classList.add('active');
    }

    // Re-render if we have data
    if (currentData) {
        renderGrid(currentData);
    }
}

function startDownload(formatId) {
    if (!ws) return;

    // Show Dock
    const dock = document.getElementById('statusDock');
    dock.classList.add('active');

    document.getElementById('statusText').innerText = "Initializing Download...";
    document.getElementById('progressFill').style.width = "0%";
    document.getElementById('dockIcon').className = "fa-solid fa-circle-notch dock-icon";
    document.getElementById('dockIcon').style.animation = "spin 2s linear infinite";

    ws.send(JSON.stringify({
        action: "download",
        url: currentUrl,
        format_id: formatId,
        download_path: selectedPath
    }));
}

function handleMessage(event) {
    const data = JSON.parse(event.data);

    // 1. Fetch Info Result
    if (data.status === "success" && data.formats) {
        document.getElementById('scanLine').classList.remove('active'); // Stop loader
        currentData = data; // Store global
        renderResults(data);
    }
    else if (data.status === "error") {
        document.getElementById('scanLine').classList.remove('active'); // Stop loader
        alert("Error: " + data.message);
    }

    // 2. Download Progress
    if (data.state === "processing") {
        document.getElementById('statusText').innerText = data.message;
        const percentMatch = data.message.match(/(\d+\.?\d*)%/);
        if (percentMatch) {
            document.getElementById('progressFill').style.width = percentMatch[1] + "%";
        }
    }
    else if (data.state === "converting") {
        document.getElementById('statusText').innerText = "Merging/Converting...";
        document.getElementById('progressFill').style.width = "100%";
    }
    else if (data.state === "completed") {
        document.getElementById('statusText').innerText = "Download Complete!";
        document.getElementById('dockIcon').className = "fa-solid fa-check-circle dock-icon";
        document.getElementById('dockIcon').style.animation = "none";
        document.getElementById('dockIcon').style.color = "#00ff88";

        setTimeout(() => {
            document.getElementById('statusDock').classList.remove('active');
            setTimeout(() => {
                document.getElementById('dockIcon').style.color = "";
            }, 500)
        }, 4000);
    }
}

function renderResults(data) {
    const area = document.getElementById('contentArea');
    area.classList.remove('hidden');
    document.getElementById('showcaseBox').classList.add('hidden'); // Hide showcase

    // Hero Data
    // Hero Data
    const heroMedia = document.getElementById('heroMedia');
    heroMedia.innerHTML = `
        <div class="hero-media-wrapper" onclick="loadVideoInHero('${data.id}')" title="Click to Play">
            <img id="thumbImg" src="${data.thumbnail}" alt="Thumbnail" class="hero-thumb">
            <div class="youtube-play-btn">
                <i class="fa-solid fa-play"></i>
            </div>
        </div>
    `;

    document.getElementById('videoTitle').innerText = data.title;

    // Improved Meta with Fallback Link
    const metaHtml = `
        <span id="videoAuthor"><i class="fa-solid fa-user"></i> ${data.author}</span>
        <span id="videoDuration"><i class="fa-regular fa-clock"></i> ${data.duration}</span>
        <a href="https://www.youtube.com/watch?v=${data.id}" target="_blank" class="fallback-link" title="Open in YouTube (If Player Error)">
             Open <i class="fa-solid fa-arrow-up-right-from-square"></i>
        </a>
    `;
    document.querySelector('.hero-meta').innerHTML = metaHtml;

    // Reset Tab to Video
    activeTab = 'video';
    document.getElementById('tabVideo').classList.add('active');
    document.getElementById('tabAudio').classList.remove('active');

    renderGrid(data);
}

// Load YouTube API
let apiLoaded = false;
function loadYouTubeAPI() {
    if (apiLoaded) return;
    const tag = document.createElement('script');
    tag.src = "https://www.youtube.com/iframe_api";
    const firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
    apiLoaded = true;
}

function loadVideoInHero(videoId) {
    const heroMedia = document.getElementById('heroMedia');
    heroMedia.innerHTML = '<div id="yt-player" class="video-embed"></div>';

    if (!window.YT || !window.YT.Player) {
        // If API not ready, wait for it
        window.onYouTubeIframeAPIReady = () => createPlayer(videoId);
        loadYouTubeAPI();
    } else {
        createPlayer(videoId);
    }
}

function createPlayer(videoId) {
    new YT.Player('yt-player', {
        height: '100%',
        width: '100%',
        videoId: videoId,
        playerVars: {
            'autoplay': 1,
            'rel': 0,
            'origin': window.location.origin
        },
        events: {
            'onReady': (event) => event.target.playVideo(),
            'onError': (event) => handlePlayerError(event, videoId)
        }
    });
}

function handlePlayerError(event, videoId) {
    // Error Codes: 100=Not Found, 101/150=Not Allowed in Embed
    if ([100, 101, 150, 153].includes(event.data)) {
        const heroMedia = document.getElementById('heroMedia');
        // Show Friendly UI
        heroMedia.innerHTML = `
            <div class="restriction-overlay">
                <i class="fa-solid fa-triangle-exclamation warning-icon"></i>
                <div class="msg">Playback Restricted on External Sites</div>
                <button class="redirect-btn" onclick="window.open('https://www.youtube.com/watch?v=${videoId}', '_blank')">
                    <i class="fa-solid fa-arrow-up-right-from-square"></i> Open in YouTube
                </button>
            </div>
        `;

        // Attempt Auto-Redirect (User Request: "it should redirect")
        // We use a small timeout to ensure the UI renders first so they aren't confused.
        setTimeout(() => {
            window.open(`https://www.youtube.com/watch?v=${videoId}`, '_blank');
        }, 500);
    }
}

function renderGrid(data) {
    const grid = document.getElementById('formatsGrid');
    grid.innerHTML = '';

    let delay = 0;

    // Choose list based on Tab
    let list = [];
    if (activeTab === 'video') {
        // Strict Filter: Ensure only video formats
        list = data.formats.video.filter(f => {
            // Check extension and quality
            const ext = (f.ext || "").toLowerCase();
            if (ext.includes('mp3') || ext.includes('m4a')) return false;
            if (f.quality === 'Audio Only') return false;

            // Ensure it has visual height
            const h = parseInt((f.quality || "0").replace('p', ''));
            if (h < 144 && ext !== 'mp4' && ext !== 'webm') return false;

            return true;
        });
    } else {
        // Process audio with Deduplication
        if (data.formats.audio) {
            const uniqueAudio = new Map();

            data.formats.audio.forEach(f => {
                // Key based on bitrate/note + size (approx)
                const key = (f.note || "0kbps") + (f.size || "NA");

                if (!uniqueAudio.has(key)) {
                    uniqueAudio.set(key, {
                        ...f,
                        quality: "Audio Only",
                        ext: f.ext === 'none' ? 'mp3' : f.ext,
                    });
                }
            });
            list = Array.from(uniqueAudio.values());
        }
    }

    if (list.length === 0) {
        grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 2rem;">No formats available for this category.</div>`;
        return;
    }

    list.forEach(f => {
        try {
            grid.innerHTML += createCard(f, activeTab, delay);
            delay += 0.05;
        } catch (e) { console.error("Card Error", e); }
    });
}

function createCard(f, type, delay) {
    const isVideo = type === 'video';
    const qualityStr = f.quality ? f.quality.replace('p', '') : '0';
    const qualityNum = parseInt(qualityStr) || 0;
    const is4K = qualityNum >= 2160;
    const isHD = qualityNum >= 1080;

    let badgeHtml = '';
    if (isVideo) {
        if (is4K) badgeHtml = `<div class="badge badge-4k">4K ULTRA</div>`;
        else if (isHD) badgeHtml = `<div class="badge badge-hd">HD ${qualityStr}p</div>`;
        else badgeHtml = `<div class="badge badge-sd">${qualityStr}p</div>`;
    } else {
        badgeHtml = `<div class="badge badge-sd">AUDIO</div>`;
    }

    const title = isVideo ? `${f.quality}` : `Best Audio`;
    const ext = f.ext || 'MP3';
    let details = "";
    if (isVideo) {
        details = ext.toUpperCase();
    } else {
        details = (f.note || 'High Quality').replace('kbps', ' Kbps');
    }

    const size = (f.size && f.size !== "N/A") ? f.size : "Variable Size";

    let downloadId = f.format_id;
    if (!isVideo) {
        // Use best_audio logic for consistency
        downloadId = 'best_audio';
    }

    const style = `animation-delay: ${delay}s`;

    return `
    <div class="format-card" style="${style}">
        ${badgeHtml}
        <div class="card-res">${title}</div>
        <div class="card-details">
            <span>${details}</span>
            <span>${size}</span>
        </div>
        <button class="download-btn" onclick="startDownload('${downloadId}')">
            DOWNLOAD
        </button>
    </div>
    `;
}

async function handlePaste() {
    try {
        const text = await navigator.clipboard.readText();
        if (text) {
            const input = document.getElementById('urlInput');
            input.value = text.trim(); // Replace content entirely
            input.dispatchEvent(new Event('input')); // Trigger scan
        }
    } catch (err) {
        console.error('Failed to read clipboard:', err);
    }
}