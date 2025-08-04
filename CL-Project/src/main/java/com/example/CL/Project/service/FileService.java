package com.example.CL.Project.service;

import org.springframework.stereotype.Service;
import org.springframework.util.FileSystemUtils;

import java.io.IOException;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

@Service
public class FileService {

    private final Path uploadPath;

    public FileService() {
        // Initialize the upload path using the 'user.dir' system property.
        // This ensures the path is absolute and correctly points to the project's 'uploads' directory.
        this.uploadPath = Paths.get(System.getProperty("user.dir"), "uploads");
    }

    /**
     * Deletes all files associated with a specific username from the uploads directory.
     * This method scans the upload directory for any files that start
     * with the given username followed by an underscore, and deletes them.
     *
     * @param username The username whose files need to be deleted.
     */
    public void deleteUserFiles(String username) {
        System.out.println("🗑️ Deleting files for user: " + username);
        String prefix = username + "_";

        // Delete files in the main uploads directory
        deleteFilesWithPrefix(uploadPath, prefix);

        // Delete files in the images subdirectory
        Path imagesPath = uploadPath.resolve("images");
        deleteFilesWithPrefix(imagesPath, prefix);
    }

    private void deleteFilesWithPrefix(Path directory, String prefix) {
        if (!Files.exists(directory) || !Files.isDirectory(directory)) {
            System.out.println("Directory does not exist, skipping: " + directory);
            return;
        }

        System.out.println("Searching for files with prefix '" + prefix + "' in directory: " + directory);
        try (DirectoryStream<Path> stream = Files.newDirectoryStream(directory)) {
            int deletedCount = 0;
            for (Path entry : stream) {
                if (Files.isRegularFile(entry) && entry.getFileName().toString().startsWith(prefix)) {
                    try {
                        Files.delete(entry);
                        System.out.println("  - Successfully deleted file: " + entry.getFileName());
                        deletedCount++;
                    } catch (IOException e) {
                        System.err.println("  - Failed to delete file: " + entry + " - " + e.getMessage());
                    }
                }
            }
            if (deletedCount == 0) {
                System.out.println("No files found with prefix '" + prefix + "' in " + directory);
            }
        } catch (IOException e) {
            System.err.println("Error reading directory: " + directory + " - " + e.getMessage());
        }
    }
}
