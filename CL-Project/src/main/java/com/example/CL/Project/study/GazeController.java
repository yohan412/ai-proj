import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Bean;
//import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.web.client.RestTemplate;
import org.springframework.http.ResponseEntity;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import java.io.IOException;

@RestController
@RequestMapping("/api/gaze")
public class GazeController {

    private final RestTemplate rest;

    public GazeController(RestTemplate restTemplate) {
        this.rest = restTemplate;
    }

    @PostMapping("/frame")
    public ResponseEntity<String> recvFrame(@RequestParam("frame") MultipartFile file) throws IOException {
        // Flask 서버로 전달할 헤더 설정
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);

        // 바디에 파일 추가
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("frame", new MultipartInputStreamFileResource(
            file.getInputStream(), file.getOriginalFilename()));

        HttpEntity<MultiValueMap<String,Object>> request =
            new HttpEntity<>(body, headers);

        String flaskUrl = "http://localhost:5000/gaze";
        ResponseEntity<String> response =
            rest.postForEntity(flaskUrl, request, String.class);

        return ResponseEntity.ok(response.getBody());
    }
}