package com.pokego.plus

import android.util.Log
import javax.crypto.Cipher
import javax.crypto.spec.SecretKeySpec
import java.security.SecureRandom

/**
 * SFIDA AES-128 authentication handshake.
 *
 * Ported from yohanes/pgpemu (MIT) and Jesus805/pokeball-rs (MIT).
 * See plus/goplusplus/crypto.py for the Python reference and REFERENCES.md for sources.
 *
 * Requires real device keys in Config — see Config.kt.
 */
class SFIDAAuth {

    enum class State { INIT, CHALLENGE_SENT, AUTHENTICATED }

    var state = State.INIT
        private set

    private var sessionKey: ByteArray? = null
    private var sessionNonce: ByteArray? = null

    val isAuthenticated get() = state == State.AUTHENTICATED

    // ── Public API ─────────────────────────────────────────────────────────────

    /** Call when phone writes to CHAR_CENTRAL_TO_SFIDA. Returns bytes to notify, or null. */
    fun handleWrite(data: ByteArray): ByteArray? = when (state) {
        State.INIT           -> handleInit()
        State.CHALLENGE_SENT -> { handleResponse(data); null }
        State.AUTHENTICATED  -> null
    }

    fun reset() {
        state        = State.INIT
        sessionKey   = null
        sessionNonce = null
    }

    // ── Handshake steps ────────────────────────────────────────────────────────

    private fun handleInit(): ByteArray? {
        return try {
            val (challenge, key, nonce) = buildChallenge()
            sessionKey   = key
            sessionNonce = nonce
            state = State.CHALLENGE_SENT
            Log.i(TAG, "SFIDA: challenge built (${challenge.size} bytes)")
            challenge
        } catch (e: Exception) {
            Log.e(TAG, "SFIDA: failed to build challenge — check device keys in Config", e)
            null
        }
    }

    private fun handleResponse(data: ByteArray) {
        val key   = sessionKey   ?: return
        val nonce = sessionNonce ?: return
        val expected = aesHash(Config.deviceKey, nonce, key, 0x01).copyOf(20)
        if (data.size >= 20 && data.copyOf(20).contentEquals(expected)) {
            Log.i(TAG, "SFIDA: authenticated")
            state = State.AUTHENTICATED
        } else {
            Log.w(TAG, "SFIDA: auth FAILED — wrong keys or wrong device")
            reset()
        }
    }

    // ── Challenge builder ──────────────────────────────────────────────────────

    private data class Challenge(val bytes: ByteArray, val sessionKey: ByteArray, val nonce: ByteArray)

    private fun buildChallenge(): Challenge {
        val nonce      = SecureRandom().generateSeed(16)
        val sessionKey = SecureRandom().generateSeed(16)
        val btAddrRev  = Config.btAddr.reversedArray()

        // XOR session key with nonce for inner ECB
        val innerInput = ByteArray(16) { i -> (sessionKey[i].toInt() xor nonce[i].toInt()).toByte() }
        val innerEnc   = ecb(Config.deviceKey, innerInput)

        // Plaintext [0:54]
        var plaintext = btAddrRev + sessionKey + nonce + innerEnc

        // Hash of first 54 bytes
        val innerHash = aesHash(Config.deviceKey, nonce, plaintext)

        // Full 80-byte plaintext
        plaintext = plaintext + innerHash + Config.flashData.copyOf(10)

        val encChallenge = aesCtr(Config.deviceKey, nonce, plaintext)
        val outerHash    = aesHash(Config.deviceKey, nonce, encChallenge)

        val challenge = ByteArray(4).also { it.putInt32LE(1) } +  // state = 1
                nonce + encChallenge + outerHash + Config.btAddr + Config.blob.copyOf(256)

        check(challenge.size == 378) { "Challenge size ${challenge.size} != 378" }
        return Challenge(challenge, sessionKey, nonce)
    }

    // ── AES primitives ─────────────────────────────────────────────────────────

    private fun ecb(key: ByteArray, block: ByteArray): ByteArray {
        val cipher = Cipher.getInstance("AES/ECB/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, SecretKeySpec(key, "AES"))
        return cipher.doFinal(block)
    }

    private fun ctrBlock(key: ByteArray, baseNonce: ByteArray, counter: Int): ByteArray {
        val nonce = ByteArray(16)
        nonce[0] = 0x00
        baseNonce.copyInto(nonce, destinationOffset = 1, startIndex = 0, endIndex = 12)
        nonce[13] = 0x00
        nonce[14] = (counter and 0xFF).toByte()
        nonce[15] = ((counter shr 8) and 0xFF).toByte()
        return ecb(key, nonce)
    }

    private fun aesCtr(key: ByteArray, baseNonce: ByteArray, data: ByteArray): ByteArray {
        val out = ByteArray(data.size)
        var counter = 1
        var offset  = 0
        while (offset < data.size) {
            val keystream = ctrBlock(key, baseNonce, counter++)
            val len = minOf(16, data.size - offset)
            for (i in 0 until len) out[offset + i] = (data[offset + i].toInt() xor keystream[i].toInt()).toByte()
            offset += len
        }
        return out
    }

    internal fun aesHash(key: ByteArray, baseNonce: ByteArray, data: ByteArray, firstByte: Int = 0x39): ByteArray {
        val nonce = ByteArray(16)
        nonce[0] = firstByte.toByte()
        baseNonce.copyInto(nonce, destinationOffset = 1, startIndex = 1, endIndex = 13)
        nonce[13] = 0x00
        nonce[14] = (data.size and 0xFF).toByte()
        nonce[15] = ((data.size shr 8) and 0xFF).toByte()

        var state = ecb(key, nonce)
        var offset = 0
        while (offset < data.size) {
            val block = ByteArray(16)
            data.copyInto(block, 0, offset, minOf(offset + 16, data.size))
            state = ecb(key, ByteArray(16) { i -> (state[i].toInt() xor block[i].toInt()).toByte() })
            offset += 16
        }
        return state
    }

    companion object {
        private const val TAG = "SFIDAAuth"
    }
}

// ── Extension ─────────────────────────────────────────────────────────────────

private fun ByteArray.putInt32LE(value: Int) {
    this[0] = (value and 0xFF).toByte()
    this[1] = ((value shr 8) and 0xFF).toByte()
    this[2] = ((value shr 16) and 0xFF).toByte()
    this[3] = ((value shr 24) and 0xFF).toByte()
}

private operator fun ByteArray.plus(other: ByteArray): ByteArray {
    val result = ByteArray(this.size + other.size)
    this.copyInto(result)
    other.copyInto(result, this.size)
    return result
}
