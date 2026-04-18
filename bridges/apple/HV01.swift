import Foundation

/**
 * Hardwareless AI — HV01 v3 Swift Bridge
 * Native iOS implementation of the hypervector swarm protocol.
 * Supports multi-layer encryption (XOR +).
 */

public struct HV01 {
    // Protocol Constants
    static let magic: UInt32 = 0x48563031 // 'HV01' in Big Endian
    static let version: UInt8 = 3 // v3 protocol
    
    public static let headerSize: Int = 43
    
    // Flags
    public struct Flags: OptionSet {
        public let rawValue: UInt8
        public init(rawValue: UInt8) { self.rawValue = rawValue }
        
        static let encrypted = Flags(rawValue: 0x01)
        static let heartbeat = Flags(rawValue: 0x02)
        static let compressed = Flags(rawValue: 0x04)
        static let broadcast = Flags(rawValue: 0x08)
        static let acknowledge = Flags(rawValue: 0x10)
    }

    /// Header Structure (v3 - 43 Bytes)
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
            data.append(nonce)
            data.append(Data(bytes: &l_big, count: 4))
            
            return data
        }
    }

    /// Pack a hypervector into v3 binary packet
    public static func pack(vector: [Int8], nodeId: UInt32, seqId: UInt32, flags: Flags = []) -> Data {
        var payload = Data(bytes: vector, count: vector.count)
        var nonce = Data(count: 24)
        
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

    /// Unpack binary packet
    public static func unpack(_ data: Data) -> UnpackedPacket? {
        guard data.count >= headerSize else { return nil }
        
        let buffer = data.withUnsafeBytes { ptr -> UInt32 in
            ptr.load(fromByteOffset: 0, as: UInt32.self).bigEndian
        }
        
        guard buffer == magic else { return nil }
        
        let ver = data[4]
        guard ver == version else { return nil }
        
        let nodeId = data.subdata(in: 5..<9).withUnsafeBytes { $0.load(as: UInt32.self).bigEndian }
        let seqId = data.subdata(in: 9..<13).withUnsafeBytes { $0.load(as: UInt32.self).bigEndian }
        let fl = data[13]
        
        let nonce = data.subdata(in: 14..<38)
        
        let length = data.subdata(in: 38..<42).withUnsafeBytes { $0.load(as: UInt32.self).bigEndian }
        
        guard data.count >= headerSize + Int(length) else { return nil }
        
        let payload = data.subdata(in: headerSize..<(headerSize + Int(length)))
        
        return UnpackedPacket(nodeId: nodeId, seqId: seqId, flags: Flags(rawValue: fl), nonce: nonce, payload: payload)
    }

    /// XOR encrypt
    public static func encrypt(_ data: Data, key: Data) -> Data {
        guard key.count > 0 else { return data }
        
        var encrypted = Data(count: data.count)
        let keyBytes = key.prefix(24)
        
        for i in 0..<data.count {
            encrypted[i] = data[i] ^ keyBytes[i % keyBytes.count]
        }
        
        return encrypted
    }

    /// XOR decrypt (same as encrypt)
    public static func decrypt(_ data: Data, key: Data) -> Data {
        return encrypt(data, key: key)
    }

    /// Verify packet integrity
    public static func verifyPacket(_ data: Data) -> Bool {
        guard data.count >= 4 else { return false }
        
        let magicBytes = data.prefix(4)
        let magicValue = magicBytes.withUnsafeBytes { $0.load(as: UInt32.self).bigEndian }
        
        return magicValue == magic
    }

    public struct UnpackedPacket {
        public let nodeId: UInt32
        public let seqId: UInt32
        public let flags: Flags
        public let nonce: Data
        public let payload: Data
    }
}