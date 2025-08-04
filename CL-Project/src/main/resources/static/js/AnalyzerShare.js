// AnalyzerShare.js

window.AnalyzerShare = window.AnalyzerShare || {};

// =================================================================================
// 1. 전역 변수 선언 (Global Variables)
// =================================================================================

AnalyzerShare.cognitiveLoadChartInstance = {}; // Chart.js 인스턴스 관리 객체 (캔버스 ID별)
AnalyzerShare.globalCognitiveLoadData = {
  labels: [],
  instantaneousLoadData: [],
  cumulativeLoadData: []
};

// =================================================================================
// 2. 핵심 기능 함수 (Core Logic Functions)
// =================================================================================

/**
 * 동영상 파일을 서버에 업로드합니다.
 * @param {File|FileList|Array<File>} files - 업로드할 파일
 * @returns {Promise<Object>} A promise that resolves with the upload response data.
 */
AnalyzerShare.uploadVideos = function(files) {
  

  // Check if user is logged in
  const token = getToken();
  if (!token) {
    alert("Please log in to upload a video.");
    return Promise.reject(new Error("User not logged in."));
  }

  const fileArr = Array.isArray(files) ? files : files instanceof FileList ? Array.from(files) : [files];

  if (!fileArr.length) {
    alert("업로드할 파일이 없습니다");
    return Promise.reject(new Error("No files selected for upload."));
  }

  const multi = fileArr.length > 1;
  const field = multi ? "files" : "file";
  const form = new FormData();
  fileArr.forEach(f => form.append(field, f));

  const url = multi ? "/api/videos/batch" : "/api/videos/upload";
  

  const fetchOptions = { 
    method: "POST", 
    body: form,
    headers: {
      'Authorization': `Bearer ${token}`
    }
  };

  return fetch(url, fetchOptions)
    .then(res => {
      if (res.ok) {
        return res.json();
      }
      return res.text().then(text => {
        throw new Error(`${res.status} ${res.statusText}: ${text}`);
      });
    })
    .then(data => {
      
      const jobId = Array.isArray(data) ? (data.length > 0 ? data[0].jobId : null) : data.jobId;
      if (jobId) {
        saveJobId(jobId); // Use the function from session.js
      }
      return data;
    })
    .catch(err => {
      
      alert("업로드 실패: " + err.message);
      throw err;
    });
}

/**
 * 주기적으로 작업 상태를 폴링합니다.
 * @param {string} jobId - 분석 Job ID
 * @param {Function} onCompleted - 작업 완료 시 ���출될 콜백 함수
 * @param {Function} onFailed - 작업 실패 시 호출될 콜백 함수
 * @param {Function} onProgress - 작업 진행 중 호출될 콜백 함수 (선택 사항)
 */
AnalyzerShare.pollJobStatus = function(jobId, onCompleted, onFailed, onProgress = null) {
  const token = getToken();
  if (!token) {
    
    onFailed(jobId, "No token found.");
    return;
  }

  const statusDisplay = document.getElementById('jobStatusDisplay');
  if (statusDisplay) {
    statusDisplay.innerText = `Job ${jobId}: ANALYSIS_STARTED...`;
    statusDisplay.style.display = 'block';
  }

  const pollInterval = setInterval(async () => {
    try {
      const response = await fetch(`/api/jobs/${jobId}/status`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) {
        if (response.status >= 400 && response.status < 500) {
            throw new Error(`Client error: ${response.status}`);
        }
        const errorData = await response.json().catch(() => ({ errorMessage: 'Failed to parse error response.' }));
        throw new Error(errorData.errorMessage || `Server error: ${response.status}`);
      }
      const job = await response.json();

      if (statusDisplay) {
        statusDisplay.innerText = `Job ${job.jobId}: ${job.status}`;
      }

      if (onProgress) {
        onProgress(job.status);
      }

      if (job.status === 'COMPLETED') {
        clearInterval(pollInterval);
        if (statusDisplay) statusDisplay.style.display = 'none';
        onCompleted(jobId);
      } else if (job.status === 'FAILED') {
        clearInterval(pollInterval);
        if (statusDisplay) statusDisplay.style.display = 'none';
        onFailed(jobId, job.errorMessage);
      }
    } catch (error) {
      
      clearInterval(pollInterval);
      if (statusDisplay) {
        statusDisplay.innerText = `Job ${jobId}: POLLING_FAILED - ${error.message}`;
      }
      onFailed(jobId, error.message);
    }
  }, 3000);
}

