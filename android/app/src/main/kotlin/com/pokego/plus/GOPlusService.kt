package com.pokego.plus

import android.app.*
import android.bluetooth.*
import android.content.Context
import android.content.Intent
import android.os.*
import android.util.Log
import androidx.core.app.NotificationCompat

/**
 * Foreground service that runs the GO Plus + BLE emulator.
 * Stays alive with screen off via a persistent notification.
 *
 * LED command → auto button press logic:
 *   Pattern ID 1–4  (yellow flash) = Pokemon nearby  → press after 500ms
 *   Pattern ID 5–8  (blue flash)   = PokeStop nearby → press after 500ms
 */
class GOPlusService : Service() {

    private lateinit var gattCallback: GattServerCallback
    private lateinit var advertiser: GOPlusAdvertiser
    private var gattServer: BluetoothGattServer? = null
    private val handler = Handler(Looper.getMainLooper())

    override fun onCreate() {
        super.onCreate()
        Config.load(this)
        createNotificationChannel()
        startForeground(NOTIF_ID, buildNotification("Starting…"))
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startEmulator()
        return START_STICKY
    }

    override fun onDestroy() {
        stopEmulator()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    // ── Emulator lifecycle ─────────────────────────────────────────────────────

    private fun startEmulator() {
        val manager = getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
        val adapter = manager.adapter

        if (adapter == null || !adapter.isEnabled) {
            Log.e(TAG, "Bluetooth not enabled")
            updateNotification("Bluetooth not enabled")
            return
        }

        gattCallback = GattServerCallback(
            context       = this,
            onConnected   = { updateNotification("Connected: ${it.address}") },
            onDisconnected = { updateNotification("Waiting for Pokemon GO…") },
            onLedCommand  = ::handleLedCommand,
        )

        gattServer = manager.openGattServer(this, gattCallback).also { server ->
            gattCallback.gattServer = server
            buildGattServices(server)
        }

        advertiser = GOPlusAdvertiser(adapter)
        advertiser.start()

        updateNotification("Advertising as '${GattProfile.DEVICE_NAME}'")
        Log.i(TAG, "Emulator started")
    }

    private fun stopEmulator() {
        advertiser.stop()
        gattServer?.close()
        gattServer = null
        Log.i(TAG, "Emulator stopped")
    }

    // ── GATT service setup ─────────────────────────────────────────────────────

    private fun buildGattServices(server: BluetoothGattServer) {
        // Battery service
        server.addService(BluetoothGattService(GattProfile.SERVICE_BATTERY, BluetoothGattService.SERVICE_TYPE_PRIMARY).apply {
            addCharacteristic(char(GattProfile.CHAR_BATTERY_LEVEL,
                BluetoothGattCharacteristic.PROPERTY_READ or BluetoothGattCharacteristic.PROPERTY_NOTIFY,
                BluetoothGattCharacteristic.PERMISSION_READ).also { addCCCD(it) })
        })

        // LED/Button service
        server.addService(BluetoothGattService(GattProfile.SERVICE_LED_BUTTON, BluetoothGattService.SERVICE_TYPE_PRIMARY).apply {
            addCharacteristic(char(GattProfile.CHAR_LED,
                BluetoothGattCharacteristic.PROPERTY_WRITE or BluetoothGattCharacteristic.PROPERTY_WRITE_NO_RESPONSE,
                BluetoothGattCharacteristic.PERMISSION_WRITE))
            addCharacteristic(char(GattProfile.CHAR_BUTTON,
                BluetoothGattCharacteristic.PROPERTY_NOTIFY,
                BluetoothGattCharacteristic.PERMISSION_READ).also { addCCCD(it) })
            addCharacteristic(char(GattProfile.CHAR_UNKNOWN_WRITE,
                BluetoothGattCharacteristic.PROPERTY_WRITE or BluetoothGattCharacteristic.PROPERTY_WRITE_NO_RESPONSE,
                BluetoothGattCharacteristic.PERMISSION_WRITE))
            addCharacteristic(char(GattProfile.CHAR_UPDATE_REQUEST,
                BluetoothGattCharacteristic.PROPERTY_WRITE or BluetoothGattCharacteristic.PROPERTY_WRITE_NO_RESPONSE,
                BluetoothGattCharacteristic.PERMISSION_WRITE))
            addCharacteristic(char(GattProfile.CHAR_FW_VERSION,
                BluetoothGattCharacteristic.PROPERTY_READ,
                BluetoothGattCharacteristic.PERMISSION_READ).also { it.value = byteArrayOf(0x00, 0x01) })
        })

        // Certificate / SFIDA service
        server.addService(BluetoothGattService(GattProfile.SERVICE_CERT, BluetoothGattService.SERVICE_TYPE_PRIMARY).apply {
            addCharacteristic(char(GattProfile.CHAR_CENTRAL_TO_SFIDA,
                BluetoothGattCharacteristic.PROPERTY_WRITE or BluetoothGattCharacteristic.PROPERTY_WRITE_NO_RESPONSE,
                BluetoothGattCharacteristic.PERMISSION_WRITE))
            addCharacteristic(char(GattProfile.CHAR_SFIDA_COMMANDS,
                BluetoothGattCharacteristic.PROPERTY_NOTIFY,
                BluetoothGattCharacteristic.PERMISSION_READ).also { addCCCD(it) })
            addCharacteristic(char(GattProfile.CHAR_SFIDA_TO_CENTRAL,
                BluetoothGattCharacteristic.PROPERTY_READ,
                BluetoothGattCharacteristic.PERMISSION_READ))
        })
    }

    private fun char(uuid: java.util.UUID, props: Int, perms: Int) =
        BluetoothGattCharacteristic(uuid, props, perms)

    private fun addCCCD(char: BluetoothGattCharacteristic) {
        char.addDescriptor(BluetoothGattDescriptor(GattProfile.CCCD,
            BluetoothGattDescriptor.PERMISSION_READ or BluetoothGattDescriptor.PERMISSION_WRITE))
    }

    // ── LED command → auto button press ───────────────────────────────────────

    private fun handleLedCommand(data: ByteArray) {
        val patternId = decodeLedPatternId(data)
        Log.d(TAG, "LED pattern_id=$patternId")
        val device = gattCallback.firstConnectedDevice() ?: return

        when (patternId) {
            in 1..4  -> autoPress(device, "Pokemon nearby")
            in 5..8  -> autoPress(device, "PokeStop nearby")
            in 9..12 -> Log.i(TAG, "Catch success")
            in 13..16 -> Log.i(TAG, "Catch failed")
            in 17..20 -> Log.i(TAG, "Spin success")
        }
    }

    private fun decodeLedPatternId(data: ByteArray): Int {
        if (data.size < 4) return 0
        val numPatterns = data[3].toInt() and 0x1F
        var total = 0
        for (i in 0 until numPatterns) {
            val p = 4 + 3 * i
            if (p + 2 >= data.size) break
            total += (data[p + 1].toInt() and 0x0F) +       // red
                     ((data[p + 1].toInt() shr 4) and 0x0F) + // green
                     (data[p + 2].toInt() and 0x0F)           // blue
        }
        return total
    }

    private fun autoPress(device: BluetoothDevice, reason: String) {
        Log.i(TAG, "Auto-press: $reason")
        handler.postDelayed({
            gattCallback.sendButtonPress(device)
            handler.postDelayed({ gattCallback.sendButtonRelease(device) }, 100)
        }, 500)
    }

    // ── Notification ──────────────────────────────────────────────────────────

    private fun createNotificationChannel() {
        val channel = NotificationChannel(CHANNEL_ID, "GO Plus + Emulator",
            NotificationManager.IMPORTANCE_LOW)
        getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
    }

    private fun buildNotification(text: String): Notification =
        NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("GO Plus + Emulator")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.stat_sys_data_bluetooth)
            .setOngoing(true)
            .build()

    private fun updateNotification(text: String) {
        getSystemService(NotificationManager::class.java)
            .notify(NOTIF_ID, buildNotification(text))
    }

    companion object {
        private const val TAG        = "GOPlusService"
        private const val CHANNEL_ID = "goplusplus"
        private const val NOTIF_ID   = 1
    }
}
