import json
import os
import networkx as nx
import google.generativeai as genai
import time
from .model_loader import get_gemini_model
from config import UPLOADS_DIR, extraction_user_prompt_template, extraction_system_prompt


def extract_spo_and_create_graph(transcript_data: list):
    """
    Extracts SPO triples from a transcript, creates a knowledge graph, and returns the data.

    Args:
        transcript_data: A list of transcript segment dictionaries.

    Returns:
        A tuple containing the graph data (dict) and the timed SPO data (list).

    Raises:
        RuntimeError: If the Gemini model is not initialized.
    """
    gemini_model = get_gemini_model(extraction_system_prompt)
    if gemini_model is None:
        raise RuntimeError("Failed to create a specialized Gemini model for SPO extraction.")

    full_text = " ".join([s['text'] for s in transcript_data])

    # --- Text Chunking for LLM Processing ---
    words = full_text.split()
    chunk_size = 1000  # Words per chunk
    overlap = 200      # Word overlap between chunks to maintain context
    
    chunks = []
    start_index = 0
    while start_index < len(words):
        end_index = min(start_index + chunk_size, len(words))
        chunk_text = " ".join(words[start_index:end_index])
        chunks.append(chunk_text)
        start_index += (chunk_size - overlap)
        if start_index >= len(words):
            break

    all_extracted_triples = []
    all_timed_triples = []

    # --- Iterate through chunks and extract SPOs ---
    for i, chunk_text in enumerate(chunks):
        extracted_triples = []
        raw_triples = ""
        retry_count = 0
        while retry_count < 3:
            try:
                # Generate content using the Gemini model with a specific user prompt
                response = gemini_model.generate_content(
                    extraction_user_prompt_template.format(text_chunk=chunk_text),
                    generation_config=genai.types.GenerationConfig(candidate_count=1, temperature=0.1)
                )
                raw_triples = response.text.strip()
                
                # Clean and parse the JSON response from the LLM
                if raw_triples.startswith("```json"):
                    raw_triples = raw_triples[len("```json"):].strip()
                if raw_triples.endswith("```"):
                    raw_triples = raw_triples[:-len("```")]

                extracted_triples = json.loads(raw_triples)
                all_extracted_triples.extend(extracted_triples)

                # Approximate timestamps for the extracted SPOs
                chunk_start_time = transcript_data[start_index]['start'] if transcript_data and start_index < len(transcript_data) else 0.0
                chunk_end_time = transcript_data[min(end_index-1, len(transcript_data)-1)]['end'] if transcript_data and min(end_index-1, len(transcript_data)-1) >= 0 else chunk_start_time + 1.0

                for triple in extracted_triples:
                    all_timed_triples.append({
                        "subject": triple.get('subject', ''),
                        "predicate": triple.get('predicate', ''),
                        "object": triple.get('object', ''),
                        "start_time": chunk_start_time,
                        "end_time": chunk_end_time
                    })
                break
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error in chunk {i}: {e}")
                print(f"Problematic raw LLM response: {raw_triples}")
                break

            except Exception as e:
                print(f"General Error extracting SPO from chunk {i}: {e}")
                retry_count += 1
                wait_time = 10 * retry_count
                time.sleep(wait_time)
        time.sleep(5)

    # --- Graph Construction and Centrality Calculation ---
    normalized_graph_triples = []
    seen_graph_triples = set()

    for t in all_extracted_triples:
        s_raw = t.get('subject', '')
        p_raw = t.get('predicate', '')
        o_raw = t.get('object', '')

        # Handle cases where the LLM returns a list or a comma-separated string
        subjects = s_raw if isinstance(s_raw, list) else [item.strip() for item in str(s_raw).split(',')]
        objects = o_raw if isinstance(o_raw, list) else [item.strip() for item in str(o_raw).split(',')]
        
        # Flatten the triples: Create a distinct triple for each combination of subject/object
        for s_item in subjects:
            for o_item in objects:
                s = s_item.strip().lower()
                p = p_raw.strip().lower()
                o = o_item.strip().lower()

                if all([s, p, o]):
                    key = (s, p, o)
                    if key not in seen_graph_triples:
                        normalized_graph_triples.append({'subject': s, 'predicate': p, 'object': o})
                        seen_graph_triples.add(key)
    
    G = nx.DiGraph()
    for triple in normalized_graph_triples:
        G.add_edge(triple['subject'], triple['object'], label=triple['predicate'])

    # --- D3.js Graph Data Formatting ---
    d3_nodes = []
    d3_links = []
    
    node_id_map = {node: i for i, node in enumerate(G.nodes())}
    
    node_degrees = dict(G.degree())
    max_degree = max(node_degrees.values()) if node_degrees else 1

    if G.number_of_nodes() == 0:
        betweenness_centrality = {}
        eigenvector_centrality = {}
    else:
        betweenness_centrality = nx.betweenness_centrality(G)
        eigenvector_centrality = nx.eigenvector_centrality(G, max_iter=1000)

    for node_name, node_id in node_id_map.items():
        degree = node_degrees.get(node_name, 0)
        node_value = 1 + (degree / max_degree) * 9
        
        d3_nodes.append({
            "id": node_id,
            "label": node_name,
            "group": 1,
            "value": node_value,
            "betweenness_centrality": betweenness_centrality.get(node_name, 0.0),
            "eigenvector_centrality": eigenvector_centrality.get(node_name, 0.0)
        })

    for u, v, data in G.edges(data=True):
        d3_links.append({
            "source": node_id_map[u],
            "target": node_id_map[v],
            "value": 1
        })
    
    graph_data = {"nodes": d3_nodes, "links": d3_links}

    return graph_data, all_timed_triples