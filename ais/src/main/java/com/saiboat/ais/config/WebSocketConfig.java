package com.saiboat.ais.config;

import com.saiboat.ais.service.TelemetryWebSocketService;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

@Configuration
@EnableWebSocket
public class WebSocketConfig implements WebSocketConfigurer {
    private final TelemetryWebSocketService telemetryWebSocketService;

    public WebSocketConfig(TelemetryWebSocketService telemetryWebSocketService) {
        this.telemetryWebSocketService = telemetryWebSocketService;
    }

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(telemetryWebSocketService, "/telemetry").setAllowedOrigins("*");
    }
}