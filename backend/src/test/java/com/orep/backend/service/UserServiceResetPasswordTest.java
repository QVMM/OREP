package com.orep.backend.service;

import com.orep.backend.entity.User;
import com.orep.backend.mapper.UserMapper;
import com.orep.backend.security.DataScopeService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.util.ReflectionTestUtils;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.contains;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class UserServiceResetPasswordTest {

    private final UserMapper userMapper = mock(UserMapper.class);
    private final JdbcTemplate jdbc = mock(JdbcTemplate.class);
    private final DataScopeService dataScopeService = mock(DataScopeService.class);
    private final UserService userService = new UserService();

    @BeforeEach
    void injectDependencies() {
        ReflectionTestUtils.setField(userService, "userMapper", userMapper);
        ReflectionTestUtils.setField(userService, "jdbc", jdbc);
        ReflectionTestUtils.setField(userService, "dataScopeService", dataScopeService);
    }

    @Test
    void resetHashesDefaultPasswordWithHutoolBcryptAndUpdatesOnlyPassword() {
        User target = student(11L, 1L);
        when(userMapper.selectById(11L)).thenReturn(target);
        when(jdbc.update(contains("SET password"), anyString(), eq(11L))).thenReturn(1);

        userService.resetUserPassword(11L, 99L, "ADMIN", 1L);

        verify(jdbc).update(contains("SET password"), org.mockito.ArgumentMatchers.argThat(hash -> {
            assertThat(hash).isInstanceOf(String.class);
            String stored = (String) hash;
            assertThat(stored).isNotEqualTo(UserService.DEFAULT_RESET_PASSWORD);
            assertThat(cn.hutool.crypto.digest.BCrypt.checkpw(UserService.DEFAULT_RESET_PASSWORD, stored)).isTrue();
            return true;
        }), eq(11L));
        verify(userMapper, never()).updateById(any());
    }

    @Test
    void resetIsAllowedForSchoolAdminAndTeacherWithinScope() {
        User target = student(11L, 1L);
        when(userMapper.selectById(11L)).thenReturn(target);
        when(jdbc.update(contains("SET password"), anyString(), eq(11L))).thenReturn(1);

        userService.resetUserPassword(11L, 8L, "SCHOOL_ADMIN", 1L);
        userService.resetUserPassword(11L, 8L, "TEACHER", 1L);

        verify(dataScopeService, org.mockito.Mockito.times(2)).assertUserAccess(eq(8L), anyString(), eq(target));
    }

    @Test
    void studentOperatorCannotResetPassword() {
        assertThatThrownBy(() -> userService.resetUserPassword(11L, 3L, "STUDENT", 1L))
                .isInstanceOf(RuntimeException.class)
                .hasMessage("无权管理用户");
        verify(userMapper, never()).selectById(any());
        verify(jdbc, never()).update(anyString(), any(), any());
    }

    @Test
    void teacherCannotResetAdminPassword() {
        User admin = student(2L, 1L);
        admin.setRole("ADMIN");
        when(userMapper.selectById(2L)).thenReturn(admin);

        assertThatThrownBy(() -> userService.resetUserPassword(2L, 8L, "TEACHER", 1L))
                .isInstanceOf(RuntimeException.class)
                .hasMessage("教师无权修改该角色用户");
        verify(jdbc, never()).update(anyString(), any(), any());
    }

    @Test
    void missingUserIsRejected() {
        when(userMapper.selectById(404L)).thenReturn(null);

        assertThatThrownBy(() -> userService.resetUserPassword(404L, 99L, "ADMIN", 1L))
                .isInstanceOf(RuntimeException.class)
                .hasMessage("用户不存在");
    }

    @Test
    void dataScopeDenialDoesNotWritePassword() {
        User target = student(11L, 1L);
        when(userMapper.selectById(11L)).thenReturn(target);
        doThrow(new RuntimeException("无权访问该用户"))
                .when(dataScopeService).assertUserAccess(anyLong(), anyString(), any());

        assertThatThrownBy(() -> userService.resetUserPassword(11L, 8L, "TEACHER", 1L))
                .isInstanceOf(RuntimeException.class)
                .hasMessage("无权访问该用户");
        verify(jdbc, never()).update(anyString(), any(), any());
    }

    private static User student(Long id, Long tenantId) {
        User user = new User();
        user.setId(id);
        user.setTenantId(tenantId);
        user.setUsername("alice");
        user.setRole("STUDENT");
        user.setPassword("old-hash");
        return user;
    }
}
