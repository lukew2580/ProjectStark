package com.hardwareless.ai.network

import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Hardwareless AI — HV01 v2 Kotlin Bridge
 * Native Android implementation of the hypervector swarm protocol.
 */
object HV01 {
    const val MAGIC = 0x48563031 // 'HV01'
    const val VERSION: Byte = 2
    
    // Flags
    const val FLAG_ENCRYPTED: Byte = 0x01
    const val FLAG_HEARTBEAT: Byte = 0x02

    /**
     * Packs a 10,000-D ByteArray hypervector into a v2 binary packet.
     */
    fun pack(
        vector: ByteArray,
        nodeId: Int = 0,
        seqId: Int = 0,
        flags: Byte = 0,
        nonce: ByteArray = ByteArray(24)
    ): ByteArray {
        val payloadSize = vector.size
        // Header: magic(4) + version(1) + node_id(4) + seq_id(4) + flags(1) + nonce(24) + length(4) = 43 bytes
        val buffer = ByteBuffer.allocate(43 + payloadSize)
        buffer.order(ByteOrder.BIG_ENDIAN)
        
        // Write Header
        buffer.putInt(MAGIC)
        buffer.put(VERSION)
        buffer.putInt(nodeId)
        buffer.putInt(seqId)
        buffer.put(flags)
        buffer.put(nonce)
        buffer.putInt(payloadSize)
        
        // Write Payload
        buffer.put(vector)
        
        return buffer.array()
    }

    /**
     * Unpacks a binary packet into header components and raw payload.
     */
    fun unpack(data: ByteArray): UnpackedPacket? {
        if (data.size < 43) return null
        
        val buffer = ByteBuffer.wrap(data)
        buffer.order(ByteOrder.BIG_ENDIAN)
        
        val magic = buffer.int
        if (magic != MAGIC) return null
        
        val version = buffer.get()
        val nodeId = buffer.int
        val seqId = buffer.int
        val flags = buffer.get()
        val nonce = ByteArray(24)
        buffer.get(nonce)
        val length = buffer.int
        
        if (data.size < 43 + length) return null
        
        val payload = ByteArray(length)
        buffer.get(payload)
        
        return UnpackedPacket(nodeId, seqId, flags, nonce, payload)
    }

    data class UnpackedPacket(
        val nodeId: Int,
        val seqId: Int,
        val flags: Byte,
        val nonce: ByteArray,
        val payload: ByteArray
    )
}
