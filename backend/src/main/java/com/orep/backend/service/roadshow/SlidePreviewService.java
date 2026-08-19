package com.orep.backend.service.roadshow;

import okhttp3.MediaType;
import okhttp3.MultipartBody;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.concurrent.TimeUnit;

/**
 * 用已有 PPT 出页图：Collabora 转成 PDF，再按页裁图。不自己拼版。
 */
@Service
public class SlidePreviewService {

    private static final Logger log = LoggerFactory.getLogger(SlidePreviewService.class);
    private static final MediaType PPTX = MediaType.parse(
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    );

    private final String collaboraUrl;
    private final OkHttpClient http = new OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(180, TimeUnit.SECONDS)
            .writeTimeout(180, TimeUnit.SECONDS)
            .build();

    public SlidePreviewService(
            @Value("${orep.inspire-office.collabora-url:http://127.0.0.1:9980/collabora}") String collaboraUrl
    ) {
        this.collaboraUrl = collaboraUrl == null ? "" : collaboraUrl.replaceAll("/+$", "");
    }

    public byte[] png(Path work, int page) throws IOException {
        if (work == null || !Files.isRegularFile(work) || page < 1) {
            throw new IOException("没有这一页");
        }
        long stamp = Files.getLastModifiedTime(work).toMillis();
        Path dir = work.resolveSibling(work.getFileName().toString() + ".preview");
        Files.createDirectories(dir);
        Path pdf = dir.resolve(stamp + ".pdf");
        Path png = dir.resolve(stamp + "-p" + page + ".png");
        if (Files.isRegularFile(png) && Files.size(png) > 1000) {
            return Files.readAllBytes(png);
        }
        if (!Files.isRegularFile(pdf) || Files.size(pdf) < 1000) {
            convertPdf(work, pdf);
        }
        raster(pdf, page, png);
        if (!Files.isRegularFile(png) || Files.size(png) < 100) {
            throw new IOException("这一页现在画不出来");
        }
        return Files.readAllBytes(png);
    }

    private void convertPdf(Path work, Path pdf) throws IOException {
        if (collaboraUrl.isBlank()) throw new IOException("没有可用的预览服务");
        byte[] src = Files.readAllBytes(work);
        RequestBody file = RequestBody.create(src, PPTX);
        RequestBody body = new MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("data", "deck.pptx", file)
                .build();
        Request req = new Request.Builder()
                .url(collaboraUrl + "/cool/convert-to/pdf")
                .post(body)
                .build();
        try (Response res = http.newCall(req).execute()) {
            if (!res.isSuccessful() || res.body() == null) {
                throw new IOException("预览服务失败 " + res.code());
            }
            byte[] pdfBytes = res.body().bytes();
            if (pdfBytes.length < 100 || pdfBytes[0] != '%' || pdfBytes[1] != 'P') {
                throw new IOException("预览服务没有给出 PDF");
            }
            Files.write(pdf, pdfBytes);
        }
    }

    private void raster(Path pdf, int page, Path png) throws IOException {
        Path outBase = png.resolveSibling("tmp-" + page);
        ProcessBuilder pb = new ProcessBuilder(
                pdftoppm(),
                "-png",
                "-r", "110",
                "-f", String.valueOf(page),
                "-l", String.valueOf(page),
                "-singlefile",
                pdf.toString(),
                outBase.toString()
        );
        pb.redirectErrorStream(true);
        Process p = pb.start();
        try {
            if (!p.waitFor(60, TimeUnit.SECONDS)) {
                p.destroyForcibly();
                throw new IOException("出图超时");
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IOException("出图中断");
        }
        Path made = Path.of(outBase + ".png");
        if (!Files.isRegularFile(made)) {
            throw new IOException("没有这一页的图");
        }
        Files.move(made, png, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
    }

    private static String pdftoppm() {
        for (String c : List.of("/opt/homebrew/bin/pdftoppm", "/usr/local/bin/pdftoppm", "pdftoppm")) {
            Path p = Path.of(c);
            if (p.isAbsolute() && Files.isExecutable(p)) return c;
            if (!p.isAbsolute()) return c;
        }
        return "pdftoppm";
    }
}
