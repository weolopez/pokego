package com.pokego.plus

import android.bluetooth.BluetoothAdapter
import android.bluetooth.le.*
import android.os.ParcelUuid
import android.util.Log

class GOPlusAdvertiser(private val adapter: BluetoothAdapter) {

    private var callback: AdvertiseCallback? = null

    fun start() {
        val le = adapter.bluetoothLeAdvertiser
        if (le == null) {
            Log.e(TAG, "BluetoothLeAdvertiser not available on this device")
            return
        }

        adapter.name = GattProfile.DEVICE_NAME

        val settings = AdvertiseSettings.Builder()
            .setAdvertiseMode(AdvertiseSettings.ADVERTISE_MODE_LOW_LATENCY)
            .setConnectable(true)
            .setTimeout(0)
            .setTxPowerLevel(AdvertiseSettings.ADVERTISE_TX_POWER_HIGH)
            .build()

        val data = AdvertiseData.Builder()
            .setIncludeDeviceName(true)
            .addServiceUuid(ParcelUuid(GattProfile.SERVICE_LED_BUTTON))
            .addManufacturerData(GattProfile.MANUFACTURER_ID, byteArrayOf(0xC5.toByte(), 0x21, 0x00))
            .build()

        callback = object : AdvertiseCallback() {
            override fun onStartSuccess(settingsInEffect: AdvertiseSettings) {
                Log.i(TAG, "Advertising started as '${GattProfile.DEVICE_NAME}'")
            }
            override fun onStartFailure(errorCode: Int) {
                Log.e(TAG, "Advertising failed: error $errorCode")
            }
        }

        le.startAdvertising(settings, data, callback!!)
    }

    fun stop() {
        callback?.let {
            adapter.bluetoothLeAdvertiser?.stopAdvertising(it)
            callback = null
            Log.i(TAG, "Advertising stopped")
        }
    }

    companion object { private const val TAG = "GOPlusAdvertiser" }
}
