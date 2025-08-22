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
import java.util.List;

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
}

