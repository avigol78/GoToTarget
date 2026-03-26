import struct
import numpy as np
import os

class TIRadarParser:
    def __init__(self):
        self.magic_word = b'\x02\x01\x04\x03\x06\x05\x08\x07'
        self.header_struct = 'QIIIIIIII' # Magic, Version, TotalLen, Platform, FrameNum, Time, NumObjs, NumTLVs, SubFrameNum
        self.header_size = struct.calcsize(self.header_struct)
        self.tlv_header_struct = 'II' # Type, Length
        self.tlv_header_size = struct.calcsize(self.tlv_header_struct)

    def parse_header(self, data):
        if len(data) < self.header_size:
            return None
        
        header = struct.unpack(self.header_struct, data[:self.header_size])
        if data[:8] != self.magic_word:
            return None
            
        return {
            'version': header[1],
            'total_packet_len': header[2],
            'platform': header[3],
            'frame_number': header[4],
            'time_cpu_cycles': header[5],
            'num_objects': header[6],
            'num_tlvs': header[7],
            'sub_frame_num': header[8]
        }

    def parse_file(self, file_path):
        results = []
        with open(file_path, 'rb') as f:
            content = f.read()
            
        offset = 0
        while offset < len(content):
            # Find magic word
            idx = content.find(self.magic_word, offset)
            if idx == -1:
                break
            
            offset = idx
            header = self.parse_header(content[offset:])
            if not header:
                offset += 8 # Skip and keep searching
                continue
            
            packet_end = offset + header['total_packet_len']
            if packet_end > len(content):
                break # Incomplete packet at end of file
            
            tlv_offset = offset + self.header_size
            tlvs = []
            
            for _ in range(header['num_tlvs']):
                if tlv_offset + self.tlv_header_size > packet_end:
                    break
                
                tlv_type, tlv_len = struct.unpack(self.tlv_header_struct, content[tlv_offset:tlv_offset + self.tlv_header_size])
                tlv_payload = content[tlv_offset + self.tlv_header_size:tlv_offset + self.tlv_header_size + tlv_len]
                
                decoded_data = self.decode_tlv(tlv_type, tlv_payload)
                
                tlvs.append({
                    'type': tlv_type,
                    'length': tlv_len,
                    'payload': tlv_payload,
                    'decoded': decoded_data
                })
                tlv_offset += self.tlv_header_size + tlv_len
                
            results.append({
                'header': header,
                'tlvs': tlvs
            })
            offset = packet_end
            
        return results

    def decode_tlv(self, tlv_type, payload):
        if tlv_type == 1: # MMWDEMO_OUTPUT_MSG_DETECTED_POINTS
            # Typically 4 floats: x, y, z, velocity
            num_objs = len(payload) // 16
            objs = []
            for i in range(num_objs):
                objs.append(struct.unpack('ffff', payload[i*16:(i+1)*16]))
            return objs
        elif tlv_type == 6: # Stats
            # Interframe processing time, transmit output time, etc.
            return struct.unpack('IIIIII', payload[:24]) if len(payload) >= 24 else None
        return None

if __name__ == "__main__":
    import sys
    import os
    
    # Use Test1.dat by default if no argument is provided
    if len(sys.argv) < 2:
        file_path = "Demo2.dat"
        if not os.path.exists(file_path):
            print(f"Usage: python3 read_radar_data.py <file_path>")
            print(f"Default file '{file_path}' not found.")
            sys.exit(1)
    else:
        file_path = sys.argv[1]
    parser = TIRadarParser()
    data = parser.parse_file(file_path)
    
    print(f"Parsed {len(data)} frames from {file_path}")
    for i, frame in enumerate(data[:3]): # Show first 3 frames
        h = frame['header']
        print(f"\nFrame {h['frame_number']}: {h['num_objects']} objects, {h['num_tlvs']} TLVs")
        for j, tlv in enumerate(frame['tlvs']):
            print(f"  TLV {j} | Type: {tlv['type']:2}, Length: {tlv['length']:6}")
            if tlv['type'] == 1 and tlv['decoded']:
                print(f"    Detected {len(tlv['decoded'])} objects:")
                for obj in tlv['decoded'][:5]: # Show first 5
                    print(f"      x: {obj[0]:6.2f}, y: {obj[1]:6.2f}, z: {obj[2]:6.2f}, v: {obj[3]:6.2f}")
                if len(tlv['decoded']) > 5:
                    print(f"      ...")
