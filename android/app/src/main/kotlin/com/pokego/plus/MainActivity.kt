package com.pokego.plus

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

class MainActivity : AppCompatActivity() {

    private lateinit var tvStatus: TextView
    private lateinit var btnToggle: Button
    private var running = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        tvStatus  = findViewById(R.id.tvStatus)
        btnToggle = findViewById(R.id.btnToggle)

        btnToggle.setOnClickListener {
            if (running) stopService() else startService()
        }

        requestPermissions()
    }

    private fun startService() {
        ContextCompat.startForegroundService(this, Intent(this, GOPlusService::class.java))
        running = true
        tvStatus.text  = "Running — advertising as\n'${GattProfile.DEVICE_NAME}'"
        btnToggle.text = "Stop"
    }

    private fun stopService() {
        stopService(Intent(this, GOPlusService::class.java))
        running = false
        tvStatus.text  = "Stopped"
        btnToggle.text = "Start"
    }

    private fun requestPermissions() {
        val needed = mutableListOf<String>()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            needed += Manifest.permission.BLUETOOTH_ADVERTISE
            needed += Manifest.permission.BLUETOOTH_CONNECT
        } else {
            needed += Manifest.permission.BLUETOOTH
            needed += Manifest.permission.BLUETOOTH_ADMIN
        }
        needed += Manifest.permission.ACCESS_FINE_LOCATION
        needed += Manifest.permission.READ_EXTERNAL_STORAGE

        val missing = needed.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (missing.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, missing.toTypedArray(), 1)
        }
    }
}
