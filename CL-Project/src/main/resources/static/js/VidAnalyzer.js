// VidAnalyzer.js
//
// This file is responsible for handling the client-side logic for the video analysis page.
// It now mirrors the robust data handling patterns from DeepAnalyzer.js to ensure stability.
// It manages video uploads, displays D3.js keyword network graphs, and renders Chart.js cognitive load graphs.

// --- Global State ---
let modalCognitiveLoadChartInstance = null;
let globalGraphData = { nodes: [], links: [] }; // Used for modal functionality

// --- D3 Network Graph ---

/**
 * Initializes and renders the D3.js force-directed graph for the keyword network.
 * @param {Array<Object>} nodes - Array of node objects.
 * @param {Array<Object>} links - Array of link objects.
 * @param {string} targetElementId - The ID of the DOM element to render the graph into.
 */
function initZettelGraphD3(nodes, links, targetElementId) {
  const zettelDiv = document.getElementById(targetElementId);
  if (!zettelDiv) return;

  globalGraphData = { nodes, links }; // Store for modal reuse

  const { width, height } = zettelDiv.getBoundingClientRect();
  d3.select(`#${targetElementId} svg`).remove();
  const svg = d3.select(`#${targetElementId}`)
    .append("svg")
    .attr("width", "100%")
    .attr("height", "100%")
    .attr("viewBox", `0 0 ${width || 400} ${height || 300}`);

  if (!nodes || !nodes.length) {
    console.warn("No nodes or links data for D3 graph.");
    return;
  }

  const color = d3.scaleOrdinal(d3.schemeCategory10);
  const rScale = d3.scaleLinear().domain(d3.extent(nodes, d => d.value || 1)).range([8, 24]);
  const linkWidthScale = d3.scaleLinear().domain(d3.extent(links, d => d.value || 1)).range([1, 5]);

  const sim = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id).distance(d => 150 - (d.value || 1) * 10))
    .force("charge", d3.forceManyBody().strength(-400))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collide", d3.forceCollide().radius(d => rScale(d.value || 1) + 5));

  const g = svg.append("g");
  svg.call(d3.zoom().scaleExtent([0.1, 8]).on("zoom", (event) => g.attr("transform", event.transform)));

  const link = g.append("g").attr("stroke-opacity", 0.6).selectAll("line").data(links).join("line")
    .attr("stroke", "#999").attr("stroke-width", d => linkWidthScale(d.value || 1));

  const node = g.append("g").selectAll("g").data(nodes).join("g").call(drag(sim));
  node.append("circle").attr("r", d => rScale(d.value || 1)).attr("fill", d => color(d.group))
    .attr("stroke", "#fff").attr("stroke-width", 1.5);
  node.append("text").text(d => d.label).attr("fill", "#fff").attr("font-size", "10px")
    .attr("text-anchor", "middle").attr("dominant-baseline", "middle").style("pointer-events", "none");

  const tooltip = d3.select("body").append("div").attr("class", "d3-tooltip")
    .style("position", "absolute").style("z-index", "10").style("visibility", "hidden")
    .style("background", "rgba(0,0,0,0.7)").style("color", "#fff").style("padding", "8px")
    .style("border-radius", "4px").style("font-size", "12px");

  node.on("mouseover", (event, d) => {
    tooltip.html(`Label: ${d.label}<br>Group: ${d.group}<br>Value: ${d.value}`)
      .style("visibility", "visible");
    link.style('stroke', l => (l.source === d || l.target === d) ? '#fff' : '#999')
      .style('stroke-opacity', l => (l.source === d || l.target === d) ? 1 : 0.6);
  }).on("mousemove", (event) => {
    tooltip.style("top", (event.pageY - 10) + "px").style("left", (event.pageX + 10) + "px");
  }).on("mouseout", () => {
    tooltip.style("visibility", "hidden");
    link.style('stroke', '#999').style('stroke-opacity', 0.6);
  });

  sim.on("tick", () => {
    link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
    node.attr("transform", d => `translate(${d.x},${d.y})`);
  });

  function drag(sim) {
    return d3.drag()
      .on("start", (event, d) => { if (!event.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
      .on("drag", (event, d) => { d.fx = event.x; d.fy = event.y; })
      .on("end", (event, d) => { if (!event.active) sim.alphaTarget(0); d.fx = null; d.fy = null; });
  }
}

// --- HP Bar & Data Fetching ---

/**
 * Updates the fatigue (HP) bar based on the video's current time.
 * This version correctly maps video time to the data index using the labels array.
 */
function updateFatigueBar() {
  const hpFill = document.getElementById('hpFill');
  const videoPlayer = document.querySelector('#videoPlayer .video-player-element');
  const { fatigueBarData, labels } = AnalyzerShare.globalCognitiveLoadData; // `labels` are in seconds

  if (!hpFill || !videoPlayer || !fatigueBarData || fatigueBarData.length === 0 || !labels || labels.length === 0) {
    hpFill.style.width = '100%';
    return;
  }

  const currentTime = videoPlayer.currentTime;
  let index = 0;

  // Find the correct index by finding the last time label that is less than or equal to the current video time
  for (let i = labels.length - 1; i >= 0; i--) {
    if (currentTime >= labels[i]) {
      index = i;
      break;
    }
  }

  const fatiguePercentage = fatigueBarData[index];
  hpFill.style.width = `${Math.round(fatiguePercentage * 100)}%`;
}

/**
 * Fetches and processes all analysis data for a completed job.
 * @param {string} jobId - The ID of the completed analysis job.
 */
async function fetchGraphAndCognitiveLoadData(jobId) {
  console.log(`Fetching final data for job ${jobId}`);
  const token = getToken();
  if (!token) {
    console.error("No token for fetching data.");
    AnalyzerShare.hideLoadingState('dualGraphCanvas');
    AnalyzerShare.hideLoadingState('zettelGraph');
    return;
  }

  try {
    const cognitiveLoadResponse = await fetch(`/api/jobs/${jobId}/cognitive-load`, { headers: { 'Authorization': `Bearer ${token}` } });
    if (!cognitiveLoadResponse.ok) throw new Error(`Cognitive load data fetch failed: ${cognitiveLoadResponse.statusText}`);
    const cognitiveLoadData = await cognitiveLoadResponse.json();

    const graphResponse = await fetch(`/api/jobs/${jobId}/graph`, { headers: { 'Authorization': `Bearer ${token}` } });
    if (!graphResponse.ok) throw new Error(`Graph data fetch failed: ${graphResponse.statusText}`);
    const graphData = await graphResponse.json();

    // --- Data Processing & Validation ---
    if (cognitiveLoadData && Array.isArray(cognitiveLoadData.labels) && cognitiveLoadData.labels.length > 0) {
      // Convert time-string labels to seconds
      const labelsInSeconds = cognitiveLoadData.labels.map(label => {
        const parts = label.split(':').map(Number);
        return parts[0] * 60 + parts[1];
      });

      // FIX: Normalize cumulative load to start from 0 for the HP bar
      const originalCumulativeLoad = cognitiveLoadData.cumulativeLoadData;
      const initialLoad = originalCumulativeLoad.length > 0 ? originalCumulativeLoad[0] : 0;
      const adjustedCumulativeLoad = originalCumulativeLoad.map(load => Math.max(0, load - initialLoad));

      AnalyzerShare.globalCognitiveLoadData = {
        labels: labelsInSeconds,
        instantaneousLoadData: cognitiveLoadData.instantaneousLoadData,
        cumulativeLoadData: adjustedCumulativeLoad, // Use adjusted data for the graph
        graph: graphData
      };

      const data = AnalyzerShare.globalCognitiveLoadData;
      const totalAdjustedLoad = data.cumulativeLoadData.length > 0 ? data.cumulativeLoadData[data.cumulativeLoadData.length - 1] : 0;
      data.fatigueBarData = totalAdjustedLoad > 0 ? data.cumulativeLoadData.map(load => 1 - (load / totalAdjustedLoad)) : data.cumulativeLoadData.map(() => 1);
      
      console.log("Successfully processed and normalized analysis data.");

      // --- UI Updates ---
      initZettelGraphD3(data.graph.nodes, data.graph.links, 'zettelGraph');
      AnalyzerShare.updateCognitiveLoadGraph('cumulative', 'dualGraphCanvas', data);
      updateFatigueBar();
    } else {
      throw new Error("Cognitive load data is missing or empty.");
    }
  } catch (error) {
    console.error("Error fetching or processing analysis results:", error);
    alert("Failed to display analysis results: " + error.message);
    const ctx = document.getElementById('dualGraphCanvas').getContext('2d');
    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
    ctx.fillStyle = 'white';
    ctx.textAlign = 'center';
    ctx.fillText('인지 부하 데이터를 불러오지 못했습니다.', ctx.canvas.width / 2, ctx.canvas.height / 2);
  } finally {
    AnalyzerShare.hideLoadingState('dualGraphCanvas');
    AnalyzerShare.hideLoadingState('zettelGraph');
  }
}

// --- DOMContentLoaded: Entry Point ---

document.addEventListener("DOMContentLoaded", function () {
  AnalyzerShare.initializeVideoPlayer('videoPlayer');

  const dropArea = document.getElementById("videoDrop");
  const videoInput = document.getElementById("videoInput");
  const videoPlayer = document.querySelector("#videoPlayer .video-player-element");
  const hpFill = document.getElementById('hpFill');

  // Load video and data if a job ID exists in the session
  const jobId = getJobId();
  if (jobId) {
    AnalyzerShare.showLoadingState('dualGraphCanvas');
    AnalyzerShare.showLoadingState('zettelGraph');
    fetch(`/api/videos/info/${jobId}`)
      .then(response => {
        if (!response.ok) throw new Error('Video not found');
        return response.json();
      })
      .then(job => {
        const videoUrl = `/uploads/${job.jobId}${job.fileName.slice(job.fileName.lastIndexOf('.'))}`;
        videoPlayer.src = videoUrl;
        videoPlayer.load();
        dropArea.querySelector('p').style.display = 'none';
        document.querySelector('#videoPlayer').style.display = 'block';
        fetchGraphAndCognitiveLoadData(jobId);
      })
      .catch(error => {
        console.error('Error loading video from Job ID:', error);
        // FIX: Instead of logging out, just clear the invalid Job ID.
        clearJobId(); 
        AnalyzerShare.hideLoadingState('dualGraphCanvas');
        AnalyzerShare.hideLoadingState('zettelGraph');
      });
  }

  if (hpFill) hpFill.style.width = '100%';

  if (dropArea && videoInput && videoPlayer) {
    const handleFile = (file) => {
      if (file && file.type.startsWith("video/")) {
        AnalyzerShare.showLoadingState('dualGraphCanvas');
        AnalyzerShare.showLoadingState('zettelGraph');
        videoPlayer.src = URL.createObjectURL(file);
        videoPlayer.load();

        // Stop click propagation on the video player itself after a file is loaded
        videoPlayer.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent the dropArea click event from firing
        });

        AnalyzerShare.uploadVideos(file)
          .then(data => {
            const jobId = data.jobId;
            if (jobId) {
              alert("업로드 완료! 분석을 시작합니다. Job ID: " + jobId);
              AnalyzerShare.pollJobStatus(
                jobId,
                (completedJobId) => { // onCompleted
                  alert(`Job ${completedJobId} finished successfully!`);
                  fetchGraphAndCognitiveLoadData(completedJobId);
                },
                (failedJobId, errorMessage) => { // onFailed
                  alert(`Job ${failedJobId} failed: ${errorMessage}`);
                  AnalyzerShare.hideLoadingState('dualGraphCanvas');
                  AnalyzerShare.hideLoadingState('zettelGraph');
                }
              );
            } else {
              throw new Error("업로드에 성공했지만 Job ID를 받지 못했습니다.");
            }
          })
          .catch(err => {
            alert(err.message);
            AnalyzerShare.hideLoadingState('dualGraphCanvas');
            AnalyzerShare.hideLoadingState('zettelGraph');
          });
      } else {
        alert("Please upload a valid video file.");
      }
    };

    dropArea.addEventListener("click", () => videoInput.click());
    ["dragover", "dragenter"].forEach(evt => dropArea.addEventListener(evt, (e) => { e.preventDefault(); dropArea.classList.add("dragover"); }));
    ["dragleave", "drop"].forEach(evt => dropArea.addEventListener(evt, () => dropArea.classList.remove("dragover")));
    dropArea.addEventListener("drop", (e) => { e.preventDefault(); handleFile(e.dataTransfer.files[0]); });
    videoInput.addEventListener("change", (e) => handleFile(e.target.files[0]));
    videoPlayer.addEventListener('timeupdate', updateFatigueBar);
  }

  // --- UI Controls & Modals ---
  const showCumulativeBtn = document.getElementById('showCumulativeBtn');
  const showInstantaneousBtn = document.getElementById('showInstantaneousBtn');

  if (showCumulativeBtn && showInstantaneousBtn) {
    showCumulativeBtn.addEventListener('click', () => {
      AnalyzerShare.updateCognitiveLoadGraph('cumulative', 'dualGraphCanvas', AnalyzerShare.globalCognitiveLoadData);
      AnalyzerShare.setActiveButton(showCumulativeBtn, showInstantaneousBtn, 'cumulative');
    });
    showInstantaneousBtn.addEventListener('click', () => {
      AnalyzerShare.updateCognitiveLoadGraph('instantaneous', 'dualGraphCanvas', AnalyzerShare.globalCognitiveLoadData);
      AnalyzerShare.setActiveButton(showCumulativeBtn, showInstantaneousBtn, 'instantaneous');
    });
    AnalyzerShare.setActiveButton(showCumulativeBtn, showInstantaneousBtn, 'cumulative');
  }

  const zettelGraphModal = document.getElementById('zettelGraphModal');
  const cognitiveLoadModal = document.getElementById('cognitiveLoadModal');
  const expandZettelBtn = document.getElementById('expandZettelGraph');
  const expandCognitiveLoadBtn = document.getElementById('expandCognitiveLoadGraph');
  const closeZettelBtn = document.getElementById('closeZettelGraphModal');
  const closeCognitiveLoadBtn = document.getElementById('closeCognitiveLoadModal');

  const closeModal = (modal, chartInstance, contentId) => {
    modal.classList.remove('visible');
    if (chartInstance) { chartInstance.destroy(); chartInstance = null; }
    if (contentId) { document.getElementById(contentId).innerHTML = ''; }
  };

  expandZettelBtn.addEventListener('click', () => {
    zettelGraphModal.classList.add('visible');
    setTimeout(() => initZettelGraphD3(globalGraphData.nodes, globalGraphData.links, 'zettelGraphModalContent'), 100);
  });

  expandCognitiveLoadBtn.addEventListener('click', () => {
    cognitiveLoadModal.classList.add('visible');
    const currentType = document.getElementById('showInstantaneousBtn').classList.contains('active') ? 'instantaneous' : 'cumulative';
    if (modalCognitiveLoadChartInstance) modalCognitiveLoadChartInstance.destroy();
    setTimeout(() => {
      modalCognitiveLoadChartInstance = AnalyzerShare.initCognitiveLoadGraph(
        AnalyzerShare.globalCognitiveLoadData.labels,
        currentType === 'instantaneous' ? AnalyzerShare.globalCognitiveLoadData.instantaneousLoadData : AnalyzerShare.globalCognitiveLoadData.cumulativeLoadData,
        currentType,
        'cognitiveLoadModalCanvas'
      );
    }, 100);
  });

  closeZettelBtn.addEventListener('click', () => closeModal(zettelGraphModal, null, 'zettelGraphModalContent'));
  closeCognitiveLoadBtn.addEventListener('click', () => closeModal(cognitiveLoadModal, modalCognitiveLoadChartInstance));
  zettelGraphModal.addEventListener('click', (e) => { if (e.target === zettelGraphModal) closeModal(zettelGraphModal, null, 'zettelGraphModalContent'); });
  cognitiveLoadModal.addEventListener('click', (e) => { if (e.target === cognitiveLoadModal) closeModal(cognitiveLoadModal, modalCognitiveLoadChartInstance); });
});
