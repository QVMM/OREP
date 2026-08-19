package com.orep.backend.service.roadshow;

import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class LegacyDeckInspectorTest {

    @Test
    void acceptsPlainPptx() throws Exception {
        byte[] bytes = zip(
                entry("ppt/slides/slide1.xml", "<p/>"),
                entry("ppt/slides/slide2.xml", "<p/>"),
                entry("[Content_Types].xml", "<Types/>")
        );
        var r = LegacyDeckInspector.inspect(bytes, "路演.pptx");
        assertTrue(r.ok());
        assertEquals(2, r.pageCount());
        assertEquals("pptx", r.ext());
        assertFalse(r.hash().isBlank());
    }

    @Test
    void rejectsPasswordPackage() throws Exception {
        byte[] bytes = zip(entry("EncryptionInfo", "secret"), entry("EncryptedPackage", "x"));
        var r = LegacyDeckInspector.inspect(bytes, "locked.pptx");
        assertFalse(r.ok());
        assertEquals("password", r.code());
        assertTrue(r.message().contains("密码"));
    }

    @Test
    void rejectsOversize() {
        var r = LegacyDeckInspector.inspect(new byte[81 * 1024 * 1024], "big.pptx");
        assertFalse(r.ok());
        assertEquals("too_large", r.code());
        assertTrue(r.message().contains("太大"));
    }

    @Test
    void rejectsTooManySlides() throws Exception {
        ZipEntry[] slides = new ZipEntry[81];
        byte[][] bodies = new byte[81][];
        for (int i = 0; i < 81; i++) {
            slides[i] = new ZipEntry("ppt/slides/slide" + (i + 1) + ".xml");
            bodies[i] = "<p/>".getBytes(StandardCharsets.UTF_8);
        }
        var r = LegacyDeckInspector.inspect(zipPairs(slides, bodies), "long.pptx");
        assertFalse(r.ok());
        assertEquals("too_many_pages", r.code());
    }

    @Test
    void rejectsPdfAndOldPpt() {
        assertEquals("pdf", LegacyDeckInspector.inspect("%PDF-1.4".getBytes(StandardCharsets.UTF_8), "a.pdf").code());
        assertEquals("need_pptx", LegacyDeckInspector.inspect(new byte[]{0, 1, 2}, "old.ppt").code());
        assertEquals("need_pptx", LegacyDeckInspector.inspect(new byte[]{0, 1, 2}, "deck.key").code());
    }

    @Test
    void rejectsBrokenZip() {
        var r = LegacyDeckInspector.inspect("not a zip".getBytes(StandardCharsets.UTF_8), "bad.pptx");
        assertFalse(r.ok());
        assertEquals("unreadable", r.code());
    }

    private static ZipEntry entry(String name, String body) {
        return new ZipEntry(name);
    }

    private static byte[] zip(ZipEntry first, ZipEntry... more) throws Exception {
        ZipEntry[] all = new ZipEntry[1 + more.length];
        all[0] = first;
        System.arraycopy(more, 0, all, 1, more.length);
        byte[][] bodies = new byte[all.length][];
        for (int i = 0; i < all.length; i++) {
            bodies[i] = "x".getBytes(StandardCharsets.UTF_8);
        }
        return zipPairs(all, bodies);
    }

    private static byte[] zipPairs(ZipEntry[] entries, byte[][] bodies) throws Exception {
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(bos)) {
            for (int i = 0; i < entries.length; i++) {
                zos.putNextEntry(entries[i]);
                zos.write(bodies[i]);
                zos.closeEntry();
            }
        }
        return bos.toByteArray();
    }
}
