package com.orep.backend.service;

import com.orep.backend.config.JwtUtil;
import com.orep.backend.dto.*;
import com.orep.backend.entity.EmailVerificationCode;
import com.orep.backend.entity.User;
import com.orep.backend.mapper.EmailVerificationCodeMapper;
import com.orep.backend.mapper.UserMapper;
import cn.hutool.core.util.RandomUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.stereotype.Service;

import jakarta.mail.internet.MimeMessage;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.concurrent.TimeUnit;

@Service
public class AuthService {

    @Autowired
    private UserMapper userMapper;
    @Autowired
    private EmailVerificationCodeMapper codeMapper;
    @Autowired
    private JwtUtil jwtUtil;
    @Autowired
    private JavaMailSender mailSender;
    @Autowired
    private StringRedisTemplate redisTemplate;

    @Value("${orep.email.from}")
    private String emailFrom;

    @Value("${orep.email.python-fallback-enabled:false}")
    private boolean pythonFallbackEnabled;

    @Value("${orep.email.python-bin:python3}")
    private String pythonBin;

    @Value("${spring.mail.username:}")
    private String mailUsername;

    @Value("${spring.mail.password:}")
    private String mailPassword;

    public void sendVerificationCode(String email) {
        // 生成6位验证码
        String code = RandomUtil.randomNumbers(6);

        // 保存到数据库
        EmailVerificationCode evc = new EmailVerificationCode();
        evc.setEmail(email);
        evc.setCode(code);
        evc.setExpiredAt(LocalDateTime.now().plusMinutes(5));
        evc.setUsed(false);
        codeMapper.insert(evc);

        // 发送邮件
        try {
            MimeMessage message = mailSender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(message, true, "UTF-8");
            helper.setFrom(emailFrom);
            helper.setTo(email);
            helper.setSubject("OREP 访问验证码");
            helper.setText(
                    "您的 OREP 验证码是：" + code + "\n验证码有效期为5分钟，请勿泄露。",
                    buildVerificationEmailHtml(code, email)
            );
            mailSender.send(message);
        } catch (Exception e) {
            System.out.println("邮件发送失败: " + e.getMessage());
            if (pythonFallbackEnabled) {
                try {
                    sendWithPythonFallback(email, code, buildVerificationEmailHtml(code, email));
                    System.out.println("邮件已通过 Python SMTP_SSL 兜底发送: " + email);
                    return;
                } catch (Exception fallbackError) {
                    System.out.println("Python 邮件兜底发送失败: " + fallbackError.getMessage());
                }
            }
            throw new RuntimeException("邮件发送失败，请检查邮箱地址或稍后重试");
        }
    }

    private void sendWithPythonFallback(String email, String code, String html) throws Exception {
        if (mailUsername == null || mailUsername.isBlank() || mailPassword == null || mailPassword.isBlank()) {
            throw new IllegalStateException("邮件用户名或授权码为空");
        }

        String script = """
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

user = os.environ["OREP_SMTP_USER"]
password = os.environ["OREP_SMTP_PASSWORD"]
sender = os.environ["OREP_SMTP_FROM"]
receiver = os.environ["OREP_SMTP_TO"]
subject = os.environ["OREP_SMTP_SUBJECT"]
text = os.environ["OREP_SMTP_TEXT"]
html = os.environ["OREP_SMTP_HTML"]

msg = MIMEMultipart("alternative")
msg["Subject"] = subject
msg["From"] = sender
msg["To"] = receiver
msg.attach(MIMEText(text, "plain", "utf-8"))
msg.attach(MIMEText(html, "html", "utf-8"))

with smtplib.SMTP_SSL("smtp.qq.com", 465, timeout=15, context=ssl.create_default_context()) as smtp:
    smtp.login(user, password)
    smtp.sendmail(sender, [receiver], msg.as_string())
""";

        ProcessBuilder pb = new ProcessBuilder(pythonBin, "-c", script);
        pb.environment().put("OREP_SMTP_USER", mailUsername);
        pb.environment().put("OREP_SMTP_PASSWORD", mailPassword);
        pb.environment().put("OREP_SMTP_FROM", emailFrom);
        pb.environment().put("OREP_SMTP_TO", email);
        pb.environment().put("OREP_SMTP_SUBJECT", "OREP 访问验证码");
        pb.environment().put("OREP_SMTP_TEXT", "您的 OREP 验证码是：" + code + "\\n验证码有效期为5分钟，请勿泄露。");
        pb.environment().put("OREP_SMTP_HTML", html);

        Process process = pb.start();
        boolean finished = process.waitFor(25, TimeUnit.SECONDS);
        String stderr = new String(process.getErrorStream().readAllBytes(), StandardCharsets.UTF_8);
        String stdout = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        if (!finished) {
            process.destroyForcibly();
            throw new RuntimeException("Python SMTP 发送超时");
        }
        if (process.exitValue() != 0) {
            throw new RuntimeException((stderr + "\n" + stdout).trim());
        }
    }

