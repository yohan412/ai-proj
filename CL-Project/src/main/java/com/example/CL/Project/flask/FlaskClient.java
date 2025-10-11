package com.example.CL.Project.flask;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.*;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;

import java.io.File;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;

@Component
public class FlaskClient {

  private final ObjectMapper mapper = new ObjectMapper();
  private final RestTemplate restTemplate;

  @Value("${app.flask.url}")
  private String flaskUrl;

  public FlaskClient(RestTemplate restTemplate) {
    this.restTemplate = restTemplate;
  }

  /** /analyze (Whisper + gpt-oss-20b) */
  public JsonNode analyze(File file, String lang) throws Exception {
    String base = flaskUrl.endsWith("/") ? flaskUrl : flaskUrl + "/";
    String url = base + "analyze";
    if (lang != null && !lang.isBlank()) {
      url += "?lang=" + URLEncoder.encode(lang, StandardCharsets.UTF_8);
    }

    HttpHeaders headers = new HttpHeaders();
    headers.setContentType(MediaType.MULTIPART_FORM_DATA);

    MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
    body.add("file", new FileSystemResource(file));

    HttpEntity<MultiValueMap<String, Object>> req = new HttpEntity<>(body, headers);
    ResponseEntity<String> resp = restTemplate.postForEntity(url, req, String.class);

    if (!resp.getStatusCode().is2xxSuccessful()) {
      throw new RuntimeException("Flask 오류: " + resp.getStatusCode() + " " + resp.getBody());
    }
    return mapper.readTree(resp.getBody());
  }

  /** /explain (챕터 상세 설명 생성) */
  public JsonNode explain(String segmentsJson, double start, double end, String lang) throws Exception {
    String base = flaskUrl.endsWith("/") ? flaskUrl : flaskUrl + "/";
    String url = base + "explain";

    HttpHeaders headers = new HttpHeaders();
    headers.setContentType(MediaType.APPLICATION_JSON);

    // JSON 요청 바디 생성
    String requestBody = String.format(
      "{\"segments\": %s, \"start\": %.2f, \"end\": %.2f, \"lang\": \"%s\"}",
      segmentsJson, start, end, lang != null ? lang : "ko"
    );

    HttpEntity<String> req = new HttpEntity<>(requestBody, headers);
    ResponseEntity<String> resp = restTemplate.postForEntity(url, req, String.class);

    if (!resp.getStatusCode().is2xxSuccessful()) {
      throw new RuntimeException("Flask 설명 생성 오류: " + resp.getStatusCode() + " " + resp.getBody());
    }
    return mapper.readTree(resp.getBody());
  }

  /** /chat (AI Agent + RAG 챗봇) */
  public JsonNode chat(String storedName, String segmentsJson, String question, String lang) throws Exception {
    String base = flaskUrl.endsWith("/") ? flaskUrl : flaskUrl + "/";
    String url = base + "chat";

    HttpHeaders headers = new HttpHeaders();
    headers.setContentType(MediaType.APPLICATION_JSON);

    // JSON 요청 바디 생성
    String requestBody = String.format(
      "{\"stored_name\": \"%s\", \"segments\": %s, \"question\": \"%s\", \"lang\": \"%s\"}",
      storedName, segmentsJson, question, lang != null ? lang : "ko"
    );

    HttpEntity<String> req = new HttpEntity<>(requestBody, headers);
    ResponseEntity<String> resp = restTemplate.postForEntity(url, req, String.class);

    if (!resp.getStatusCode().is2xxSuccessful()) {
      throw new RuntimeException("Flask 챗봇 오류: " + resp.getStatusCode() + " " + resp.getBody());
    }
    return mapper.readTree(resp.getBody());
  }
}