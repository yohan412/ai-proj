package com.example.CL.Project.content;

import com.example.CL.Project.content.*;
import com.example.CL.Project.flask.*;
import com.example.CL.Project.video.AnalyzeResponse;
import com.example.CL.Project.video.Chapter;
import com.example.CL.Project.video.Segment;
import com.fasterxml.jackson.databind.JsonNode;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.nio.file.Files;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class AnalyzeController {

  private final FlaskClient flaskClient;

  public AnalyzeController(FlaskClient flaskClient) {
    this.flaskClient = flaskClient;
  }

  /**
   * 업로드 → Flask(/analyze) → Whisper segments + gpt-oss-20b chapters 반환
   * 응답 스키마:
   * {
   *   "format":"json",
   *   "duration": 123.456,
   *   "segments":[{"start":..,"end":..,"text":".."}],
   *   "chapters":[{"start":..,"end":..,"title":"..","summary":".."}]
   * }
   */
  @PostMapping(
      value = "/analyze",
      consumes = MediaType.MULTIPART_FORM_DATA_VALUE,
      produces = MediaType.APPLICATION_JSON_VALUE
  )
  public ResponseEntity<AnalyzeResponse> analyze(
      @RequestParam("file") MultipartFile file,
      @RequestParam(value = "lang", required = false, defaultValue = "ko") String lang
  ) throws Exception {

    if (file == null || file.isEmpty()) {
      throw new IllegalArgumentException("업로드된 파일이 없습니다.");
    }

    var temp = Files.createTempFile("video_", "_" + file.getOriginalFilename()).toFile();
    try {
      file.transferTo(temp);

      JsonNode node = flaskClient.analyze(temp, lang);

      AnalyzeResponse out = new AnalyzeResponse();
      out.setFormat(node.path("format").asText("json"));
      out.setDuration(node.path("duration").asDouble(0.0));

      // segments
      if (node.has("segments")) {
        List<Segment> list = new ArrayList<>();
        for (JsonNode seg : node.get("segments")) {
          list.add(new Segment(
              seg.path("start").asDouble(0.0),
              seg.path("end").asDouble(0.0),
              seg.path("text").asText("")));
        }
        out.setSegments(list);
      }

      // chapters
      if (node.has("chapters")) {
        List<Chapter> list = new ArrayList<>();
        for (JsonNode ch : node.get("chapters")) {
          list.add(new Chapter(
              ch.path("start").asDouble(0.0),
              ch.path("end").asDouble(0.0),
              ch.path("title").asText(""),
              ch.path("summary").asText("")));
        }
        out.setChapters(list);
      }

      // fallback text (있으면 전달)
      if (node.has("text")) out.setText(node.path("text").asText(""));

      return ResponseEntity.ok(out);
    } finally {
      try { Files.deleteIfExists(temp.toPath()); } catch (Exception ignore) {}
    }
  }

  /**
   * 챕터 구간에 대한 상세 설명 생성
   * 요청 바디: { "segments": [...], "start": 10.5, "end": 20.3, "lang": "ko" }
   * 응답: { "explanation": "...", "segment_count": 0 }
   */
  @PostMapping(
      value = "/explain",
      consumes = MediaType.APPLICATION_JSON_VALUE,
      produces = MediaType.APPLICATION_JSON_VALUE
  )
  public ResponseEntity<?> explain(@RequestBody Map<String, Object> requestBody) {
    try {
      System.out.println("📘 챕터 설명 생성 요청");
      
      // 요청 파라미터 추출
      String segmentsJson = new com.fasterxml.jackson.databind.ObjectMapper()
          .writeValueAsString(requestBody.get("segments"));
      double start = ((Number) requestBody.getOrDefault("start", 0)).doubleValue();
      double end = ((Number) requestBody.getOrDefault("end", 0)).doubleValue();
      String lang = (String) requestBody.getOrDefault("lang", "ko");
      
      System.out.println("  - 구간: " + start + "s ~ " + end + "s");
      System.out.println("  - 언어: " + lang);
      
      // Flask로 요청 전달
      JsonNode response = flaskClient.explain(segmentsJson, start, end, lang);
      
      // 응답 파싱
      Map<String, Object> result = new HashMap<>();
      result.put("explanation", response.path("explanation").asText(""));
      result.put("segment_count", response.path("segment_count").asInt(0));
      
      System.out.println("✅ 설명 생성 완료");
      
      return ResponseEntity.ok(result);
      
    } catch (Exception e) {
      System.err.println("❌ 설명 생성 실패: " + e.getMessage());
      e.printStackTrace();
      
      Map<String, Object> errorResponse = new HashMap<>();
      errorResponse.put("error", "설명 생성 중 오류가 발생했습니다: " + e.getMessage());
      return ResponseEntity.status(500).body(errorResponse);
    }
  }

  /**
   * AI 챗봇 질의응답
   * 요청: { "stored_name": "...", "segments": [...], "question": "...", "lang": "ko" }
   * 응답: { "answer": "...", "sources": [...], "thinking_steps": [] }
   */
  @PostMapping(
      value = "/chat",
      consumes = MediaType.APPLICATION_JSON_VALUE,
      produces = MediaType.APPLICATION_JSON_VALUE
  )
  public ResponseEntity<?> chat(@RequestBody Map<String, Object> requestBody) {
    try {
      System.out.println("🤖 챗봇 질문 요청");
      
      String storedName = (String) requestBody.get("stored_name");
      String question = (String) requestBody.get("question");
      String lang = (String) requestBody.getOrDefault("lang", "ko");
      
      String segmentsJson = new com.fasterxml.jackson.databind.ObjectMapper()
          .writeValueAsString(requestBody.get("segments"));
      
      System.out.println("  - stored_name: " + storedName);
      System.out.println("  - question: " + question);
      
      // Flask로 요청 전달
      JsonNode response = flaskClient.chat(storedName, segmentsJson, question, lang);
      
      // 응답 파싱
      Map<String, Object> result = new HashMap<>();
      result.put("answer", response.path("answer").asText(""));
      
      // sources 배열
      List<Map<String, Object>> sources = new ArrayList<>();
      if (response.has("sources")) {
        for (JsonNode src : response.get("sources")) {
          Map<String, Object> sourceMap = new HashMap<>();
          sourceMap.put("start", src.path("start").asDouble(0.0));
          sourceMap.put("end", src.path("end").asDouble(0.0));
          sourceMap.put("text", src.path("text").asText(""));
          sourceMap.put("score", src.path("score").asDouble(0.0));
          sources.add(sourceMap);
        }
      }
      result.put("sources", sources);
      result.put("thinking_steps", new ArrayList<>());
      
      System.out.println("✅ 챗봇 응답 완료");
      
      return ResponseEntity.ok(result);
      
    } catch (Exception e) {
      System.err.println("❌ 챗봇 응답 실패: " + e.getMessage());
      e.printStackTrace();
      
      Map<String, Object> errorResponse = new HashMap<>();
      errorResponse.put("answer", "죄송합니다. 답변 생성 중 오류가 발생했습니다.");
      errorResponse.put("error", e.getMessage());
      errorResponse.put("sources", new ArrayList<>());
      errorResponse.put("thinking_steps", new ArrayList<>());
      return ResponseEntity.status(500).body(errorResponse);
    }
  }
}