    private String buildVerificationEmailHtml(String code, String email) {
        String[] digits = code.split("");
        StringBuilder digitCells = new StringBuilder();
        for (String digit : digits) {
            digitCells
                    .append("<td style=\"padding:0 4px;\">")
                    .append("<div style=\"width:46px;height:54px;line-height:54px;text-align:center;border:1px solid #3b4546;background:#101416;color:#eff3ff;font-size:28px;font-weight:800;letter-spacing:0;border-radius:0;font-family:Arial,'Helvetica Neue',Helvetica,sans-serif;\">")
                    .append(escapeHtml(digit))
                    .append("</div>")
                    .append("</td>");
        }

        return "<!doctype html>"
                + "<html><head><meta charset=\"UTF-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\"></head>"
                + "<body style=\"margin:0;padding:0;background:#050607;color:#eff3ff;font-family:Arial,'PingFang SC','Microsoft YaHei',sans-serif;\">"
                + "<table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\" style=\"background:#050607;margin:0;padding:28px 12px;\">"
                + "<tr><td align=\"center\">"
                + "<table role=\"presentation\" width=\"620\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\" style=\"width:620px;max-width:100%;background:#0b0d10;border:1px solid #2b3135;\">"
                + "<tr><td style=\"padding:30px 34px 20px 34px;border-bottom:1px solid #252b30;background:#080a0d;\">"
                + "<table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\"><tr>"
                + "<td align=\"left\">"
                + "<div style=\"display:inline-block;background:#eff3ff;color:#050607;padding:10px 16px;font-size:23px;font-weight:800;letter-spacing:3px;line-height:1;font-family:Arial,'Helvetica Neue',Helvetica,sans-serif;\">OREP</div>"
                + "<div style=\"display:inline-block;margin-left:14px;color:#80868f;font-size:12px;font-weight:700;letter-spacing:4px;vertical-align:middle;\">ROADSHOW OPS</div>"
                + "</td>"
                + "<td align=\"right\" style=\"color:#72f0a7;font-size:12px;font-weight:800;letter-spacing:3px;white-space:nowrap;\">ACCESS CODE</td>"
                + "</tr></table>"
                + "</td></tr>"
                + "<tr><td style=\"padding:42px 34px 18px 34px;background:#0b0d10;\">"
                + "<div style=\"color:#72f0a7;font-size:12px;font-weight:800;letter-spacing:4px;margin-bottom:14px;\">USER ACCESS TERMINAL</div>"
                + "<h1 style=\"margin:0;color:#eff3ff;font-size:34px;line-height:1.18;font-weight:800;letter-spacing:0;\">邮箱验证</h1>"
                + "<p style=\"margin:16px 0 0 0;color:#a5a9b2;font-size:16px;line-height:1.8;\">你正在开通 OREP 用户端访问权限，请在注册页面输入以下验证码。</p>"
                + "</td></tr>"
                + "<tr><td align=\"center\" style=\"padding:20px 34px 18px 34px;\">"
                + "<table role=\"presentation\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\"><tr>"
                + digitCells
                + "</tr></table>"
                + "</td></tr>"
                + "<tr><td style=\"padding:4px 34px 30px 34px;\">"
                + "<table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\" style=\"border-top:1px solid #252b30;border-bottom:1px solid #252b30;\">"
                + "<tr>"
                + "<td style=\"padding:18px 0;color:#7d838c;font-size:12px;font-weight:800;letter-spacing:3px;\">VALID WINDOW</td>"
                + "<td align=\"right\" style=\"padding:18px 0;color:#eff3ff;font-size:14px;font-weight:700;\">5 分钟</td>"
                + "</tr>"
                + "<tr>"
                + "<td style=\"padding:0 0 18px 0;color:#7d838c;font-size:12px;font-weight:800;letter-spacing:3px;\">DESTINATION</td>"
                + "<td align=\"right\" style=\"padding:0 0 18px 0;color:#a5a9b2;font-size:13px;\">" + escapeHtml(email) + "</td>"
                + "</tr>"
                + "</table>"
                + "</td></tr>"
                + "<tr><td style=\"padding:0 34px 38px 34px;\">"
                + "<div style=\"border:1px solid #214637;background:#0d1714;padding:16px 18px;color:#b8c0c8;font-size:14px;line-height:1.7;\">"
                + "<strong style=\"color:#72f0a7;letter-spacing:1px;\">SECURITY NOTE</strong><br>"
                + "如果不是你本人操作，请忽略此邮件。OREP 工作人员不会向你索要验证码。"
                + "</div>"
                + "</td></tr>"
                + "<tr><td style=\"padding:18px 34px;background:#07090b;border-top:1px solid #252b30;color:#666c75;font-size:12px;line-height:1.6;\">"
                + "OREP Roadshow Operations · This message was generated automatically."
                + "</td></tr>"
                + "</table>"
                + "</td></tr>"
                + "</table>"
                + "</body></html>";
    }

