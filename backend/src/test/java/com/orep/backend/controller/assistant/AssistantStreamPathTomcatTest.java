package com.orep.backend.controller.assistant;

import org.apache.catalina.Context;
import org.apache.catalina.startup.Tomcat;
import org.junit.jupiter.api.Test;

import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.File;
import java.net.HttpURLConnection;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Confirms what Tomcat actually delivers for the 小启 SSE URL
 * POST /api/assistant/sessions/{id}/messages:stream
 */
class AssistantStreamPathTomcatTest {

    @Test
    void tomcatDeliversColonStreamPathToServlet() throws Exception {
        Tomcat tomcat = new Tomcat();
        tomcat.setPort(0);
        tomcat.setBaseDir("target/tomcat-assistant-stream");
        Context ctx = tomcat.addContext("", new File("target/tomcat-assistant-stream").getAbsolutePath());
        AtomicReference<String> uri = new AtomicReference<>();
        AtomicReference<String> servletPath = new AtomicReference<>();
        AtomicReference<String> pathInfo = new AtomicReference<>();
        Tomcat.addServlet(ctx, "echo", new HttpServlet() {
            @Override
            protected void service(HttpServletRequest req, HttpServletResponse resp) {
                uri.set(req.getRequestURI());
                servletPath.set(req.getServletPath());
                pathInfo.set(String.valueOf(req.getPathInfo()));
                resp.setStatus(200);
                resp.setContentType("text/plain;charset=UTF-8");
                try {
                    resp.getWriter().write("uri=" + req.getRequestURI()
                            + ";servletPath=" + req.getServletPath()
                            + ";pathInfo=" + req.getPathInfo());
                } catch (Exception ignored) {
                    /* test probe */
                }
            }
        });
        ctx.addServletMappingDecoded("/*", "echo");
        tomcat.getConnector();
        tomcat.start();
        try {
            int port = tomcat.getConnector().getLocalPort();
            String colonUrl = "http://127.0.0.1:" + port + "/api/assistant/sessions/9/messages:stream";
            String slashUrl = "http://127.0.0.1:" + port + "/api/assistant/sessions/9/messages/stream";

            Recorded colon = hit(colonUrl);
            Recorded slash = hit(slashUrl);

            assertThat(slash.code).isEqualTo(200);
            assertThat(slash.body).contains("/api/assistant/sessions/9/messages/stream");

            assertThat(colon.code)
                    .as("colon path HTTP status; body=%s uri=%s servletPath=%s pathInfo=%s",
                            colon.body, uri.get(), servletPath.get(), pathInfo.get())
                    .isEqualTo(200);
            assertThat(colon.body).contains("messages:stream");
        } finally {
            tomcat.stop();
            tomcat.destroy();
        }
    }

    private static Recorded hit(String url) throws Exception {
        HttpURLConnection conn = (HttpURLConnection) URI.create(url).toURL().openConnection();
        conn.setRequestMethod("POST");
        conn.setDoOutput(true);
        conn.getOutputStream().write("{}".getBytes(StandardCharsets.UTF_8));
        int code = conn.getResponseCode();
        byte[] raw = (code >= 400 ? conn.getErrorStream() : conn.getInputStream()).readAllBytes();
        return new Recorded(code, new String(raw, StandardCharsets.UTF_8));
    }

    private record Recorded(int code, String body) {
    }
}
