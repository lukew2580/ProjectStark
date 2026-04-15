import Foundation

/**
 Hardwareless AI — HV01 v2 Swift Bridge
 Native iOS implementation of the hypervector swarm protocol.
 */

public struct HV01 {
    // Protocol Constants
    static let magic: UInt32 = 0x48563031 // 'HV01' in Big Endian
    static let version: UInt8 = 2
    
    // Flags
    public struct Flags: OptionSet {
        public let rawValue: UInt8
        public init(rawValue: UInt8) { self.rawValue = rawValue }
        
        static let encrypted = Flags(rawValue: 0x01)
        static let heartbeat = Flags(rawValue: 0x02)
    }

    /// Header Structure (43 Bytes for v2)
    /// magic(4) + version(1) + node_id(4) + seq_id(4) + flags(1) + nonce(24) + length(4)
    public struct Header {
        let nodeId: UInt32
        let seqId: UInt32
        let flags: Flags
        let nonce: Data
        let length: UInt32
        
        func pack() -> Data {
            var data = Data()
            var m_big = HV01.magic.bigEndian
            var v = HV01.version
            var n_big = nodeId.bigEndian
            var s_big = seqId.bigEndian
            var f = flags.rawValue
            var l_big = length.bigEndian
            
            data.append(Data(bytes: &m_big, count: 4))
            data.append(v)
            data.append(Data(bytes: &n_big, count: 4))
            data.append(Data(bytes: &s_big, count: 4))
            data.append(f)
            data.append(nonce) // Nonce should already be 24 bytes
            data.append(Data(bytes: &l_big, count: 4))
            
            return data
        }
    }

    /// Packs a 10,000-D int8 vector into a binary packet
    public static func pack(vector: [Int8], nodeId: UInt32, seqId: UInt32, key: Data? = nil) -> Data {
        var payload = Data(bytes: vector, count: vector.count)
        var flags = Flags()
        var nonce = Data(count: 24)
        
        if let _ = key {
            // Note: Native SwiftSodium encryption logic would go here
            // For now, we set the flag to signal encryption capability
            flags.insert(.encrypted)
            // Mock nonce for protocol parity check
        }
        
        let header = Header(
            nodeId: nodeId,
            seqId: seqId,
            flags: flags,
            nonce: nonce,
            length: UInt32(payload.count)
        )
        
        var packet = header.pack()
        packet.append(payload)
        return packet
    }
}