    private String escapeHtml(String value) {
        if (value == null) {
            return "";
        }
        return value
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\"", "&quot;")
                .replace("'", "&#39;");
    }

    public void register(RegisterRequest request) {
        // 验证验证码
        EmailVerificationCode codeRecord = codeMapper.selectList(
                new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<EmailVerificationCode>()
                        .eq(EmailVerificationCode::getEmail, request.getEmail())
                        .eq(EmailVerificationCode::getCode, request.getCode())
                        .eq(EmailVerificationCode::getUsed, false)
                        .gt(EmailVerificationCode::getExpiredAt, LocalDateTime.now())
                        .orderByDesc(EmailVerificationCode::getCreatedAt)
                        .last("LIMIT 1")
        ).stream().findFirst().orElse(null);

        if (codeRecord == null) {
            throw new RuntimeException("验证码无效或已过期");
        }

        // 标记验证码已使用
        codeRecord.setUsed(true);
        codeMapper.updateById(codeRecord);

        // 检查用户名和邮箱是否已存在
        if (userMapper.findByUsername(request.getUsername()) != null) {
            throw new RuntimeException("用户名已存在");
        }
        if (userMapper.findByEmail(request.getEmail()) != null) {
            throw new RuntimeException("邮箱已注册");
        }

        // 创建用户
        User user = new User();
        user.setTenantId(request.getTenantId() != null ? request.getTenantId() : 1L);
        user.setUsername(request.getUsername());
        user.setPassword(cn.hutool.crypto.digest.BCrypt.hashpw(request.getPassword(), cn.hutool.crypto.digest.BCrypt.gensalt()));
        user.setEmail(request.getEmail());
        user.setRole("STUDENT");
        userMapper.insert(user);
    }

    public LoginResponse login(LoginRequest request) {
        User user = userMapper.findByUsername(request.getUsername());
        if (user == null) {
            throw new RuntimeException("用户名或密码错误");
        }

        if (!cn.hutool.crypto.digest.BCrypt.checkpw(request.getPassword(), user.getPassword())) {
            throw new RuntimeException("用户名或密码错误");
        }

        String token = jwtUtil.generateToken(user.getId(), user.getUsername(), user.getRole(), user.getTenantId());

        LoginResponse response = new LoginResponse();
        response.setToken(token);
        LoginResponse.UserInfo userInfo = new LoginResponse.UserInfo();
        userInfo.setId(user.getId());
        userInfo.setUsername(user.getUsername());
        userInfo.setEmail(user.getEmail());
        userInfo.setRole(user.getRole());
        userInfo.setTenantId(user.getTenantId());
        response.setUser(userInfo);

        return response;
    }

    public boolean checkToken(String token) {
        if (token != null && token.startsWith("Bearer ")) {
            token = token.substring(7);
            return jwtUtil.validateToken(token);
        }
        return false;
    }
}