// =================================================================================
// 3. UI 렌더링 및 조작 함수 (UI Rendering & Manipulation)
// =================================================================================

/**
 * 로딩 상태를 표시합니다.
 * @param {string} elementId - 로딩 오버레이를 표시할 요소의 ID (예: 'dualGraphCanvas', 'zettelGraph')
 */
AnalyzerShare.showLoadingState = function(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        const container = element.closest('.graph-container, .graph-canvas-wrapper');
        if (container) {
            container.classList.add('blur-active');
            const overlay = container.querySelector('.graph-loading-overlay');
            if (overlay) {
                overlay.style.display = 'flex';
            }
        }
    }
}

/**
 * 로딩 상태를 숨깁니다.
 * @param {string} elementId - 로딩 오버레이를 숨길 요소의 ID (예: 'dualGraphCanvas', 'zettelGraph')
 */
AnalyzerShare.hideLoadingState = function(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        const container = element.closest('.graph-container, .graph-canvas-wrapper');
        if (container) {
            container.classList.remove('blur-active');
            const overlay = container.querySelector('.graph-loading-overlay');
            if (overlay) {
                overlay.style.display = 'none';
            }
        }
    }
}

/**
 * 인지 부하 그래프를 초기화하거나 다시 그립니다.
 * @param {string[]} labels - 그래프의 X축 레이블 (타임스탬프)
 * @param {number[]} loadData - 인지 부하 데이터 배열
 * @param {string} type - 'cumulative' 또는 'instantaneous'
 * @param {string} canvasId - 그래프를 그릴 캔버스 ID
 */
AnalyzerShare.initCognitiveLoadGraph = function(labels, loadData, type = 'cumulative', canvasId, options = {}) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) {
    
    return null;
  }

  if (!labels || !labels.length || !loadData || !loadData.length) {
    
    return null;
  }

  if (AnalyzerShare.cognitiveLoadChartInstance[canvasId]) {
    AnalyzerShare.cognitiveLoadChartInstance[canvasId].destroy();
  }
  
  const { labels: denseLabels, loadData: denseData } = densifyLabelsAndDataCubic(labels, loadData);

  const chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: denseLabels,
      datasets: [{
        data: denseData,
        label: `${type === 'cumulative' ? 'Cumulative' : 'Instantaneous'} Cognitive Load`,
        borderColor: "#fff",
        borderWidth: 2,
        tension: 0.6,
		cubicInterpolationMode: 'monotone',
        pointRadius: 0,
        fill: true,
        backgroundColor: "rgba(255,255,255,0.15)",
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          ticks: {
            color: 'white',
            callback: function(value, index, ticks) {
              return AnalyzerShare.formatTime(value); // value is in seconds
            }
          }
        },
        y: { ticks: { color: 'white' } }
      },
      plugins: {
        legend: { display: true, labels: { color: 'white' } },
        tooltip: { // Add this block
          callbacks: {
            title: function(tooltipItems) {
              // tooltipItems[0].label contains the x-axis label (time in seconds)
              const seconds = parseFloat(tooltipItems[0].label);
              return AnalyzerShare.formatTime(seconds);
            },
            label: function(tooltipItem) {
              // tooltipItem.dataset.label is like "Cumulative Cognitive Load"
              // tooltipItem.formattedValue is the y-axis value
              return `${tooltipItem.dataset.label}: ${tooltipItem.formattedValue}`;
            }
          }
        },
        // Pass custom data to be accessible in event handlers
        customOptions: options
      },
      interaction: {
        mode: 'index',
        intersect: false
      },
      onClick: function(event, elements) { // Using regular function to get chart instance as 'this'
        if (elements.length > 0) {
          const chartElement = elements[0];
          const index = chartElement.index;
          const seconds = this.data.labels[index]; // timeLabel is already in seconds

          let videoPlayerElement = null;
          if (canvasId === 'dualGraphCanvasOriginal') {
            videoPlayerElement = document.querySelector('#originalVideoPlayer .video-player-element');
          } else if (canvasId === 'dualGraphCanvasEdited' || canvasId === 'cognitiveLoadModalCanvas') {
            videoPlayerElement = document.querySelector('#editedVideoPlayer .video-player-element');
          } else if (canvasId === 'dualGraphCanvas') {
            videoPlayerElement = document.querySelector('#videoPlayer .video-player-element');
          }

          if (videoPlayerElement) {
            const customOptions = this.config.options.plugins.customOptions;
            if (customOptions.segment && typeof customOptions.segment.start === 'number') {
              videoPlayerElement.currentTime = customOptions.segment.start + seconds;
            } else {
              videoPlayerElement.currentTime = seconds;
            }
          }
        }
      }
    },
  });

  AnalyzerShare.cognitiveLoadChartInstance[canvasId] = chart;
  return chart;
}

