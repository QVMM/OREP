package com.orep.backend.service.roadshow;

import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;

class LegacySlideReaderTest {

    @Test
    void gradesTextPictureAndEmpty() {
        String text = """
                <p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
                  <p:cSld><p:spTree>
                    <p:sp><p:txBody><a:p><a:r><a:t>损耗发生在入库前</a:t></a:r></a:p></p:txBody></p:sp>
                  </p:spTree></p:cSld>
                </p:sld>
                """;
        String pic = """
                <p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
                  <p:cSld><p:spTree>
                    <p:pic><p:blipFill><a:blip r:embed="rId2"/></p:blipFill></p:pic>
                  </p:spTree></p:cSld>
                </p:sld>
                """;
        String empty = """
                <p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
                  <p:cSld><p:spTree></p:spTree></p:cSld>
                </p:sld>
                """;
        List<Map<String, Object>> pages = LegacySlideReader.grade(List.of(text, pic, empty));
        assertEquals("editable", pages.get(0).get("grade"));
        assertEquals("损耗发生在入库前", pages.get(0).get("excerpt"));
        assertEquals("picture", pages.get(1).get("grade"));
        assertEquals("empty", pages.get(2).get("grade"));
    }

    @Test
    void dropsXmlFragmentsFromExcerpt() {
        String dirty = """
                <p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
                  <a:t>团队分工</a:t>
                  <a:t></a:gradFill><a:latin typeface="+mn-ea"/></a:t>
                </p:sld>
                """;
        var pages = LegacySlideReader.grade(List.of(dirty));
        assertEquals("团队分工", pages.get(0).get("excerpt"));
    }

    @Test
    void unescapesQuotesAndDropsOurKicker() {
        String xml = """
                <p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
                  <a:t>按讲稿</a:t>
                  <a:t>&quot;识土&quot;是对番茄生长</a:t>
                </p:sld>
                """;
        var pages = LegacySlideReader.grade(List.of(xml));
        assertEquals("\"识土\"是对番茄生长", pages.get(0).get("excerpt"));
    }
}
