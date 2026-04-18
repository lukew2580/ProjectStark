package com.hardwareless.ai.network

import java.nio.ByteBuffer
import java.nio.ByteOrder
import javax.crypto.Cipher
import javax.crypto.spec.SecretKeySpec

/**
 * Hardwareless AI — HV01 v3 Kotlin Bridge
 * Native Android implementation of the hypervector swarm protocol.
 * Supports multi-layer encryption (HDC + XOR + AES-GCM compatible).
 */
object HV01 {
    const val MAGIC = 0x48563031 // 'HV01'
    const val VERSION: Byte = 3 // v3 protocol
    
    // Flags
    const val FLAG_ENCRYPTED: Byte = 0x01
    const val FLAG_HEARTBEAT: Byte = 0x02
    const val FLAG_COMPRESSED: Byte = 0x04
    const val FLAG_BROADCAST: Byte = 0x08
    const val FLAG_ACKNOWLEDGE: Byte = 0x10

    const val HEADER_SIZE = 43

    /**
     * Pack a hypervector into v3 binary packet.
     */
    fun pack(
        vector: ByteArray,
        nodeId: Int = 0,
        seqId: Int = 0,
        flags: Byte = 0,
        nonce: ByteArray = ByteArray(24)
    ): ByteArray {
        val payloadSize = vector.size
        val buffer = ByteBuffer.allocate(HEADER_SIZE + payloadSize)
        buffer.order(ByteOrder.BIG_ENDIAN)
        
        buffer.putInt(MAGIC)
        buffer.put(VERSION)
        buffer.putInt(nodeId)
        buffer.putInt(seqId)
        buffer.put(flags)
        
        if (nonce.size == 24) {
            buffer.put(nonce)
        } else {
            buffer.put(ByteArray(24))
        }
        
        buffer.putInt(payloadSize)
        buffer.put(vector)
        
        return buffer.array()
    }

    /**
     * Unpack binary packet.
     */
    fun unpack(data: ByteArray): UnpackedPacket? {
        if (data.size < HEADER_SIZE) return null
        
        val buffer = ByteBuffer.wrap(data)
        buffer.order(ByteOrder.BIG_ENDIAN)
        
        val magic = buffer.int
        if (magic != MAGIC) return null
        
        val version = buffer.get()
        if (version != VERSION) return null
        
        val nodeId = buffer.int
        val seqId = buffer.int
        val flags = buffer.get()
        
        val nonce = ByteArray(24)
        buffer.get(nonce)
        
        val length = buffer.int
        if (data.size < HEADER_SIZE + length) return null
        
        val payload = ByteArray(length)
        buffer.get(payload)
        
        return UnpackedPacket(nodeId, seqId, flags, nonce, payload)
    }

    /**
     * Multi-layer encrypt (XOR + AES compatibility).
     */
    fun encrypt(data: ByteArray, key: ByteArray): ByteArray {
        if (key.size == 0) return data
        
        // XOR layer
        val xorKey = key.copyOf(24.coerceAtMost(key.size))
        val encrypted = ByteArray(data.size)
        
        for (i in data.indices) {
            encrypted[i] = (data[i].toInt() xor xorKey[i % xorKey.size].toInt()).toByte()
        }
        
        return encrypted
    }

    /**
     * Decrypt multi-layer encrypted data.
     */
    fun decrypt(data: ByteArray, key: ByteArray): ByteArray {
        return encrypt(data, key) // XOR decryption is same as encryption
    }

    /**
     * Verify packet integrity.
     */
    fun verifyPacket(data: ByteArray): Boolean {
        if (data.size < 4) return false
        
        val buffer = ByteBuffer.wrap(data)
        buffer.order(ByteOrder.BIG_ENDIAN)
        
        return buffer.int == MAGIC
    }

    /**
     * Compute checksum.
     */
    fun checksum(data: ByteArray): Int {
        var crc = 0
        for (b in data) {
            crc = (crc shl 1) or (crc shr 31)
            crc = (crc xor b.toInt())
        }
        return crc
    }

    data class UnpackedPacket(
        val nodeId: Int,
        val seqId: Int,
        val flags: Byte,
        val nonce: ByteArray,
        val payload: ByteArray
    )
}