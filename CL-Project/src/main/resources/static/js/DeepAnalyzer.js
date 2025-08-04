// =================================================================================
// 1. 전역 변수 선언 (Global Variables)
// =================================================================================

let editStart = null; // 편집 시작 시간 저장
let latestThumbnailDataURL = null; // 마지막으로 캡처된 썸네일 데이터 URL
let currentPage = 0; // 편집 썸네일 목록의 현재 페이지
const pageSize = 9; // 페이지 당 썸네일 수
const editedSegments = []; // 편집된 영상 조각(segment)들의 배열
let dropArea, videoInput, editButtons; // DOM 요소 참조
let editedPlayerInitialized = false;
let currentJobId = null; // 원본 영상 분석 요청의 Job ID


// 현재 보고 있는 편집된 영상 조각의 인지 부하 데이터
let editedSegmentCognitiveLoadData = null;


// =================================================================================
// 2. 핵심 기능 함수 (Core Logic Functions)
// =================================================================================

/**
 * 드래그 앤 드롭 영역을 비활성화하고 스타일을 변경합니다.
 */
function disableDropArea() {
  if (dropArea) {
    dropArea.removeEventListener("dragover", onDragOver);
    dropArea.removeEventListener("drop", onDropHandler);
    dropArea.removeEventListener("click", onClickDropArea);
    dropArea.classList.add("disabled"); // 비활성화 스타일 추가
  }
}

/**
 * 드래그 앤 드롭 영역을 활성화하고 스타일을 변경합니다.
 */
function enableDropArea() {
  if (dropArea) {
    dropArea.addEventListener("dragover", onDragOver);
    dropArea.addEventListener("drop", onDropHandler);
    dropArea.addEventListener("click", onClickDropArea);
    dropArea.classList.remove("disabled"); // 비활성화 스타일 제거
  }
}

/**
 * 드래그 오버 이벤트 핸들러
 */
function onDragOver(e) {
  e.preventDefault();
  e.stopPropagation();
  e.dataTransfer.dropEffect = "copy";
}

/**
 * 드롭 영역 클릭 이벤트 핸들러
 */
function onClickDropArea() {
  videoInput.click();
}

/**
 * 파일 입력 변경 이벤트 핸들러
 */
function onFileInputChange(e) {
  const f = e.target.files[0];
  if (f) {
    handleVideoFile(f);
  }
}

/**
 * 비디오 파일을 처리하고 업로드 및 분석을 시작합니다.
 * @param {File} file - 처리할 비디오 파일
 */
function handleVideoFile(file) {
  if (file && file.type.startsWith("video/")) {
    const originalVideo = document.querySelector('#originalVideoPlayer .video-player-element');
    originalVideo.src = URL.createObjectURL(file);
    originalVideo.load();
    AnalyzerShare.showLoadingState('dualGraphCanvasOriginal'); // Show loading overlay for original graph
    AnalyzerShare.uploadVideos(file)
      .then(data => {
        let jobId = Array.isArray(data) ? (data.length > 0 ? data[0].jobId : null) : data.jobId;
        if (jobId) {
          currentJobId = jobId;
          alert("업로드 완료! 분석을 시작합니다. Job ID: " + jobId);
          AnalyzerShare.pollJobStatus(
            jobId,
            (completedJobId) => { // onCompleted 콜백
              alert(`Job ${completedJobId} finished successfully!`);
              fetchCognitiveLoadData(completedJobId);
              AnalyzerShare.hideLoadingState('dualGraphCanvasOriginal'); // 성공 시 로딩 상태 숨김
            },
            (failedJobId, errorMessage) => { // onFailed 콜백
              alert(`Job ${failedJobId} failed: ${errorMessage}`);
              AnalyzerShare.hideLoadingState('dualGraphCanvasOriginal'); // 실패 시 로딩 상태 숨김
            }
          );
        } else {
          alert("업로드에 성공했지만 Job ID를 찾지 못했습니다.");
          AnalyzerShare.hideLoadingState('dualGraphCanvasOriginal');
        }
      })
      .catch(err => {
        // AnalyzerShare.uploadVideos에서 이미 alert와 console.error를 처리하므로 여기서는 추가 처리 불필요
        AnalyzerShare.hideLoadingState('dualGraphCanvasOriginal'); // 업로드 실패 시 로딩 상태 숨김
      });
        if (editButtons) editButtons.style.display = "flex";
        const uploadHint = document.getElementById("uploadHint");
        if (uploadHint) uploadHint.style.display = "none";
        const videoContentWrapper = document.querySelector(".video-content-wrapper");
        if (videoContentWrapper) videoContentWrapper.style.display = "block";
        disableDropArea();
        AnalyzerShare.initializeVideoPlayer('originalVideoPlayer');
  }
}