/**
 * 표시할 인지 부하 데이터 유형(누적/순간)에 따라 그래프를 업데이트합니다.
 * @param {string} type - 'cumulative' 또는 'instantaneous'
 * @param {string} canvasId - 업데이트할 캔버스 ID
 * @param {object} sourceData - 그래프를 그릴 원본 데이터 (labels, instantaneousLoadData, cumulativeLoadData 포함)
 */
AnalyzerShare.updateCognitiveLoadGraph = function(type, canvasId, sourceData, options = {}) {
  if (!sourceData) {
      console.warn(`No source data available for canvas ${canvasId}`);
      return;
  }

  const data = (type === 'instantaneous') ? sourceData.instantaneousLoadData : sourceData.cumulativeLoadData;
  // Use labelsInSeconds if available, otherwise fall back to labels (which should be numbers now)
  const labelsToUse = sourceData.labelsInSeconds || sourceData.labels;
  AnalyzerShare.initCognitiveLoadGraph(labelsToUse, data, type, canvasId, options);
}

/**
 * 누적/순간 인지 부하 버튼의 활성 상태를 설정합니다.
 * @param {HTMLElement} cumulativeBtn - 누적 버튼 요소
 * @param {HTMLElement} instantaneousBtn - 순간 버튼 요소
 * @param {string} activeType - 'cumulative' 또는 'instantaneous'
 */
AnalyzerShare.setActiveButton = function(cumulativeBtn, instantaneousBtn, activeType) {
  cumulativeBtn.classList.remove('active');
  instantaneousBtn.classList.remove('active');
  if (activeType === 'cumulative') {
    cumulativeBtn.classList.add('active');
  } else {
    instantaneousBtn.classList.add('active');
  }
}

/**
 * 비디오 플레이어 UI를 초기화하고 이벤트 리스너를 설정합니다.
 * @param {string} playerId - 초기화할 비디��� 플레이어의 컨테이너 ID
 */
