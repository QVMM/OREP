package com.orep.backend.service.roadshow;

import java.io.ByteArrayInputStream;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.Locale;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * 收下已有 PPT 前的硬检查。不对用户装 100% 读懂。
 */
public final class LegacyDeckInspector {

    public static final long MAX_BYTES = 80L * 1024 * 1024;
    public static final int MAX_PAGES = 80;

    private LegacyDeckInspector() {
    }

    public record Result(
            boolean ok,
            String code,
            String message,
            int pageCount,
            String ext,
            String hash
    ) {
        public static Result fail(String code, String message, String ext) {
            return new Result(false, code, message, 0, ext, "");
        }
    }

    public static Result inspect(byte[] bytes, String fileName) {
        String ext = extOf(fileName);
        if (bytes == null || bytes.length == 0) {
            return Result.fail("empty", "文件是空的。", ext);
        }
        if (bytes.length > MAX_BYTES) {
            return Result.fail("too_large", "太大了，先删附录再传，或拆开。", ext);
        }
        if ("pdf".equals(ext)) {
            return Result.fail("pdf", "这份是 PDF，不能按原件改字还你。请另存成 pptx。", ext);
        }
        if ("key".equals(ext) || "ppt".equals(ext) || "odp".equals(ext) || "pptm".equals(ext)) {
            return Result.fail("need_pptx", "请用 WPS 另存为 pptx 再传。", ext);
        }
        if (!"pptx".equals(ext) && !looksLikeZip(bytes)) {
            return Result.fail("need_pptx", "请另存为 pptx 再传。", ext);
        }
        if (looksLikeOle(bytes)) {
            return Result.fail("password", "这份加了密码，解开再传。", ext);
        }
        if (!looksLikeZip(bytes)) {
            return Result.fail("unreadable", "文件打不开。", ext);
        }
        try (ZipInputStream in = new ZipInputStream(new ByteArrayInputStream(bytes))) {
            int pages = 0;
            boolean encrypted = false;
            boolean hasContentTypes = false;
            ZipEntry e;
            while ((e = in.getNextEntry()) != null) {
                String name = e.getName();
                if ("EncryptionInfo".equals(name) || "EncryptedPackage".equals(name)
                        || name.endsWith("/EncryptionInfo") || name.endsWith("/EncryptedPackage")) {
                    encrypted = true;
                }
                if ("[Content_Types].xml".equals(name)) hasContentTypes = true;
                if (name.matches("ppt/slides/slide\\d+\\.xml")) pages += 1;
            }
            if (encrypted) {
                return Result.fail("password", "这份加了密码，解开再传。", ext);
            }
            if (!hasContentTypes && pages == 0) {
                return Result.fail("unreadable", "文件打不开。", ext);
            }
            if (pages > MAX_PAGES) {
                return Result.fail("too_many_pages", "页太多了，先删附录再传。", ext);
            }
            return new Result(true, "ok", "", pages, "pptx", sha256(bytes));
        } catch (Exception ex) {
            return Result.fail("unreadable", "文件打不开。", ext);
        }
    }

    static String extOf(String fileName) {
        if (fileName == null) return "";
        int dot = fileName.lastIndexOf('.');
        if (dot < 0) return "";
        return fileName.substring(dot + 1).toLowerCase(Locale.ROOT);
    }

    static boolean looksLikeZip(byte[] bytes) {
        return bytes.length >= 4 && bytes[0] == 'P' && bytes[1] == 'K';
    }

    static boolean looksLikeOle(byte[] bytes) {
        return bytes.length >= 8
                && (bytes[0] & 0xff) == 0xD0
                && (bytes[1] & 0xff) == 0xCF
                && (bytes[2] & 0xff) == 0x11
                && (bytes[3] & 0xff) == 0xE0;
    }

    static String sha256(byte[] bytes) {
        try {
            byte[] d = MessageDigest.getInstance("SHA-256").digest(bytes);
            return HexFormat.of().formatHex(d);
        } catch (Exception e) {
            return "";
        }
    }
}
