from flask import Flask, request, jsonify
import os
import sys
import json
import datetime
from core.model_loader import initialize_models
from core.transcription import transcribe_audio
from core.spo_extraction import extract_spo_and_create_graph
from core.cognitive_load import calculate_cognitive_load
from core.str_extraction import rephrase_segments_as_paragraphs
from core.craft.text_scaling import weighted_top_words
from conda_run import run_in_conda as conda
from config import UPLOADS_DIR, IMAGES_DIR

app = Flask(__name__)

initialize_models()

def log_message(job_id, message):
    """Helper function to print log messages with a timestamp and job ID."""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if job_id:
        print(f"[{timestamp}] [Job {job_id}] {message}")
    else:
        print(f"[{timestamp}] {message}")

@app.route('/analyze', methods=['POST'])
def analyze_route():
    job_id = None
    try:
        log_message(None, "\n--- Received request for /analyze ---")
        data = request.get_json()
        if not data:
            log_message(None, "ERROR: Invalid JSON received.")
            return jsonify({"error": "Invalid JSON"}), 400

        audio_path = data.get('audio_path')
        job_id = data.get('jobId')
        log_message(job_id, f"Starting analysis for audio_path: {audio_path}")

        # Ensure the uploads directory exists
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

        if not audio_path:
            log_message(job_id, "ERROR - audio_path is required.")
            return jsonify({"error": "audio_path is required"}), 400
        
        audio_path = audio_path.replace('\\', '/')
        if not os.path.exists(audio_path):
            log_message(job_id, f"ERROR - Audio file not found at {audio_path}")
            return jsonify({"error": f"Audio file not found at {audio_path}"}), 404

        log_message(job_id, "Calling OCR service (compute_ssim)...")
        try:
            ocr_data = conda("ocr_env", "core.compute_ssim", audio_path.split('/')[-1].split('.')[0])
            str_data = ocr_data.get("data")
            log_message(job_id, "OCR service call successful.")
        except Exception as e:
            log_message(job_id, f"ERROR - OCR service call failed: {e}")
            return jsonify({"error": "Video file not found or OCR failed"}), 404

        log_message(job_id, "Transcribing audio...")
        transcript_data, language = transcribe_audio(audio_path)
        log_message(job_id, f"Transcription successful (Language: {language}).")

        log_message(job_id, "Rephrasing text segments...")
        str_data = rephrase_segments_as_paragraphs(str_data)
        log_message(job_id, "Rephrasing complete.")

        log_message(job_id, "Creating keyword graph...")
        graph_data, _ = extract_spo_and_create_graph(transcript_data)
        log_message(job_id, "Keyword graph created.")

        log_message(job_id, "Calculating keyword weights...")
        key_weight = 0
        if graph_data.get('nodes'):
            for node in graph_data['nodes']:
                key_weight += node.get('betweenness_centrality', 0.0) + node.get('eigenvector_centrality', 0.0)
            if len(graph_data['nodes']) > 0:
                key_weight /= len(graph_data['nodes'])
        log_message(job_id, f"Average key_weight = {key_weight}")

        top = [k for k, _ in weighted_top_words(str_data, 10)]
        n = len(top)
        node_centrality_map = {k: key_weight * (n - i) / n for i, k in enumerate(top)}
        log_message(job_id, "Node centrality map created.")

        log_message(job_id, "Calculating cognitive load...")
        cognitive_load_data = calculate_cognitive_load(str_data, graph_data, transcript_data, node_centrality_map)
        log_message(job_id, "Cognitive load calculation complete.")

        log_message(job_id, "Saving analysis results to files...")
        # Save transcript data
        transcript_file_path = UPLOADS_DIR / f"{job_id}_transcript.json"
        with open(transcript_file_path, 'w', encoding='utf-8') as f:
            json.dump(transcript_data, f, ensure_ascii=False, indent=4)
        log_message(job_id, f"Transcript saved to {transcript_file_path}")

        # Save graph data
        graph_file_path = UPLOADS_DIR / f"{job_id}_graph.json"
        with open(graph_file_path, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=4)
        log_message(job_id, f"Graph saved to {graph_file_path}")

        # Save cognitive load data
        cognitive_load_file_path = UPLOADS_DIR / f"{job_id}_cognitive_load.json"
        with open(cognitive_load_file_path, 'w', encoding='utf-8') as f:
            json.dump(cognitive_load_data, f, ensure_ascii=False, indent=4)
        log_message(job_id, f"Cognitive load saved to {cognitive_load_file_path}")

        # Save str_data
        str_data_file_path = UPLOADS_DIR / f"{job_id}_str_data.json"
        with open(str_data_file_path, 'w', encoding='utf-8') as f:
            json.dump(str_data, f, ensure_ascii=False, indent=4)
        log_message(job_id, f"str_data saved to {str_data_file_path}")

        final_result = {
            "language": language,
            "transcript": transcript_data,
            "graph": graph_data,
            "cognitiveLoad": cognitive_load_data,
            "strData": str_data
        }
        
        log_message(job_id, "--- Analysis complete. Sending response back to Java.---\n")
        return jsonify(final_result), 200

    except Exception as e:
        log_message(job_id, f"An error occurred during analysis: {e}")
        app.logger.error(f"[PYTHON] Job {job_id}: An error occurred during analysis: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/analyze_segment', methods=['POST'])
def analyze_segment_route():
    job_id = None
    try:
        log_message(None, "\n--- Received request for /analyze_segment ---")
        data = request.get_json()
        log_message(job_id, f"Received JSON data: {data}")
        if not data:
            log_message(None, "ERROR: Invalid JSON received for segment analysis.")
            return jsonify({"error": "Invalid JSON"}), 400

        job_id = data.get('jobId')

        start_val = data.get('startTime')
        end_val = data.get('endTime')

        if start_val is None or end_val is None:
            log_message(job_id, "ERROR - 'start' and 'end' times are required for segment analysis.")
            return jsonify({"error": "'start' and 'end' times are required"}), 400

        segment_start = float(start_val)
        segment_end = float(end_val)
        log_message(job_id, f"Starting segment analysis for Job {job_id}, from {segment_start} to {segment_end}")

        # Load original analysis data
        transcript_file_path = UPLOADS_DIR / f"{job_id}_transcript.json"
        graph_file_path = UPLOADS_DIR / f"{job_id}_graph.json"
        str_data_file_path = UPLOADS_DIR / f"{job_id}_str_data.json"

        log_message(job_id, f"Loading original data from: {transcript_file_path}, {graph_file_path}, {str_data_file_path}")
        with open(transcript_file_path, 'r', encoding='utf-8') as f:
            original_transcript_data = json.load(f)
        log_message(job_id, f"Loaded original_transcript_data with {len(original_transcript_data)} entries.")
        with open(graph_file_path, 'r', encoding='utf-8') as f:
            original_graph_data = json.load(f)
        log_message(job_id, f"Loaded original_graph_data with {len(original_graph_data.get('nodes', []))} nodes and {len(original_graph_data.get('links', []))} edges.")
        with open(str_data_file_path, 'r', encoding='utf-8') as f:
            original_str_data = json.load(f)
        log_message(job_id, f"Loaded original_str_data with {len(original_str_data)} entries.")

        # Helper to parse time strings (like MM:SS or just seconds) to seconds
        def parse_time_to_seconds(time_str):
            if isinstance(time_str, (int, float)):
                return time_str  # Already in seconds
            if not isinstance(time_str, str) or not time_str.strip():
                return 0  # Return 0 if it's not a string or is empty

            parts = time_str.split(':')
            try:
                if len(parts) == 1:
                    return int(parts[0]) # Just seconds
                elif len(parts) == 2:
                    return int(parts[0]) * 60 + int(parts[1]) # MM:SS
                elif len(parts) == 3:  # Handle HH:MM:SS
                    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            except (ValueError, TypeError):
                # This will catch cases like int('abc') or int(None)
                return 0
            return 0

        # Slice transcript data
        log_message(job_id, f"Slicing transcript data for segment {segment_start}-{segment_end}...")
        sliced_transcript_data = []
        for entry in original_transcript_data:
            entry_start_sec = parse_time_to_seconds(entry['start'])
            entry_end_sec = parse_time_to_seconds(entry['end'])
            if entry_start_sec >= segment_start and entry_end_sec <= segment_end:
                sliced_transcript_data.append(entry)
            elif entry_start_sec < segment_start and entry_end_sec > segment_start: # Partial overlap at start
                new_entry = entry.copy()
                new_entry['start'] = segment_start
                sliced_transcript_data.append(new_entry)
            elif entry_start_sec < segment_end and entry_end_sec > segment_end: # Partial overlap at end
                new_entry = entry.copy()
                new_entry['end'] = segment_end
                sliced_transcript_data.append(new_entry)
        log_message(job_id, f"Sliced transcript data contains {len(sliced_transcript_data)} entries.")

        # Slice str_data (assuming it has 'start' and 'end' like transcript)
        log_message(job_id, f"Slicing str_data for segment {segment_start}-{segment_end}...")
        sliced_str_data = []
        for entry in original_str_data:
            entry_start_sec = parse_time_to_seconds(entry['start'])
            entry_end_sec = parse_time_to_seconds(entry['end'])
            if entry_start_sec >= segment_start and entry_end_sec <= segment_end:
                sliced_str_data.append(entry)
            elif entry_start_sec < segment_start and entry_end_sec > segment_start: # Partial overlap at start
                new_entry = entry.copy()
                new_entry['start'] = segment_start
                sliced_str_data.append(new_entry)
            elif entry_start_sec < segment_end and entry_end_sec > segment_end: # Partial overlap at end
                new_entry = entry.copy()
                new_entry['end'] = segment_end
                sliced_str_data.append(new_entry)
        log_message(job_id, f"Sliced str_data contains {len(sliced_str_data)} entries.")

        # Recalculate graph data for the segment (simplified for now, full re-extraction might be too heavy)
        log_message(job_id, f"Slicing graph data for segment {segment_start}-{segment_end}...")
        sliced_graph_data = {"nodes": [], "edges": []}
        node_ids_in_segment = set()

        # Filter nodes
        for node in original_graph_data.get('nodes', []):
            # Assuming nodes have 'start_time' and 'end_time' or are associated with transcript entries
            # This part needs more specific logic based on how graph nodes are tied to time.
            # For simplicity, let's assume nodes are keywords from transcript entries.
            # We'll include nodes if their associated transcript entry is in the sliced_transcript_data.
            # This is a placeholder. A more robust solution would involve re-running SPO extraction on sliced_transcript_data.
            # For now, we'll just include all nodes from the original graph.
            # If graph nodes have time info, filter them here.
            sliced_graph_data['nodes'].append(node)
            node_ids_in_segment.add(node['id']) # Assuming 'id' is unique for nodes

        # Filter edges
        for edge in original_graph_data.get('edges', []):
            if edge['source'] in node_ids_in_segment and edge['target'] in node_ids_in_segment:
                sliced_graph_data['edges'].append(edge)
        log_message(job_id, f"Sliced graph data contains {len(sliced_graph_data['nodes'])} nodes and {len(sliced_graph_data['edges'])} edges.")

        # Recalculate cognitive load for the sliced segment
        # Need to re-calculate key_weight and node_centrality_map based on sliced_str_data and sliced_graph_data
        log_message(job_id, "Recalculating keyword weights for segment...")
        key_weight = 0
        if sliced_graph_data.get('nodes'):
            for node in sliced_graph_data['nodes']:
                key_weight += node.get('betweenness_centrality', 0.0) + node.get('eigenvector_centrality', 0.0)
            if len(sliced_graph_data['nodes']) > 0:
                key_weight /= len(sliced_graph_data['nodes'])
        log_message(job_id, f"Segment average key_weight = {key_weight}")

        top = [k for k, _ in weighted_top_words(sliced_str_data, 10)]
        n = len(top)
        node_centrality_map = {k: key_weight * (n - i) / n for i, k in enumerate(top)}
        log_message(job_id, "Segment node centrality map created.")

        log_message(job_id, "Calculating cognitive load for segment...")
        segment_cognitive_load_data = calculate_cognitive_load(sliced_str_data, sliced_graph_data, sliced_transcript_data, node_centrality_map, segment_start, segment_end)
        log_message(job_id, f"Segment cognitive load calculation complete. Data: {json.dumps(segment_cognitive_load_data)}")

        # Normalize cognitive load data
        log_message(job_id, "Normalizing cognitive load data...")
        max_instantaneous = 0
        if segment_cognitive_load_data['instantaneousLoadData']:
            max_instantaneous = max(segment_cognitive_load_data['instantaneousLoadData'])
        
        max_cumulative = 0
        if segment_cognitive_load_data['cumulativeLoadData']:
            max_cumulative = max(segment_cognitive_load_data['cumulativeLoadData'])

        # Determine the overall max for normalization (either instantaneous or cumulative)
        overall_max = max(max_instantaneous, max_cumulative)
        if overall_max == 0: # Avoid division by zero if all values are zero
            overall_max = 1

        normalized_instantaneous_load = [val / overall_max for val in segment_cognitive_load_data['instantaneousLoadData']]
        normalized_cumulative_load = [val / overall_max for val in segment_cognitive_load_data['cumulativeLoadData']]

        normalized_result = {
            "labels": segment_cognitive_load_data['labels'],
            "instantaneousLoadData": normalized_instantaneous_load,
            "cumulativeLoadData": normalized_cumulative_load
        }
        
        log_message(job_id, "--- Segment analysis complete. Sending normalized response.---\n")
        return jsonify({"cognitiveLoad": normalized_result}), 200

    except Exception as e:
        log_message(job_id, f"An error occurred during segment analysis: {e}")
        import traceback
        log_message(job_id, traceback.format_exc())
        app.logger.error(f"[PYTHON] Job {job_id}: An error occurred during segment analysis: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
