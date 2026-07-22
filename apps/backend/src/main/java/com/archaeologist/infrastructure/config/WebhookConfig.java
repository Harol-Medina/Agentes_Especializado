package com.archaeologist.infrastructure.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;

/**
 * HMAC-SHA256 webhook signature validation.
 * Validates that incoming webhooks from the Analyzer are authentic.
 */
@Component
public class WebhookConfig {

    private static final String HMAC_ALGORITHM = "HmacSHA256";
    private static final String SIGNATURE_PREFIX = "sha256=";

    private final String webhookSecret;

    public WebhookConfig(@Value("${app.webhook-secret:shared_webhook_secret}") String webhookSecret) {
        this.webhookSecret = webhookSecret;
    }

    /**
     * Validates the HMAC-SHA256 signature from the X-Webhook-Signature header.
     *
     * @param payload   the raw request body
     * @param signature the value of X-Webhook-Signature header (e.g., "sha256=abcdef...")
     * @return true if the signature is valid
     */
    public boolean validateSignature(String payload, String signature) {
        if (signature == null || payload == null) {
            return false;
        }

        String expectedSignature = computeSignature(payload);
        return constantTimeEquals(SIGNATURE_PREFIX + expectedSignature, signature);
    }

    /**
     * Computes the HMAC-SHA256 hex digest for a payload.
     */
    private String computeSignature(String payload) {
        try {
            Mac mac = Mac.getInstance(HMAC_ALGORITHM);
            SecretKeySpec keySpec = new SecretKeySpec(
                webhookSecret.getBytes(StandardCharsets.UTF_8), HMAC_ALGORITHM);
            mac.init(keySpec);
            byte[] hash = mac.doFinal(payload.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (NoSuchAlgorithmException | InvalidKeyException e) {
            throw new RuntimeException("Failed to compute HMAC-SHA256 signature", e);
        }
    }

    /**
     * Constant-time string comparison to prevent timing attacks.
     */
    private boolean constantTimeEquals(String a, String b) {
        if (a.length() != b.length()) {
            return false;
        }
        int result = 0;
        for (int i = 0; i < a.length(); i++) {
            result |= a.charAt(i) ^ b.charAt(i);
        }
        return result == 0;
    }
}
