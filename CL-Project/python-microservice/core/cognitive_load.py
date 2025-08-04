import json
import os
import re
from typing import List, Dict

Segment = Dict[str, float | str]

def combine_segments(*lists_of_segments: List[Segment]) -> List[Segment]:
    """
    여러 개의 `segments` 목록을 하나로 합쳐 `start` 값 기준으로 정렬한다.

    Parameters
    ----------
    *lists_of_segments :
        (가변 인자) `[{'start': …, 'end': …, 'text': …}, …]` 형태의 리스트들을
        원하는 만큼 넘기면 된다.

    Returns
    -------
    List[Segment]
        `start` 오름차순으로 정렬된 단일 리스트
    """
    # ① 모두 펼쳐서 하나로 모음
    flat: List[Segment] = [seg for seg_list in lists_of_segments for seg in seg_list]

    # ② start 값 기준 정렬
    flat.sort(key=lambda seg: float(seg["start"]))
    return flat

def calculate_cognitive_load(str_data: list, graph_data: dict, transcript_data: list, node_centrality_map = {}, segment_start: float = 0.0, segment_end: float = 0.0):
    """
    Calculates cognitive load and returns the results as a dictionary.

    Args:
        str_data: str text.
        graph_data: A dictionary containing graph nodes and links.
        transcript_data: A list of transcript segment dictionaries.
        segment_start: The start time of the segment in seconds. Defaults to 0.0 for full video.
        segment_end: The end time of the segment in seconds. Defaults to 0.0 for full video.

    Returns:
        A dictionary containing the cognitive load data.
    """

    for node in graph_data['nodes']:
        node_centrality_map[node['label'].lower()] = node.get('betweenness_centrality', 0.0) + node.get('eigenvector_centrality', 0.0)
        

    transcript_data = combine_segments(transcript_data, str_data)

    window_size = 15
    
    # Determine the actual start and end times for the graph calculation
    # If segment_end is not explicitly provided (or is 0.0), assume full video analysis
    is_segment_analysis = (segment_end > segment_start)

    if is_segment_analysis:
        graph_calc_start_time = segment_start
        graph_calc_end_time = segment_end
    else: # Full video analysis
        graph_calc_start_time = 0.0
        # Find the maximum end time from all transcript data
        graph_calc_end_time = 0.0
        if transcript_data:
            graph_calc_end_time = max(float(s.get('end', 0.0)) for s in transcript_data)

    current_window_start = graph_calc_start_time

    labels = []
    instantaneous_load_data = []
    
    while current_window_start <= graph_calc_end_time + window_size:
        window_end = current_window_start + window_size
        
        current_window_load = 0.0
        
        for segment in transcript_data:
            # Only consider segments that overlap with the current window
            # And are within the overall graph_calc_start_time and graph_calc_end_time
            segment_actual_start = float(segment.get('start', 0.0))
            segment_actual_end = float(segment.get('end', 0.0))

            if segment_actual_start >= window_end:
                break # No more relevant segments in this window

            if segment_actual_end > current_window_start and \
               segment_actual_start < graph_calc_end_time + window_size and \
               segment_actual_end > graph_calc_start_time: # Ensure segment is within overall graph range
                words = re.findall(r'\b\w+\b', str(segment.get('text', '')).lower())
                for word in words:
                    if word in node_centrality_map:
                        current_window_load += node_centrality_map[word]
        
        instantaneous_load_data.append(current_window_load)
        
        # Label calculation based on analysis type
        if is_segment_analysis:
            relative_time = current_window_start - segment_start
            labels.append(f"{int(relative_time // 60):02d}:{int(relative_time % 60):02d}")
        else:
            labels.append(f"{int(current_window_start // 60):02d}:{int(current_window_start % 60):02d}")
        
        current_window_start += window_size

    cumulative_load_data = []
    current_cumulative_sum = 0.0
    for load_val in instantaneous_load_data:
        current_cumulative_sum += load_val
        cumulative_load_data.append(current_cumulative_sum)

    if instantaneous_load_data:
        max_instantaneous_load = max(instantaneous_load_data)
        if max_instantaneous_load > 0:
            instantaneous_load_data = [l / max_instantaneous_load for l in instantaneous_load_data]

    if cumulative_load_data:
        max_cumulative_load = max(cumulative_load_data)
        if max_cumulative_load > 0:
            cumulative_load_data = [l / max_cumulative_load for l in cumulative_load_data]

    cognitive_load_data = {
        "labels": labels,
        "instantaneousLoadData": instantaneous_load_data,
        "cumulativeLoadData": cumulative_load_data
    }

    return cognitive_load_data
