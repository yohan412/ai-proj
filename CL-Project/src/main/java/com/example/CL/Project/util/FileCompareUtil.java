package com.example.CL.Project.util;

import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;

import org.apache.commons.codec.binary.Hex;
import org.springframework.web.multipart.MultipartFile;

public class FileCompareUtil {

    // SHA-256 해시 계산
    public static String getFileHash(InputStream is) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] buffer = new byte[8192];
        int read;
        while ((read = is.read(buffer)) != -1) {
            digest.update(buffer, 0, read);
        }
        byte[] hashBytes = digest.digest();
        return Hex.encodeHexString(hashBytes); // commons-codec 필요
    }

    // 크기 비교 후 해시 비교
    public static boolean isSameFile(MultipartFile uploadedFile, String serverFilePath) throws Exception {
        Path serverPath = Paths.get(serverFilePath);
        long serverFileSize = Files.size(serverPath);
        long uploadedFileSize = uploadedFile.getSize();

        // 1단계: 파일 크기 비교
        if (serverFileSize != uploadedFileSize) {
            return false;
        }

        // 2단계: 해시 비교
        try (InputStream uploadedIs = uploadedFile.getInputStream();
             InputStream serverIs = Files.newInputStream(serverPath)) {

            String uploadedHash = getFileHash(uploadedIs);
            String serverHash = getFileHash(serverIs);

            return uploadedHash.equals(serverHash);
        }
    }
}