AnalyzerShare.initializeVideoPlayer = function(playerId) {
  const playerContainer = document.getElementById(playerId);
  
  if (!playerContainer) {
    
    return;
  }

  const video = playerContainer.querySelector('.video-player-element');
  const controlsContainer = playerContainer.querySelector('.video-controls');
  const playPauseBtn = playerContainer.querySelector('.play-pause-btn');
  const timeline = playerContainer.querySelector('.timeline');
  const progressBarFill = playerContainer.querySelector('.progress');
  const timeDisplay = playerContainer.querySelector('.time-display');
  const playIcon = playPauseBtn ? playPauseBtn.querySelector('.play-icon') : null;
  const pauseIcon = playPauseBtn ? playPauseBtn.querySelector('.pause-icon') : null;
  const volumeBtn = playerContainer.querySelector(".volume-btn");
  const volumeSlider = playerContainer.querySelector(".volume-slider");
  const fullscreenBtn = playerContainer.querySelector(".fullscreen-btn");

  // Ensure all required elements are present
  if (!video) {
    

    return;
  }
  if (!controlsContainer) {
    console.error(`Player ${playerId} is missing essential component: .video-controls`);

    return;
  }
  if (!playPauseBtn) {
    console.error(`Player ${playerId} is missing essential component: .play-pause-btn`);

    return;
  }
  if (!timeline) {
    console.error(`Player ${playerId} is missing essential component: .timeline`);

    return;
  }

  

  let inactivityTimer;

  const showControls = () => {
    controlsContainer.classList.remove('controls-hidden');
  };

  const hideControls = () => {
    if (video.paused || document.activeElement === volumeSlider) return;
    controlsContainer.classList.add('controls-hidden');
  };

  const startHideTimer = () => {
    clearTimeout(inactivityTimer);
    inactivityTimer = setTimeout(hideControls, 2500);
  };

  const cancelHideTimer = () => {
    clearTimeout(inactivityTimer);
  };

  playerContainer.addEventListener('mouseenter', () => {
    showControls();
    startHideTimer();
  });

  playerContainer.addEventListener('mousemove', () => {
    showControls();
    startHideTimer();
  });

  playerContainer.addEventListener('mouseleave', () => {
    startHideTimer();
  });

  video.addEventListener('click', () => video.paused ? video.play() : video.pause());
  controlsContainer.addEventListener('click', (e) => e.stopPropagation());
  playPauseBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    if (video.paused) video.play();
    else video.pause();
  });

  video.addEventListener('play', () => {
    if (playIcon) playIcon.style.display = 'none';
    if (pauseIcon) pauseIcon.style.display = 'block';
    startHideTimer();
  });

  video.addEventListener('loadedmetadata', () => {
    const segment = video._segment;
    const duration = segment ? segment.end - segment.start : video.duration;
    if (timeDisplay) {
      timeDisplay.textContent = `00:00 / ${AnalyzerShare.formatTime(duration)}`;
    }
  });

  video.addEventListener('pause', () => {
    if (playIcon) playIcon.style.display = 'block';
    if (pauseIcon) pauseIcon.style.display = 'none';
    cancelHideTimer();
    showControls();
  });

  video.addEventListener('timeupdate', () => {
    const segment = video._segment;
    let displayTime, duration, progress;

    if (segment) {
      const elapsedTime = video.currentTime - segment.start;
      duration = segment.end - segment.start;
      displayTime = elapsedTime;
      progress = duration > 0 ? (elapsedTime / duration) * 100 : 0;

      if (video.currentTime >= segment.end) {
        video.pause();
        progress = 100;
        displayTime = duration;
      }
    } else {
      duration = video.duration;
      displayTime = video.currentTime;
      if (!duration) return;
      progress = (video.currentTime / duration) * 100;
    }

    if (progressBarFill) progressBarFill.style.width = `${progress}%`;
    if (timeDisplay) timeDisplay.textContent = `${AnalyzerShare.formatTime(displayTime)} / ${AnalyzerShare.formatTime(duration)}`;
  });

  timeline.addEventListener('click', (e) => {
    const timelineWidth = timeline.clientWidth;
    const clickX = e.offsetX;
    const segment = video._segment;

    if (segment) {
      const segmentDuration = segment.end - segment.start;
      if (segmentDuration > 0) video.currentTime = segment.start + (clickX / timelineWidth) * segmentDuration;
    } else {
      if (!video.duration) return;
      video.currentTime = (clickX / timelineWidth) * video.duration;
    }
  });

  if (volumeBtn && volumeSlider) {
    const toggleMute = () => video.muted = !video.muted;
    const setVolume = () => video.volume = volumeSlider.value;
    video.addEventListener("volumechange", () => {
      const volumeHighIcon = volumeBtn ? volumeBtn.querySelector(".volume-high-icon") : null;
      const volumeMuteIcon = volumeBtn ? volumeBtn.querySelector(".volume-mute-icon") : null;
      if (!volumeHighIcon || !volumeMuteIcon) return;
      volumeHighIcon.style.display = (video.muted || video.volume === 0) ? "none" : "block";
      volumeMuteIcon.style.display = (video.muted || video.volume === 0) ? "block" : "none";
    });
    volumeBtn.addEventListener("click", toggleMute);
    volumeSlider.addEventListener("input", setVolume);
  }

  if (fullscreenBtn) {
    fullscreenBtn.addEventListener("click", () => {
      if (!document.fullscreenElement) {
        
        playerContainer.requestFullscreen().catch(err => alert(`Error: ${err.message}`));
      } else {
        
        document.exitFullscreen();
      }
    });
  }
}