/**
 * "MM:SS" 형식의 시간 문자열을 초 단위 숫자로 변환합니다.
 * @param {string} timeStr - 변환할 시간 문자열
 * @returns {number} - 초 단위 시간
 */
function parseTimeToSeconds(timeStr) {
    if (typeof timeStr !== 'string') return NaN;
    const parts = timeStr.split(':');
    if (parts.length !== 2) return NaN;
    const minutes = parseInt(parts[0], 10);
    const seconds = parseInt(parts[1], 10);
    if (isNaN(minutes) || isNaN(seconds)) return NaN;
    return minutes * 60 + seconds;
}

/**
 * 정렬된 배열에서 이진 탐색으로 target보다 크거나 같은 첫 번째 요소의 인덱스를 찾습니다. (lower_bound)
 * @param {number[]} sortedArr - 정렬된 숫자 배열
 * @param {number} target - 찾고자 하는 값
 * @returns {number} - target보다 크거나 같은 첫 번째 요소의 인덱스
 */
function findLowerBoundIndex(sortedArr, target) {
    let low = 0;
    let high = sortedArr.length;
    while (low < high) {
        const mid = Math.floor(low + (high - low) / 2);
        if (sortedArr[mid] < target) {
            low = mid + 1;
        } else {
            high = mid;
        }
    }
    return low;
}

/**
 * 정렬된 배열에서 이진 탐색으로 target보다 큰 첫 번째 요소의 인덱스를 찾습니다. (upper_bound)
 * @param {number[]} sortedArr - 정렬된 숫자 배열
 * @param {number} target - 찾고자 하는 값
 * @returns {number} - target보다 큰 첫 번째 요소의 인덱스
 */
