package com.pokego.plus

import android.bluetooth.*
import android.bluetooth.BluetoothGatt.GATT_SUCCESS
import android.content.Context
import android.os.Handler
import android.os.Looper
import android.util.Log

/**
 * Handles all GATT server events: connect/disconnect, reads, writes, CCCD.
 *
 * LED commands from Pokemon GO arrive via CHAR_LED writes.
 * SFIDA auth exchange goes through CHAR_CENTRAL_TO_SFIDA writes +
 * CHAR_SFIDA_COMMANDS notifications.
 * Button presses are sent as notifications on CHAR_BUTTON.
 */
class GattServerCallback(
    private val context: Context,
    private val onConnected:    (BluetoothDevice) -> Unit,
    private val onDisconnected: (BluetoothDevice) -> Unit,
    private val onLedCommand:   (ByteArray) -> Unit,
) : BluetoothGattServerCallback() {

    var gattServer: BluetoothGattServer? = null

    private val auth = SFIDAAuth()
    private val connectedDevices = mutableSetOf<BluetoothDevice>()
    private val notifyEnabled    = mutableSetOf<BluetoothDevice>() // for CHAR_BUTTON
    private val sfidaNotifyEnabled = mutableSetOf<BluetoothDevice>()
    private val deviceMtu        = mutableMapOf<String, Int>()
    private val handler          = Handler(Looper.getMainLooper())

    val hasConnectedDevice get() = connectedDevices.isNotEmpty()

    // ── Connection ─────────────────────────────────────────────────────────────

    override fun onConnectionStateChange(device: BluetoothDevice, status: Int, newState: Int) {
        if (newState == BluetoothProfile.STATE_CONNECTED) {
            Log.i(TAG, "Connected: ${device.address}")
            connectedDevices += device
            onConnected(device)
        } else {
            Log.i(TAG, "Disconnected: ${device.address}")
            connectedDevices -= device
            notifyEnabled -= device
            sfidaNotifyEnabled -= device
            deviceMtu.remove(device.address)
            auth.reset()
            onDisconnected(device)
        }
    }

    override fun onMtuChanged(device: BluetoothDevice, mtu: Int) {
        deviceMtu[device.address] = mtu
        Log.d(TAG, "MTU changed: ${device.address} → $mtu")
    }

    // ── Reads ──────────────────────────────────────────────────────────────────

    override fun onCharacteristicReadRequest(
        device: BluetoothDevice, requestId: Int, offset: Int,
        characteristic: BluetoothGattCharacteristic
    ) {
        val value: ByteArray = when (characteristic.uuid) {
            GattProfile.CHAR_BATTERY_LEVEL -> byteArrayOf(GattProfile.BATTERY_LEVEL.toByte())
            GattProfile.CHAR_FW_VERSION    -> byteArrayOf(0x00, 0x01)
            GattProfile.CHAR_SFIDA_TO_CENTRAL -> characteristic.value ?: byteArrayOf(0x00)
            else -> byteArrayOf()
        }
        gattServer?.sendResponse(device, requestId, GATT_SUCCESS, offset,
            if (offset < value.size) value.copyOfRange(offset, value.size) else byteArrayOf())
    }

    // ── Writes ─────────────────────────────────────────────────────────────────

    override fun onCharacteristicWriteRequest(
        device: BluetoothDevice, requestId: Int, characteristic: BluetoothGattCharacteristic,
        preparedWrite: Boolean, responseNeeded: Boolean, offset: Int, value: ByteArray
    ) {
        if (responseNeeded) gattServer?.sendResponse(device, requestId, GATT_SUCCESS, 0, null)

        when (characteristic.uuid) {
            GattProfile.CHAR_LED -> {
                Log.d(TAG, "LED: ${value.toHex()}")
                onLedCommand(value)
            }
            GattProfile.CHAR_CENTRAL_TO_SFIDA -> {
                Log.d(TAG, "SFIDA write: ${value.toHex()}")
                val response = auth.handleWrite(value)
                if (response != null) sendSfidaNotification(device, response)
            }
            else -> Log.d(TAG, "Write to ${characteristic.uuid}: ${value.toHex()}")
        }
    }

    // ── CCCD (notification enable) ─────────────────────────────────────────────

    override fun onDescriptorWriteRequest(
        device: BluetoothDevice, requestId: Int, descriptor: BluetoothGattDescriptor,
        preparedWrite: Boolean, responseNeeded: Boolean, offset: Int, value: ByteArray
    ) {
        if (responseNeeded) gattServer?.sendResponse(device, requestId, GATT_SUCCESS, 0, null)
        val enabled = value.contentEquals(BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE)
        when (descriptor.characteristic.uuid) {
            GattProfile.CHAR_BUTTON        -> if (enabled) notifyEnabled += device else notifyEnabled -= device
            GattProfile.CHAR_SFIDA_COMMANDS -> if (enabled) sfidaNotifyEnabled += device else sfidaNotifyEnabled -= device
        }
        Log.d(TAG, "Notify ${descriptor.characteristic.uuid} → $enabled for ${device.address}")
    }

    // ── Button notifications ───────────────────────────────────────────────────

    fun sendButtonPress(device: BluetoothDevice)   = sendButtonPayload(device, GattProfile.BUTTON_PRESSED)
    fun sendButtonRelease(device: BluetoothDevice) = sendButtonPayload(device, GattProfile.BUTTON_RELEASED)

    private fun sendButtonPayload(device: BluetoothDevice, payload: ByteArray) {
        if (device !in notifyEnabled) return
        val char = gattServer?.getService(GattProfile.SERVICE_LED_BUTTON)
            ?.getCharacteristic(GattProfile.CHAR_BUTTON) ?: return
        char.value = payload
        gattServer?.notifyCharacteristicChanged(device, char, false)
    }

    fun firstConnectedDevice(): BluetoothDevice? = connectedDevices.firstOrNull()

    // ── SFIDA chunked notification ─────────────────────────────────────────────

    private fun sendSfidaNotification(device: BluetoothDevice, data: ByteArray) {
        val char = gattServer?.getService(GattProfile.SERVICE_CERT)
            ?.getCharacteristic(GattProfile.CHAR_SFIDA_COMMANDS) ?: return

        // Also expose via readable characteristic
        gattServer?.getService(GattProfile.SERVICE_CERT)
            ?.getCharacteristic(GattProfile.CHAR_SFIDA_TO_CENTRAL)?.value = data

        val mtu         = deviceMtu[device.address] ?: 23
        val payloadSize = mtu - 3  // ATT overhead

        var offset = 0
        fun sendNext() {
            if (offset >= data.size) return
            val chunk = data.copyOfRange(offset, minOf(offset + payloadSize, data.size))
            char.value = chunk
            gattServer?.notifyCharacteristicChanged(device, char, false)
            offset += payloadSize
            if (offset < data.size) handler.postDelayed(::sendNext, 15)
        }
        sendNext()
    }

    companion object {
        private const val TAG = "GattServerCallback"
        private fun ByteArray.toHex() = joinToString("") { "%02x".format(it) }
    }
}
