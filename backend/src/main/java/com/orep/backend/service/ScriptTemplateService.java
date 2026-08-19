package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.entity.ScriptTemplate;
import com.orep.backend.mapper.ScriptTemplateMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class ScriptTemplateService {

    @Autowired
    private ScriptTemplateMapper mapper;

    /** 获取所有可用模板（系统默认 + 用户自定义） */
    public List<ScriptTemplate> listAvailable(Long userId) {
        LambdaQueryWrapper<ScriptTemplate> wrapper = new LambdaQueryWrapper<ScriptTemplate>()
                .eq(ScriptTemplate::getIsDefault, true);
        if (userId != null) {
            wrapper.or().eq(ScriptTemplate::getCreatedBy, userId);
        }
        return mapper.selectList(
                wrapper.orderByAsc(ScriptTemplate::getIsDefault) // 默认模板排前面
                        .orderByDesc(ScriptTemplate::getUpdatedAt)
        );
    }

    /** 获取用户自定义模板 */
    public List<ScriptTemplate> listByUser(Long userId) {
        return mapper.selectList(
                new LambdaQueryWrapper<ScriptTemplate>()
                        .eq(ScriptTemplate::getCreatedBy, userId)
                        .orderByDesc(ScriptTemplate::getUpdatedAt)
        );
    }

    /** 根据ID获取：系统默认模板可读，用户模板只允许本人读取。 */
    public ScriptTemplate getById(Long id, Long userId) {
        ScriptTemplate t = mapper.selectById(id);
        if (t == null) return null;
        if (Boolean.TRUE.equals(t.getIsDefault())) return t;
        if (userId != null && userId.equals(t.getCreatedBy())) return t;
        return null;
    }

    /** 创建模板 */
    public ScriptTemplate create(String name, String description, String content, String roles, Long userId) {
        ScriptTemplate t = new ScriptTemplate();
        t.setName(name);
        t.setDescription(description);
        t.setContent(content);
        t.setRoles(roles);
        t.setIsDefault(false);
        t.setCreatedBy(userId);
        t.setCreatedAt(LocalDateTime.now());
        t.setUpdatedAt(LocalDateTime.now());
        mapper.insert(t);
        return t;
    }

    /** 更新模板 */
    public ScriptTemplate update(Long id, String name, String description, String content, String roles, Long userId) {
        ScriptTemplate t = mapper.selectById(id);
        if (t == null || t.getIsDefault()) return null;
        if (userId == null || !userId.equals(t.getCreatedBy())) return null;
        t.setName(name);
        t.setDescription(description);
        if (content != null) t.setContent(content);
        if (roles != null) t.setRoles(roles);
        t.setUpdatedAt(LocalDateTime.now());
        mapper.updateById(t);
        return t;
    }

    /** 删除模板（不能删系统默认） */
    public boolean delete(Long id, Long userId) {
        ScriptTemplate t = mapper.selectById(id);
        if (t == null || t.getIsDefault()) return false;
        if (!userId.equals(t.getCreatedBy())) return false;
        return mapper.deleteById(id) > 0;
    }

    /** 从讲稿保存为模板 */
    public ScriptTemplate saveFromScript(String name, String description, String content, String roles, Long userId) {
        return create(name, description, content, roles, userId);
    }
}
