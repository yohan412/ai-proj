package com.example.CL.Project.service;

import com.example.CL.Project.dto.AnalysisResult;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.client.RestTemplate;
import org.springframework.http.ResponseEntity;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Collections;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;

@Service
public class VideoAnalysisServiceImpl implements VideoAnalysisService {

    private final InMemoryJobManager jobManager;
    private final RestTemplate restTemplate = new RestTemplate();
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final Path uploadPath;
    private final String FFMPEG_PATH = "../AudioModel/ffmpeg.exe";
    private final String PYTHON_MICROSERVICE_URL = "http://localhost:5000";

    @Autowired
    public VideoAnalysisServiceImpl(InMemoryJobManager jobManager) {
        this.jobManager = jobManager;
        // Initialize the upload path using the 'user.dir' system property to ensure it's absolute.
        this.uploadPath = Paths.get(System.getProperty("user.dir"), "uploads");
    }

    @Override
    public String analyzeVideo(MultipartFile file, String username) {
        String originalFilename = file.getOriginalFilename();
        String filenameWithoutExtension = originalFilename.substring(0, originalFilename.lastIndexOf('.'));
        String extension = originalFilename.substring(originalFilename.lastIndexOf('.'));
        String jobId = getUniqueJobId(username, filenameWithoutExtension, extension);

        CompletableFuture<AnalysisResult> future = new CompletableFuture<>();
        jobManager.submitJob(jobId, future);

        // Run the actual analysis in a separate thread.
        performAnalysis(file, jobId, future);

        // Return the Job ID to the controller immediately.
        return jobId;
    }

    private String getUniqueJobId(String username, String filename, String extension) {
        String baseJobId = username + "_" + filename;
        String finalJobId = baseJobId;
        int counter = 1;
        // This loop now checks for the existence of the video file itself.
        // If a file such as 'uploads/admin_helloWorld.mp4' already exists, it appends a counter.
        // For example, if 'admin_helloWorld.mp4' exists, the next ID will be 'admin_helloWorld(1)'.
        while (Files.exists(uploadPath.resolve(finalJobId + extension))) {
            finalJobId = baseJobId + "(" + counter + ")";
            counter++;
        }
        return finalJobId;
    }

    @Async
    public void performAnalysis(MultipartFile file, String jobId, CompletableFuture<AnalysisResult> future) {
        try {
            if (!Files.exists(uploadPath)) {
                Files.createDirectories(uploadPath);
            }

            String originalFilename = file.getOriginalFilename();
            String extension = "";
            if (originalFilename != null && originalFilename.contains(".")) {
                extension = originalFilename.substring(originalFilename.lastIndexOf("."));
            }
            // Save the video file directly in the 'uploads' directory.
            Path videoFilePath = uploadPath.resolve(jobId + extension);
            Files.copy(file.getInputStream(), videoFilePath);

            Path audioFilePath = uploadPath.resolve(jobId + ".mp3");
            extractAudio(videoFilePath, audioFilePath);

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.setAccept(Collections.singletonList(MediaType.APPLICATION_JSON));

            Map<String, String> requestBody = Map.of(
                    "audio_path", audioFilePath.toAbsolutePath().toString(),
                    "jobId", jobId
            );
            HttpEntity<Map<String, String>> request = new HttpEntity<>(requestBody, headers);

            ResponseEntity<Map> analysisResponse = restTemplate.postForEntity(
                    PYTHON_MICROSERVICE_URL + "/analyze", request, Map.class);

            if (analysisResponse.getStatusCode().is2xxSuccessful() && analysisResponse.getBody() != null) {
                Map<String, Object> responseData = analysisResponse.getBody();

                // All generated files will be stored directly in the 'uploads' directory.
                Object transcriptObj = responseData.get("transcript");
                Path transcriptPath = uploadPath.resolve(jobId + "_transcript.json");
                objectMapper.writeValue(transcriptPath.toFile(), transcriptObj);

                Object graphObj = responseData.get("graph");
                Path graphPath = uploadPath.resolve(jobId + "_graph.json");
                objectMapper.writeValue(graphPath.toFile(), graphObj);

                Object cognitiveLoadObj = responseData.get("cognitiveLoad");
                Path cognitiveLoadPath = uploadPath.resolve(jobId + "_cognitive_load.json");
                objectMapper.writeValue(cognitiveLoadPath.toFile(), cognitiveLoadObj);

                Object strDataObj = responseData.get("strData");
                Path strDataPath = uploadPath.resolve(jobId + "_str_data.json");
                objectMapper.writeValue(strDataPath.toFile(), strDataObj);

                AnalysisResult result = new AnalysisResult(
                        transcriptPath.toString(),
                        graphPath.toString(),
                        cognitiveLoadPath.toString(),
                        strDataPath.toString()
                );
                future.complete(result);

            } else {
                throw new IOException("Analysis failed: " + analysisResponse.getStatusCode());
            }

        } catch (Exception e) {
            future.completeExceptionally(e);
        }
    }


    private void extractAudio(Path videoFilePath, Path audioFilePath) throws IOException, InterruptedException {
        ProcessBuilder processBuilder = new ProcessBuilder(
                FFMPEG_PATH,
                "-i", videoFilePath.toString(),
                "-vn",
                "-acodec", "libmp3lame",
                "-q:a", "2",
                "-ar", "16000",
                "-map_metadata", "-1",
                audioFilePath.toString()
        );
        processBuilder.directory(new java.io.File(System.getProperty("user.dir")));
        processBuilder.redirectErrorStream(true);
        Process process = processBuilder.start();

        new Thread(() -> {
            try (var reader = new java.io.BufferedReader(new java.io.InputStreamReader(process.getInputStream()))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    System.out.println(line);
                }
            } catch (IOException e) {
                System.err.println("Error reading FFmpeg output: " + e.getMessage());
            }
        }).start();

        int exitCode = process.waitFor();
        if (exitCode != 0) {
            throw new IOException("FFmpeg audio extraction failed with exit code " + exitCode);
        }
    }
}
