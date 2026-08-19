package com.orep.backend.config;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.messaging.Message;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.simp.stomp.StompCommand;
import org.springframework.messaging.simp.stomp.StompHeaderAccessor;
import org.springframework.messaging.support.MessageBuilder;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class WebSocketAuthChannelInterceptorTest {
    private JwtUtil jwtUtil;
    private WebSocketAuthChannelInterceptor interceptor;

    @BeforeEach
    void setUp() {
        jwtUtil = mock(JwtUtil.class);
        interceptor = new WebSocketAuthChannelInterceptor(jwtUtil);
    }

    @Test
    void validConnectTokenBindsUserPrincipal() {
        when(jwtUtil.validateToken("valid-token")).thenReturn(true);
        when(jwtUtil.getUserId("valid-token")).thenReturn(21L);
        Message<?> result = interceptor.preSend(
                connectMessage("Bearer valid-token"),
                mock(MessageChannel.class)
        );

        assertEquals("21", StompHeaderAccessor.wrap(result).getUser().getName());
    }

    @Test
    void invalidConnectTokenDoesNotBindIdentity() {
        when(jwtUtil.validateToken("invalid-token")).thenReturn(false);
        Message<?> result = interceptor.preSend(
                connectMessage("Bearer invalid-token"),
                mock(MessageChannel.class)
        );

        assertNull(StompHeaderAccessor.wrap(result).getUser());
    }

    private Message<byte[]> connectMessage(String authorization) {
        StompHeaderAccessor accessor = StompHeaderAccessor.create(StompCommand.CONNECT);
        accessor.setNativeHeader("Authorization", authorization);
        accessor.setLeaveMutable(true);
        return MessageBuilder.createMessage(new byte[0], accessor.getMessageHeaders());
    }
}
