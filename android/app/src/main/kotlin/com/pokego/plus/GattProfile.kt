package com.pokego.plus

import java.util.UUID

object GattProfile {

    const val DEVICE_NAME = "Pokemon GO Plus +"

    // Services
    val SERVICE_LED_BUTTON: UUID = UUID.fromString("21c50462-67cb-63a3-5c4c-82b5b9939aeb")
    val SERVICE_CERT:       UUID = UUID.fromString("bbe87709-5b89-4433-ab7f-8b8eef0d8e37")
    val SERVICE_BATTERY:    UUID = UUID.fromString("0000180f-0000-1000-8000-00805f9b34fb")

    // LED / Button characteristics
    val CHAR_LED:            UUID = UUID.fromString("21c50462-67cb-63a3-5c4c-82b5b9939aec") // write
    val CHAR_BUTTON:         UUID = UUID.fromString("21c50462-67cb-63a3-5c4c-82b5b9939aed") // notify
    val CHAR_UNKNOWN_WRITE:  UUID = UUID.fromString("21c50462-67cb-63a3-5c4c-82b5b9939aee") // write
    val CHAR_UPDATE_REQUEST: UUID = UUID.fromString("21c50462-67cb-63a3-5c4c-82b5b9939aef") // write
    val CHAR_FW_VERSION:     UUID = UUID.fromString("21c50462-67cb-63a3-5c4c-82b5b9939af0") // read

    // Certificate / SFIDA characteristics
    val CHAR_CENTRAL_TO_SFIDA: UUID = UUID.fromString("bbe87709-5b89-4433-ab7f-8b8eef0d8e38") // write
    val CHAR_SFIDA_COMMANDS:   UUID = UUID.fromString("bbe87709-5b89-4433-ab7f-8b8eef0d8e39") // notify
    val CHAR_SFIDA_TO_CENTRAL: UUID = UUID.fromString("bbe87709-5b89-4433-ab7f-8b8eef0d8e3a") // read

    // Battery
    val CHAR_BATTERY_LEVEL: UUID = UUID.fromString("00002a19-0000-1000-8000-00805f9b34fb") // read

    // Descriptor
    val CCCD: UUID = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")

    // Button payloads
    val BUTTON_PRESSED  = byteArrayOf(0x03.toByte(), 0xFF.toByte())
    val BUTTON_RELEASED = byteArrayOf(0x00, 0x00)

    const val MANUFACTURER_ID = 0x0462 // Nintendo Co. Ltd.
    const val BATTERY_LEVEL   = 80
}
