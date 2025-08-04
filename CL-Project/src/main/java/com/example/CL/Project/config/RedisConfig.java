package com.example.CL.Project.config;

import com.example.CL.Project.service.RedisKeyExpirationListener;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.listener.PatternTopic;
import org.springframework.data.redis.listener.RedisMessageListenerContainer;

@Configuration
public class RedisConfig {

    @Bean
    public RedisMessageListenerContainer keyExpirationListenerContainer(RedisConnectionFactory connectionFactory, RedisKeyExpirationListener listener) {
        RedisMessageListenerContainer listenerContainer = new RedisMessageListenerContainer();
        listenerContainer.setConnectionFactory(connectionFactory);
        listenerContainer.addMessageListener(listener, new PatternTopic("__keyevent@*__:expired"));
        // Ensure keyspace notifications are enabled
        connectionFactory.getConnection().setConfig("notify-keyspace-events", "Ex");
        return listenerContainer;
    }
}
