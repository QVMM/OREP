package com.orep.backend.service;

import com.orep.backend.entity.Script;
import com.orep.backend.mapper.ScriptMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class ScriptServiceApplyPatchesTest {

    private static final String DOC = """
            [{"id":"c1","title":"开场","steps":[
              {"id":"s1","role":"主讲人A","duration":0.5,"focus":"封面（P01）","content":"各位评委好","notes":"自信","transition":"接下来看背景"}
            ]}]
            """;

    @Mock
    private ScriptMapper scriptMapper;
    @Mock
    private ScriptRevisionService scriptRevisionService;
    @Mock
    private InspireOfficeService inspireOfficeService;

    private ScriptService service;

    @BeforeEach
    void setUp() {
        service = new ScriptService(scriptMapper, scriptRevisionService, inspireOfficeService);
    }

    @Test
    void applyPatchesIncrementsVersionAndKeepsRole() {
        Script existing = ownedScript();
        when(scriptMapper.selectOne(any())).thenReturn(existing);
        when(scriptMapper.updateById(any(Script.class))).thenReturn(1);

        Script out = service.applyPatches(12L, 9L, 7, List.of(contentPatch("各位评委好", "各位评委老师好")));

        assertEquals(8, out.getContentVersion());
        assertTrue(out.getContent().contains("各位评委老师好"));
        assertTrue(out.getContent().contains("\"role\":\"主讲人A\""));
        verify(scriptRevisionService).snapshot(existing, 9L, "apply_script_patch");
        ArgumentCaptor<Script> captor = ArgumentCaptor.forClass(Script.class);
        verify(scriptMapper).updateById(captor.capture());
        assertEquals(8, captor.getValue().getContentVersion());
    }

    @Test
    void versionMismatchReturns409() {
        when(scriptMapper.selectOne(any())).thenReturn(ownedScript());
        ResponseStatusException ex = assertThrows(
                ResponseStatusException.class,
                () -> service.applyPatches(12L, 9L, 3, List.of(contentPatch("各位评委好", "新稿"))));
        assertEquals(HttpStatus.CONFLICT, ex.getStatusCode());
    }

    @Test
    void missingScriptReturns404() {
        when(scriptMapper.selectOne(any())).thenReturn(null);
        ResponseStatusException ex = assertThrows(
                ResponseStatusException.class,
                () -> service.applyPatches(12L, 9L, 7, List.of(contentPatch("各位评委好", "新稿"))));
        assertEquals(HttpStatus.NOT_FOUND, ex.getStatusCode());
    }

    @Test
    void staleBeforeReturns409() {
        when(scriptMapper.selectOne(any())).thenReturn(ownedScript());
        ResponseStatusException ex = assertThrows(
                ResponseStatusException.class,
                () -> service.applyPatches(12L, 9L, 7, List.of(contentPatch("过期原文", "新稿"))));
        assertEquals(HttpStatus.CONFLICT, ex.getStatusCode());
    }

    @Test
    void roleFieldReturns400() {
        when(scriptMapper.selectOne(any())).thenReturn(ownedScript());
        Map<String, Object> patch = new LinkedHashMap<>();
        patch.put("stepId", "s1");
        patch.put("field", "role");
        patch.put("before", "主讲人A");
        patch.put("after", "角色B");
        ResponseStatusException ex = assertThrows(
                ResponseStatusException.class,
                () -> service.applyPatches(12L, 9L, 7, List.of(patch)));
        assertEquals(HttpStatus.BAD_REQUEST, ex.getStatusCode());
    }

    private static Script ownedScript() {
        Script script = new Script();
        script.setId(12L);
        script.setCreatedBy(9L);
        script.setContentVersion(7);
        script.setContent(DOC);
        script.setRoles("[{\"label\":\"主讲人A\"}]");
        script.setTitle("智慧农业");
        return script;
    }

    private static Map<String, Object> contentPatch(String before, String after) {
        Map<String, Object> patch = new LinkedHashMap<>();
        patch.put("stepId", "s1");
        patch.put("field", "content");
        patch.put("before", before);
        patch.put("after", after);
        patch.put("reason", "开场");
        return patch;
    }
}
