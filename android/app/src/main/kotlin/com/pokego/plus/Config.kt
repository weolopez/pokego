package com.pokego.plus

import android.content.Context
import android.util.Log
import org.json.JSONObject
import java.io.File

/**
 * Loads device key material from /sdcard/goplusplus/device_keys.json.
 *
 * Required keys:
 *   bt_addr    — 12 hex chars  (6-byte Bluetooth MAC of your real GO Plus)
 *   device_key — 32 hex chars  (16-byte AES key from OTP flash)
 *   blob       — 512 hex chars (256-byte cert blob from OTP flash)
 *   flash_data — 20 hex chars  (10-byte device flash data)
 *
 * Extraction tool: https://github.com/Jesus805/Suota-Go-Plus
 * Writeup: https://coderjesus.com/blog/pgp-suota/
 *
 * Without real keys the SFIDA handshake will fail and Pokemon GO will not
 * accept the connection.
 */
object Config {

    private const val TAG       = "Config"
    private const val KEYS_PATH = "/sdcard/goplusplus/device_keys.json"

    lateinit var btAddr:    ByteArray  // 6 bytes
    lateinit var deviceKey: ByteArray  // 16 bytes
    lateinit var blob:      ByteArray  // 256 bytes
    lateinit var flashData: ByteArray  // 10 bytes

    private var loaded = false

    fun load(context: Context) {
        if (loaded) return
        val file = File(KEYS_PATH)
        if (!file.exists()) {
            Log.e(TAG, "device_keys.json not found at $KEYS_PATH — auth will fail")
            loadDefaults()
            return
        }
        try {
            val json = JSONObject(file.readText())
            btAddr    = json.getString("bt_addr").hexToBytes()
            deviceKey = json.getString("device_key").hexToBytes()
            blob      = json.getString("blob").hexToBytes()
            flashData = json.getString("flash_data").hexToBytes()
            Log.i(TAG, "Device keys loaded from $KEYS_PATH")
            loaded = true
        } catch (e: Exception) {
            Log.e(TAG, "Failed to load device_keys.json: ${e.message}")
            loadDefaults()
        }
    }

    private fun loadDefaults() {
        btAddr    = ByteArray(6)
        deviceKey = ByteArray(16)
        blob      = ByteArray(256)
        flashData = ByteArray(10)
        loaded    = true
    }

    private fun String.hexToBytes(): ByteArray {
        val s = replace(" ", "").replace(":", "")
        return ByteArray(s.length / 2) { i -> s.substring(i * 2, i * 2 + 2).toInt(16).toByte() }
    }
}