// =================================================================================
// 4. 유틸리티 및 보조 함수 (Utility & Helper Functions)
// =================================================================================

AnalyzerShare.formatTime = function(timeInSeconds) {
    if (isNaN(timeInSeconds) || timeInSeconds < 0) return "00:00";
    const minutes = Math.floor(timeInSeconds / 60);
    const seconds = Math.floor(timeInSeconds % 60);
    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

/**
 * Loads a specific segment into a video player.
 * @param {string} playerId - The ID of the video player container.
 * @param {string} src - The source URL of the video.
 * @param {object} segment - The segment object with start and end times.
 */
AnalyzerShare.loadVideoSegment = function(playerId, src, segment) {
  const playerContainer = document.getElementById(playerId);
  if (!playerContainer) return;
  const video = playerContainer.querySelector('.video-player-element');

  video._segment = segment; // Attach segment data to the video element
  video.src = src;

  video.onloadedmetadata = () => {
    video.currentTime = segment.start;
    video.play().catch(err => {
      
      alert("Edited video failed to auto-play. Please play it manually.");
    });
    video.onloadedmetadata = null; // Handler only needed once
  };

  video.load();
}

// =================================================================================
// 5. 1초단위 보간함수(chart함수 전처리용)
// =================================================================================
function densifyLabelsAndDataCubic(labels, loadData) {
  const n = labels.length;
  const x = labels.map(lbl => lbl); // lbl is already in seconds
  const y = loadData.slice();

  // 자연 스플라인 2차 도함수 계산
  const y2 = new Array(n).fill(0);
  const u  = new Array(n).fill(0);
  for (let i = 1; i < n - 1; i++) {
    const sig = (x[i] - x[i-1]) / (x[i+1] - x[i-1]);
    const p   = sig * y2[i-1] + 2;
    y2[i] = (sig - 1) / p;
    u[i]  = (6 * (
               (y[i+1] - y[i]) / (x[i+1] - x[i])
             - (y[i]   - y[i-1]) / (x[i]   - x[i-1])
             ) / (x[i+1] - x[i-1])
            - sig * u[i-1]
          ) / p;
  }
  for (let k = n - 2; k >= 0; k--) {
    y2[k] = y2[k] * y2[k+1] + u[k];
  }

  // 1초 단위 샘플링 + 보간 + 클램프
  const tStart = x[0], tEnd = x[n-1];
  const outLabels = [];
  const outData   = [];

  for (let t = tStart; t <= tEnd; t++) {
    let i = 0;
    while (i < n - 2 && t > x[i+1]) i++;
    const h = x[i+1] - x[i];
    const a = (x[i+1] - t) / h;
    const b = (t - x[i])     / h;

    // 자연 3차 스플라인 보간
    let y_t = a * y[i]
            + b * y[i+1]
            + ((a*a*a - a) * y2[i]
             + (b*b*b - b) * y2[i+1]) * (h*h) / 6;

    // 음수 클램프 및 최대값 클램프
    y_t = Math.max(0, y_t);
    y_t = Math.min(1.0, y_t);

    // 라벨 및 데이터 저장
    outLabels.push(t); // Push seconds directly
    outData.push(Number(y_t.toFixed(2)));
  }

  return { labels: outLabels, loadData: outData };
}