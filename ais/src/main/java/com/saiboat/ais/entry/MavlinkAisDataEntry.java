package com.saiboat.ais;

import com.saiboat.ais.service.TelemetryWebSocketService;
import io.dronefleet.mavlink.MavlinkConnection;
import io.dronefleet.mavlink.MavlinkMessage;
import io.dronefleet.mavlink.common.AisVessel;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.net.Socket;
import java.util.HashMap;
import java.util.Map;

@Service
public class MavlinkAisDataEntry {

    @Value("${mavlink.host:127.0.0.1}")
    private String mavlinkHost;

    @Value("${mavlink.port:5760}")
    private int mavlinkPort;

    private final TelemetryWebSocketService telemetryWebSocketService;

    public MavlinkAisDataEntry(TelemetryWebSocketService telemetryWebSocketService) {
        this.telemetryWebSocketService = telemetryWebSocketService;
    }

    @PostConstruct
    public void init() {
        new Thread(this::startMavlinkConnection).start();
    }

    private void startMavlinkConnection() {
        while (true) {
            try (Socket socket = new Socket(mavlinkHost, mavlinkPort)) {
                MavlinkConnection connection = MavlinkConnection.create(
                        socket.getInputStream(),
                        socket.getOutputStream()
                );
                while (!Thread.interrupted()) {
                    MavlinkMessage message = connection.next();
                    if (message != null) {
                        processMavlinkMessage(message);
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
                try {
                    Thread.sleep(5000); // Wait 5 seconds before reconnecting
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }
        }
    }

    private void processMavlinkMessage(MavlinkMessage message) {
        Map<String, Object> telemetryData = new HashMap<>();

        if (message.getPayload() instanceof AisVessel) {
            AisVessel aisVessel = (AisVessel) message.getPayload();
            telemetryData.put("mmsi", aisVessel.mmsi());
            telemetryData.put("latitude", aisVessel.lat() / 1e7); // Convert to degrees
            telemetryData.put("longitude", aisVessel.lon() / 1e7); // Convert to degrees
        }

        if (!telemetryData.isEmpty()) {
            TelemetryWebSocketService.sendTelemetryData(telemetryData);
        }
    }
}