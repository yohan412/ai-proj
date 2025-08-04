package com.example.CL.Project.service;

import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.connection.Message;
import org.springframework.data.redis.connection.MessageListener;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class RedisKeyExpirationListener implements MessageListener {

    private final FileService fileService;

    @Override
    public void onMessage(Message message, byte[] pattern) {
        String expiredKey = new String(message.getBody());
        if (expiredKey.startsWith("jwt:")) {
            String username = expiredKey.substring(4);
            System.out.println("Redis key expired: " + expiredKey + ". Triggering file deletion for user: " + username);
            fileService.deleteUserFiles(username);
        }
    }
}