function findUpperBoundIndex(sortedArr, target) {
    let low = 0;
    let high = sortedArr.length;
    while (low < high) {
        const mid = Math.floor(low + (high - low) / 2);
        if (sortedArr[mid] > target) {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    return low;
}


/**
 * Job ID를 사용해 원본 영상의 인지 부하 데이터를 서버에서 가져옵니다.
 * 데이터 로드 시 레이블을 초 단위로 변환하여 검색 효율을 높입니다.
 * @param {string} jobId - 분석 Job ID
 */
async function fetchCognitiveLoadData(jobId) {
  try {
    const response = await fetch(`/api/jobs/${jobId}/cognitive-load`);
    if (!response.ok) throw new Error(`CL fetch failed: ${response.statusText}`);
    const data = await response.json();

    // 레이블을 초 단위로 미리 변환하여 저장
    const labelsInSeconds = data.labels.map(parseTimeToSeconds);

    AnalyzerShare.globalCognitiveLoadData = {
        labels: data.labels,
        labelsInSeconds: labelsInSeconds, // 검색용 초 단위 레이블
        instantaneousLoadData: data.instantaneousLoadData,
        cumulativeLoadData: data.cumulativeLoadData
    };

    AnalyzerShare.initCognitiveLoadGraph(AnalyzerShare.globalCognitiveLoadData.labelsInSeconds, AnalyzerShare.globalCognitiveLoadData.cumulativeLoadData, 'cumulative', 'dualGraphCanvasOriginal');
    AnalyzerShare.hideLoadingState('dualGraphCanvasOriginal');

    // 그래프 컨테이너를 명시적으로 보이도록 설정
    const graphCanvasOriginal = document.getElementById('dualGraphCanvasOriginal');
    if (graphCanvasOriginal) {
      const graphContainerOriginal = graphCanvasOriginal.closest('.graph-container, .graph-canvas-wrapper');
      if (graphContainerOriginal) {
        graphContainerOriginal.style.display = 'block'; // 또는 'flex' (CSS에 따라)
      }
    }

    const showCumulativeBtnOriginal = document.getElementById("showCumulativeBtnOriginal");
    const showInstantaneousBtnOriginal = document.getElementById("showInstantaneousBtnOriginal");
    if (showCumulativeBtnOriginal && showInstantaneousBtnOriginal) {
      AnalyzerShare.setActiveButton(showCumulativeBtnOriginal, showInstantaneousBtnOriginal, 'cumulative');
    }
  } catch (err) {
    
    alert("Cognitive Load 데이터를 불러오지 못했습니다: " + err.message);
    AnalyzerShare.hideLoadingState('dualGraphCanvasOriginal');
  }
}


// =================================================================================
// 3. UI 렌더링 및 조작 함수 (UI Rendering & Manipulation)
// =================================================================================





/**
 * 편집된 영상 썸네일 목록의 현재 페이지를 렌더링합니다.
 */
function renderPage() {
  const grid = document.getElementById("previewGrid");
  grid.innerHTML = ""; // 초기화

  const startIdx = currentPage * pageSize;
  const endIdx = Math.min(startIdx + pageSize, editedSegments.length);
  const pageItems = editedSegments.slice(startIdx, endIdx);

  pageItems.forEach((segment, index) => {
    const preview = document.createElement("div");
    preview.className = "preview";

    const img = document.createElement("img");
    img.src = segment.thumbnail;
    img.alt = `편집: ${segment.start.toFixed(1)}~${segment.end.toFixed(1)}`;
    preview.appendChild(img);

    const label = document.createElement("span");
    label.className = "label";
    label.innerText = `Edit ${startIdx + index + 1}`;
    preview.appendChild(label);

    // 클릭 시 독립적인 영상처럼 재생 및 UI 구성
    preview.addEventListener("click", () => {
      
      const originalVideo = document.querySelector("#originalVideoPlayer .video-player-element");
      const editedPlayerContainer = document.getElementById("editedPlayerContainer");
      const previewGrid = document.getElementById("previewGrid");
      const pager = document.getElementById("pager");
      const closeBtn = document.getElementById("closePlayer");

      if (!editedPlayerInitialized) {
        AnalyzerShare.initializeVideoPlayer('editedVideoPlayer');
        editedPlayerInitialized = true;
      }

      // UI 상태 변경
      editedPlayerContainer.style.display = "block";
      closeBtn.style.display = "block";
      previewGrid.style.display = "none";
      pager.style.display = "none";
      

      // --- 비디오 설정 및 재생 ---
      // AnalyzerShare에 세그먼트 정보를 전달하여 플레이어 설정을 위임합니다.
      AnalyzerShare.loadVideoSegment('editedVideoPlayer', originalVideo.src, segment);

      // --- 분석 데이터 처리 ---
      // 썸네일 클릭 시 실행될 분석 및 그래프 렌더링 함수
      const analyzeAndRenderSegment = async () => {
        AnalyzerShare.showLoadingState('dualGraphCanvasEdited');
        try {
          if (!currentJobId) {
            throw new Error("원본 영상 분석 Job ID가 없습니다. 먼저 원본 영상을 분석해주세요.");
          }

          const response = await fetch('/api/videos/analyze-segment', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${getToken()}` // Add Authorization header
            },
            body: JSON.stringify({
              jobId: currentJobId,
              start: segment.start,
              end: segment.end
            }),
          });
          

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: response.statusText }));
            throw new Error(`세그먼트 분석 실패: ${errorData.error || 'Unknown error'}`);
          }

          const segmentData = await response.json();

          if (segmentData && segmentData.labels && segmentData.labels.length > 0) {
            
            editedSegmentCognitiveLoadData = segmentData; // 전역 변수 업데이트
            editedSegmentCognitiveLoadData.labelsInSeconds = segmentData.labels.map(parseTimeToSeconds); // 초 단위 레이블 추가
            currentPlayingSegment = segment; // 현재 재생 중인 세그먼트 정보 저장

            // 그래프 초기화 (세그먼트 정보 전달)
            AnalyzerShare.initCognitiveLoadGraph(
              editedSegmentCognitiveLoadData.labelsInSeconds,
              editedSegmentCognitiveLoadData.cumulativeLoadData,
              'cumulative',
              'dualGraphCanvasEdited',
              { segment: currentPlayingSegment }
            );

            // 버튼 상태 활성화
            const showCumulativeBtnEdited = document.getElementById("showCumulativeBtnEdited");
            const showInstantaneousBtnEdited = document.getElementById("showInstantaneousBtnEdited");
            AnalyzerShare.setActiveButton(showCumulativeBtnEdited, showInstantaneousBtnEdited, 'cumulative');

          } else {
            
            alert("해당 편집 구간에 대한 분석 데이터를 찾을 수 없습니다.");
            AnalyzerShare.initCognitiveLoadGraph([], [], 'cumulative', 'dualGraphCanvasEdited');
          }
        } catch (err) {
          
          alert(err.message);
          AnalyzerShare.initCognitiveLoadGraph([], [], 'cumulative', 'dualGraphCanvasEdited'); // 오류 시 그래프 비움
        } finally {
          AnalyzerShare.hideLoadingState('dualGraphCanvasEdited');
        }
      };

      // 함수 호출
      analyzeAndRenderSegment();
    });

    grid.appendChild(preview);
  });

  updateDots();
}

/**
 * 새로운 편집 조각(segment)을 썸네일 패널에 추가합니다.
 * @param {object} segment - 추가할 세그먼트 정보
 */
function addThumbnailToPanel(segment) {
  editedSegments.push(segment);
  renderPage();
}

/**
 * 페이징 컨트롤의 점(dot)들을 업데이트합니다.
 */
function updateDots() {
  const dotContainer = document.querySelector(".pager-dots");
  const pager = document.getElementById("pager");

  dotContainer.innerHTML = "";

  let totalPages = Math.ceil(editedSegments.length / pageSize);
  if (editedSegments.length === 0) { // If no segments, show 1 page
    totalPages = 1;
    currentPage = 0; // Ensure current page is 0
  }

  if (pager) pager.style.display = "flex"; // Always show the pager

  for (let i = 0; i < totalPages; i++) {
    const dot = document.createElement("span");
    dot.className = "dot" + (i === currentPage ? " active" : "");
    dotContainer.appendChild(dot);
  }
}








// =================================================================================
// 4. 유틸리티 및 보조 함수 (Utility & Helper Functions)
// =================================================================================



/**
 * 비디오의 현재 프레임을 캡처하여 썸네일로 만듭니다.
 * @param {HTMLVideoElement} video - 캡처할 비디오 요소
 */
function captureThumbnail(video) {
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  latestThumbnailDataURL = canvas.toDataURL("image/png");
}






// =================================================================================
// 5. 이벤트 핸들러 및 초기화 (Event Handlers & Initialization)
// =================================================================================

// --- Drag & Drop Handlers ---
function onDropHandler(e) {
  e.preventDefault();
  const f = e.dataTransfer.files[0];
  handleVideoFile(f);
}


document.addEventListener("DOMContentLoaded", () => {
  dropArea = document.getElementById("videoDrop");
  videoInput = document.getElementById("videoInput");
  editButtons = document.getElementById("editButtons");

  if (dropArea) {
    dropArea.addEventListener("dragover", onDragOver);
    dropArea.addEventListener("drop", onDropHandler);
    dropArea.addEventListener("click", onClickDropArea);
  }

  if (videoInput) {
    videoInput.addEventListener("change", onFileInputChange);
  }

  const closePlayerBtn = document.getElementById("closePlayer");
  if (closePlayerBtn) {
    closePlayerBtn.addEventListener("click", () => {
      const editedPlayerContainer = document.getElementById("editedPlayerContainer");
      const previewGrid = document.getElementById("previewGrid");
      const pager = document.getElementById("pager");

      if (editedPlayerContainer) editedPlayerContainer.style.display = "none";
      if (previewGrid) previewGrid.style.display = "grid"; // 다시 보이게
      if (pager) pager.style.display = "flex"; // 다시 보이게

      // 비디오 일시정지 및 시간 초기화 (선택 사항)
      const editedVideo = document.querySelector('#editedVideoPlayer .video-player-element');
      if (editedVideo) {
        editedVideo.pause();
        editedVideo.currentTime = 0;
      }
    });
  }

  const startEditBtn = document.getElementById("startEditBtn");
  const endEditBtn = document.getElementById("endEditBtn");

  if (startEditBtn) {
    startEditBtn.addEventListener("click", () => {
      const originalVideo = document.querySelector('#originalVideoPlayer .video-player-element');
      editStart = originalVideo.currentTime;
      captureThumbnail(originalVideo); // 편집 시작 시 썸네일 캡처
      alert(`편집 시작 시간: ${AnalyzerShare.formatTime(editStart)}`);
    });
  }

  if (endEditBtn) {
    endEditBtn.addEventListener("click", () => {
      const originalVideo = document.querySelector('#originalVideoPlayer .video-player-element');
      if (editStart !== null && originalVideo.currentTime > editStart) {
        const segment = {
          start: editStart,
          end: originalVideo.currentTime,
          thumbnail: latestThumbnailDataURL // 마지막 캡처된 썸네일 사용
        };
        addThumbnailToPanel(segment);
        editStart = null; // 편집 시작 시간 초기화
        alert(`편집 완료: ${AnalyzerShare.formatTime(segment.start)} ~ ${AnalyzerShare.formatTime(segment.end)}`);
      } else {
        alert("편집 시작 시간을 먼저 설정하거나, 종료 시간이 시작 시간보다 늦어야 합니다.");
      }
    });
  }

  const showCumulativeBtnOriginal = document.getElementById("showCumulativeBtnOriginal");
  const showInstantaneousBtnOriginal = document.getElementById("showInstantaneousBtnOriginal");
  const showCumulativeBtnEdited = document.getElementById("showCumulativeBtnEdited");
  const showInstantaneousBtnEdited = document.getElementById("showInstantaneousBtnEdited");

  // 페이지 로드 시 원본 그래프의 'Show Cumulative' 버튼을 활성화
  if (showCumulativeBtnOriginal && showInstantaneousBtnOriginal) {
    AnalyzerShare.setActiveButton(showCumulativeBtnOriginal, showInstantaneousBtnOriginal, 'cumulative');
  }

  if (showCumulativeBtnOriginal && showInstantaneousBtnOriginal) {
    showCumulativeBtnOriginal.addEventListener("click", () => {
      AnalyzerShare.updateCognitiveLoadGraph('cumulative', 'dualGraphCanvasOriginal', AnalyzerShare.globalCognitiveLoadData);
      AnalyzerShare.setActiveButton(showCumulativeBtnOriginal, showInstantaneousBtnOriginal, 'cumulative');
    });
    showInstantaneousBtnOriginal.addEventListener("click", () => {
      AnalyzerShare.updateCognitiveLoadGraph('instantaneous', 'dualGraphCanvasOriginal', AnalyzerShare.globalCognitiveLoadData);
      AnalyzerShare.setActiveButton(showCumulativeBtnOriginal, showInstantaneousBtnOriginal, 'instantaneous');
    });
  }

  if (showCumulativeBtnEdited && showInstantaneousBtnEdited) {
    showCumulativeBtnEdited.addEventListener("click", () => {
      AnalyzerShare.updateCognitiveLoadGraph('cumulative', 'dualGraphCanvasEdited', editedSegmentCognitiveLoadData, { segment: currentPlayingSegment });
      AnalyzerShare.setActiveButton(showCumulativeBtnEdited, showInstantaneousBtnEdited, 'cumulative');
    });
    showInstantaneousBtnEdited.addEventListener("click", () => {
      AnalyzerShare.updateCognitiveLoadGraph('instantaneous', 'dualGraphCanvasEdited', editedSegmentCognitiveLoadData, { segment: currentPlayingSegment });
      AnalyzerShare.setActiveButton(showCumulativeBtnEdited, showInstantaneousBtnEdited, 'instantaneous');
    });
  }
});